"""Opt-in, real-server tests. Never accepts an existing server URL or account."""

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import struct
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from uptime_kuma_api import UptimeKumaApi
from dotenv import dotenv_values

from kumaops.client import LiveAdapter
from kumaops.config import http_url


class BootstrapApi(UptimeKumaApi):
    def __init__(self, *args, **kwargs):
        self.bootstrap_ready = threading.Event()
        super().__init__(*args, **kwargs)

    def _event_info(self, data):
        super()._event_info(data)
        # Kuma hides version until login; the initial event still gates handler setup.
        self.bootstrap_ready.set()


def pytest_addoption(parser):
    parser.addoption(
        "--live-kuma-source", type=Path, help="Disposable official Kuma 2.5.9 checkout"
    )
    parser.addoption(
        "--discord-env-file",
        type=Path,
        help="Opt in to real test-channel messages using DISCORD_TEST_WEBHOOK_URL",
    )


def wait_for(predicate, timeout=60, description="verification condition"):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.25)
    pytest.fail("Timed out waiting for " + description)


def totp(secret, offset=0):
    key = base64.b32decode(secret.upper() + "=" * ((-len(secret)) % 8))
    counter = int(time.time() // 30) + offset
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    start = digest[-1] & 15
    return f"{(struct.unpack('>I', digest[start : start + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


class LocalEndpoints:
    def __init__(self):
        self.up = True
        self.receipts = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200 if owner.up else 503)
                self.end_headers()
                self.wfile.write(b"KumaOps disposable verification endpoint")

            def do_POST(self):
                size = int(self.headers.get("Content-Length", "0"))
                owner.receipts.append(json.loads(self.rfile.read(size)))
                self.send_response(204)
                self.end_headers()

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


@pytest.fixture(scope="session")
def live_source(request):
    source = request.config.getoption("--live-kuma-source")
    if source is None:
        pytest.skip("Opt in with --live-kuma-source; no live instance is used by default")
    source = source.resolve()
    assert json.loads((source / "package.json").read_text())["version"] == "2.5.9"
    assert (source / "dist/index.html").is_file()
    assert (source / "node_modules").is_dir()
    return source


@pytest.fixture(scope="session")
def real_webhook(request):
    path = request.config.getoption("--discord-env-file")
    if path is None:
        return None
    values = dotenv_values(path, interpolate=False)
    value = values.get("DISCORD_TEST_WEBHOOK_URL", "")
    if not (
        http_url(value)
        and value.startswith("https://discord.com/api/webhooks/")
        and len(value.split("/")) == 7
        and "?" not in value
    ):
        pytest.fail("Invalid test webhook; check the local environment file")
    return value


@pytest.fixture(scope="session")
def live(live_source, tmp_path_factory, real_webhook):
    node = shutil.which("node")
    assert node, "Node.js is required"
    local = LocalEndpoints()
    data = tmp_path_factory.mktemp("kuma-live")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    inherited = {k: v for k, v in os.environ.items() if not k.startswith("UPTIME_KUMA_")}
    env = {
        **inherited,
        "UPTIME_KUMA_HOST": "127.0.0.1",
        "UPTIME_KUMA_PORT": str(port),
        "UPTIME_KUMA_DB_TYPE": "sqlite",
        "DATA_DIR": str(data / "data"),
        "NODE_ENV": "production",
        "TZ": "UTC",
        "KUMAOPS_VERIFY_SINK": local.url,
        "KUMAOPS_REAL_TEST_WEBHOOK": real_webhook or "",
    }
    # The isolated server's Discord provider uses a local sink only for the exact fake URL.
    preload = Path(__file__).with_name("discord-sink.cjs")
    log = (data / "server.log").open("w", encoding="utf-8")
    process = subprocess.Popen(
        [node, "--require", str(preload), "server/server.js"],
        cwd=live_source,
        env=env,
        stdout=log,
        stderr=log,
    )
    client = None
    try:

        def ready():
            if process.poll() is not None:
                pytest.fail("Disposable Kuma exited; inspect local server.log (do not publish it)")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    return True
            except OSError:
                return False

        wait_for(ready, timeout=90)
        url = f"http://127.0.0.1:{port}"
        client = BootstrapApi(url, timeout=15)
        assert client.bootstrap_ready.wait(15), "Initial Kuma handshake did not complete"
        assert client.need_setup() is True
        username, password = "kumaops-verification", secrets.token_urlsafe(32)
        client.setup(username, password)
        assert client.login(username, password).get("token")
        assert client.info()["version"] == "2.5.9"
        yield {
            "api": LiveAdapter(client),
            "local": local,
            "url": url,
            "username": username,
            "password": password,
            "source": live_source,
        }
    finally:
        if client:
            client.disconnect()
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()
        local.close()
