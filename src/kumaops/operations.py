"""Local setup and apply exclusion. No server credentials are written by these helpers."""

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path

import yaml

from .config import ConfigError, require


def initialize(config_path, env_path):
    paths = (Path(config_path), Path(env_path))
    require(paths[0].resolve() != paths[1].resolve(), "Config and environment paths must differ")
    require(
        not any(p.exists() or p.is_symlink() for p in paths),
        "Setup refuses to overwrite existing config or environment files",
    )
    config = {
        "version": 1,
        "namespace": "my-lab",
        "monitors": {"website": {"type": "http", "url": "https://example.com", "interval": 60}},
    }
    contents = (
        yaml.safe_dump(config, sort_keys=False),
        "KUMA_URL=https://kuma.example.com\nKUMA_USERNAME=\nKUMA_PASSWORD=\nKUMA_TOTP_CODE=\n",
    )
    for path, content in zip(paths, contents):
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ConfigError(
                "A setup file appeared concurrently; existing files were preserved"
            ) from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)


@contextmanager
def apply_lock(directory, url, namespace):
    location = Path(directory) / ".kumaops" / "locks"
    location.mkdir(parents=True, exist_ok=True)
    identity = hashlib.sha256((url.rstrip("/") + "\n" + namespace).encode()).hexdigest()
    lock = location / (identity + ".lock")
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ConfigError(
            "Another apply holds this local lock; inspect stopped processes before removing a stale lock"
        ) from exc
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()
