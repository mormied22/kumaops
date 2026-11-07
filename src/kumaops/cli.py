import argparse
import getpass
import logging
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

from .config import ConfigError, http_url, load_config, require
from .engine import apply, plan


def credentials(env, prompt_2fa):
    username = env.get("KUMA_USERNAME")
    password = env.get("KUMA_PASSWORD")
    token = env.get("KUMA_TOTP_CODE", "")
    interactive = sys.stdin.isatty()
    if not username and interactive:
        username = input("Kuma username: ")
    if not password and interactive:
        password = getpass.getpass("Kuma password: ")
    if prompt_2fa:
        require(interactive, "--two-factor needs a terminal; use KUMA_TOTP_CODE in automation")
        token = getpass.getpass("Current six-digit 2FA code: ")
    require(bool(username and password), "Set KUMA_USERNAME and KUMA_PASSWORD or use a terminal")
    require(not token or re.fullmatch(r"\d{6}", token), "2FA code must be six digits")
    return username, password, token


def main(argv=None):
    parser = argparse.ArgumentParser(description="KumaOps v0.1: additive Kuma v2 provisioning")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--env-file", type=Path, help="Explicit .env path; never auto-discovered")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true", help="Offline YAML schema validation")
    mode.add_argument("--plan", action="store_true", help="Read server and print redacted actions")
    mode.add_argument(
        "--apply", action="store_true", help="Plan, apply and verify additive changes"
    )
    parser.add_argument("--two-factor", action="store_true", help="Prompt for a current 2FA code")
    parser.add_argument(
        "--allow-http", action="store_true", help="Allow plaintext on a trusted lab network"
    )
    args = parser.parse_args(argv)
    api = None
    # Third-party exceptions/loggers can contain complete payloads or credentials.
    logging.getLogger("uptime_kuma_api").disabled = True
    logging.getLogger("socketio").disabled = True
    logging.getLogger("engineio").disabled = True
    try:
        cfg = load_config(args.config)
        if args.validate:
            print("Configuration valid (offline; secrets and server compatibility not checked).")
            return 0
        if args.env_file:
            require(args.env_file.is_file(), "Environment file not found")
        env = {
            **(dotenv_values(args.env_file, interpolate=False) if args.env_file else {}),
            **os.environ,
        }
        url = env.get("KUMA_URL", "")
        require(
            http_url(url) and not urlsplit(url).query,
            "Set a valid KUMA_URL without credentials/query",
        )
        require(
            url.startswith("https://") or args.allow_http,
            "HTTP requires --allow-http on a trusted lab network",
        )
        from uptime_kuma_api import UptimeKumaApi, UptimeKumaException
        from .client import LiveAdapter

        username, password, token = credentials(env, args.two_factor)
        api = UptimeKumaApi(url, timeout=15, ssl_verify=True)
        try:
            result = api.login(username, password, token=token)
        except UptimeKumaException as exc:
            raise ConfigError(
                "Login failed; check credentials and use a fresh unused 2FA code. "
                "Kuma rejects a code already used for another login."
            ) from exc
        require(
            isinstance(result, dict) and bool(result.get("token")),
            "Login incomplete; check credentials and supply current 2FA code",
        )
        require(str(api.info().get("version", "")).startswith("2."), "Only Kuma v2 is supported")
        api = LiveAdapter(api)
        actions = plan(api, cfg, env)
        for action in actions:
            print(action.summary())
        print(
            f"Plan: {len(actions)} additive action(s). No delete or configuration update operations."
        )
        if args.apply:
            print(f"Applied and verified {apply(api, cfg, env, actions)} action(s).")
        return 0
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 -- exception messages may expose secrets
        # Deliberately do not echo exception text, paths, URL, secrets or server payloads.
        print(
            "Error: operation failed. Check connectivity/authentication and inspect the server "
            "before re-planning. Partial changes may exist; no automatic retries.",
            file=sys.stderr,
        )
        return 1
    finally:
        if api is not None:
            try:
                api.disconnect()
            except Exception:  # noqa: BLE001 -- disconnect must not leak server payloads
                pass  # noqa: S110


if __name__ == "__main__":
    raise SystemExit(main())
