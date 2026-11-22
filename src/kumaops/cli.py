"""Command-line interface with redacted text and versioned JSON output."""

import argparse
import getpass
import json
import logging
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

from . import __version__
from .config import ConfigError, http_url, load_config, require
from .engine import apply, plan
from .operations import apply_lock, initialize


def credentials(env, prompt_2fa, non_interactive=False):
    username = env.get("KUMA_USERNAME")
    password = env.get("KUMA_PASSWORD")
    token = env.get("KUMA_TOTP_CODE") or ""
    interactive = sys.stdin.isatty() and not non_interactive
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


def positive_timeout(value):
    try:
        number = int(value)
        if 1 <= number <= 300:
            return number
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("timeout must be an integer from 1 to 300")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="KumaOps: configuration and drift checks for Kuma v2"
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--env-file", type=Path, help="Explicit .env path; never auto-discovered")
    mode = parser.add_mutually_exclusive_group(required=True)
    for flag, help_text in (
        ("init", "Create a starter config and local environment file offline"),
        ("validate", "Offline YAML schema validation"),
        ("plan", "Read server and show proposed actions"),
        ("check", "Read-only drift check; exit 3 when changes or conflicts exist"),
        ("apply", "Apply and verify additive changes; stop on drift"),
    ):
        mode.add_argument("--" + flag, action="store_true", help=help_text)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--two-factor", action="store_true", help="Read a current 2FA code through hidden input"
    )
    parser.add_argument(
        "--non-interactive", action="store_true", help="Fail instead of requesting credentials"
    )
    parser.add_argument(
        "--timeout", type=positive_timeout, default=15, help="API timeout in seconds (1–300)"
    )
    parser.add_argument(
        "--ca-bundle", type=Path, help="Custom trusted CA bundle; certificate checks stay enabled"
    )
    parser.add_argument(
        "--allow-http", action="store_true", help="Allow plaintext on a trusted lab network"
    )
    args = parser.parse_args(argv)
    command = next(
        name for name in ("init", "validate", "plan", "check", "apply") if getattr(args, name)
    )
    api = None

    def emit(status, actions=(), message=None, applied=None):
        records = [
            {
                "operation": a.verb,
                "kind": a.ref.kind,
                "key": a.ref.key,
                **({"fields": a.payload["fields"]} if a.verb == "conflict" else {}),
            }
            for a in actions
        ]
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "command": command,
                        "status": status,
                        "actions": records,
                        "message": message,
                        "applied": applied,
                    }
                )
            )
        elif status == "error":
            print("Error: " + message, file=sys.stderr)
        else:
            for action in actions:
                print(
                    action.summary()
                    + (
                        ": " + ", ".join(action.payload["fields"])
                        if action.verb == "conflict"
                        else ""
                    )
                )
            if message:
                print(message)
            conflicts = sum(a.verb == "conflict" for a in actions)
            if conflicts:
                print(f"Plan blocked: {conflicts} conflicting resource(s). No changes applied.")
            elif command in {"plan", "check", "apply"}:
                print(
                    f"Plan: {len(actions)} additive action(s). No delete or configuration update operations."
                )
            if applied is not None:
                print(f"Applied and verified {applied} action(s).")

    for name in ("uptime_kuma_api", "socketio", "engineio"):
        logging.getLogger(name).disabled = True
    try:
        if args.init:
            initialize(args.config, args.env_file or args.config.parent / ".env")
            emit(
                "initialized",
                message="Created starter configuration and private environment template. Edit before applying.",
            )
            return 0
        require(args.config.is_file(), "Configuration not found; run --init or specify --config")
        cfg = load_config(args.config)
        if args.validate:
            emit(
                "valid",
                message="Configuration valid (offline; secrets and server compatibility not checked).",
            )
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
        if args.ca_bundle:
            require(args.ca_bundle.is_file(), "CA bundle not found")
        from uptime_kuma_api import UptimeKumaApi, UptimeKumaException
        from .client import LiveAdapter

        username, password, token = credentials(
            env, args.two_factor, args.non_interactive or args.format == "json"
        )
        api = UptimeKumaApi(
            url,
            timeout=args.timeout,
            ssl_verify=str(args.ca_bundle.resolve()) if args.ca_bundle else True,
        )
        try:
            result = api.login(username, password, token=token)
        except UptimeKumaException as exc:
            raise ConfigError(
                "Login failed; check credentials and use a fresh unused 2FA code. Kuma rejects a code already used for another login."
            ) from exc
        require(
            isinstance(result, dict) and bool(result.get("token")),
            "Login incomplete; check credentials and supply current 2FA code",
        )
        require(str(api.info().get("version", "")).startswith("2."), "Only Kuma v2 is supported")
        api = LiveAdapter(api)
        if args.apply:
            with apply_lock(args.config.resolve().parent, url, cfg["namespace"]):
                actions = plan(api, cfg, env)
                count = apply(api, cfg, env, actions)
            emit("applied", actions, applied=count)
            return 0
        actions = plan(api, cfg, env, allow_drift=True)
        conflicts = any(a.verb == "conflict" for a in actions)
        status = "conflict" if conflicts else "changes" if actions else "in_sync"
        emit(status, actions)
        return 3 if args.check and actions else 2 if conflicts else 0
    except ConfigError as exc:
        emit("error", message=str(exc))
        return 2
    except Exception:
        emit(
            "error",
            message="Operation failed. Check connectivity/authentication and inspect the server before re-planning. Partial changes may exist; no automatic retries.",
        )
        return 1
    finally:
        if api is not None:
            try:
                api.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
