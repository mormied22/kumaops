"""Real Kuma + real client + disposable endpoint; Discord transport is a local sink."""

from copy import deepcopy
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import pytest
from uptime_kuma_api import UptimeKumaApi, UptimeKumaException

from kumaops.config import ConfigError
from kumaops.engine import apply, plan
from conftest import totp, wait_for


def config(live, namespace):
    return {
        "version": 1,
        "namespace": namespace,
        "notifications": {"alerts": {"webhook_env": "TEST_WEBHOOK", "prefix": "[KumaOps test]"}},
        "groups": {"checks": {}},
        "monitors": {
            "http": {
                "type": "http",
                "url": live["local"].url,
                "interval": 20,
                "notifications": ["alerts"],
                "group": "checks",
            },
            "tcp": {
                "type": "port",
                "hostname": "127.0.0.1",
                "port": live["local"].port,
                "interval": 20,
                "group": "checks",
            },
            "ping": {"type": "ping", "hostname": "127.0.0.1", "group": "checks"},
        },
        "maintenance": {
            "weekly": {
                "timezone": "Europe/London",
                "weekdays": [0],
                "start_date": "2026-01-01",
                "start": "03:00",
                "end": "03:30",
                "active": False,
                "monitors": ["http", "tcp"],
            }
        },
    }


FAKE_ENV = {"TEST_WEBHOOK": "https://discord.com/api/webhooks/KUMAOPS_TEST/NOT_A_REAL_TOKEN"}


def test_live_provision_rerun_drift_and_links(live):
    api = live["api"]
    cfg = config(live, "verify-provision")
    before = len(api.get_monitors())
    actions = plan(api, cfg, FAKE_ENV)
    assert len(api.get_monitors()) == before
    assert apply(api, cfg, FAKE_ENV, actions) == 7
    assert plan(api, cfg, FAKE_ENV) == []
    assert apply(api, cfg, FAKE_ENV, []) == 0
    maintenance = next(m for m in api.get_maintenances() if "/ verify-provision /" in m["title"])
    assert maintenance["status"] == "inactive"
    assert maintenance["timezoneOption"] == "Europe/London"
    assert len(api.get_monitor_maintenance(maintenance["id"])) == 2
    for row in api.get_monitors():
        if "/ verify-provision /" in row["name"] and row["type"] != "group":

            def healthy():
                beats = api.get_monitor_beats(row["id"], 1)
                return bool(beats) and beats[-1]["status"] == 1

            wait_for(healthy, timeout=65)
    changed = deepcopy(cfg)
    changed["monitors"]["http"]["interval"] = 30
    with pytest.raises(ConfigError, match="Drift"):
        plan(api, changed, FAKE_ENV)
    assert plan(api, cfg, FAKE_ENV) == []


def alert_cycle(live, namespace, webhook_env):
    api, local = live["api"], live["local"]
    cfg = config(live, namespace)
    # Only the HTTP monitor is relevant to this test.
    cfg["monitors"] = {"http": cfg["monitors"]["http"]}
    now = datetime.now(ZoneInfo("Europe/London"))
    end = now + timedelta(minutes=10)
    assert now.date() == end.date(), "Run away from midnight for same-day maintenance"
    cfg["maintenance"]["weekly"].update(
        {
            "weekdays": [(now.weekday() + 1) % 7],
            "start_date": now.date().isoformat(),
            "start": now.strftime("%H:%M"),
            "end": end.strftime("%H:%M"),
            "monitors": ["http"],
        }
    )
    apply(api, cfg, webhook_env, plan(api, cfg, webhook_env))
    monitor = next(m for m in api.get_monitors() if f"/ {namespace} / http" in m["name"])
    monitor_id = monitor["id"]
    maintenance = next(m for m in api.get_maintenances() if f"/ {namespace} /" in m["title"])

    def heartbeat_status(status):
        beats = api.get_monitor_beats(monitor_id, 1)
        return bool(beats) and beats[-1]["status"] == status

    def alerts(word):
        return [
            r
            for r in local.receipts
            if any(
                f"{namespace} / http" in e.get("title", "") and word in e.get("title", "")
                for e in r.get("payload", r).get("embeds", [])
            )
        ]

    try:
        wait_for(lambda: heartbeat_status(1), timeout=60, description="baseline UP heartbeat")
        initial_down, initial_up = len(alerts("went down")), len(alerts("is up"))
        local.up = False
        # The pinned client defaults to one retry at 60 seconds after the 20s interval.
        wait_for(
            lambda: len(alerts("went down")) == initial_down + 1,
            timeout=140,
            description="DOWN provider event",
        )
        local.up = True
        wait_for(
            lambda: len(alerts("is up")) == initial_up + 1,
            timeout=65,
            description="UP provider event",
        )
        api.resume_maintenance(maintenance["id"])
        wait_for(
            lambda: (
                next(m for m in api.get_maintenances() if m["id"] == maintenance["id"])["status"]
                == "under-maintenance"
            ),
            description="maintenance activation",
        )
        before = len(alerts("went down"))
        local.up = False
        wait_for(lambda: heartbeat_status(3), timeout=65, description="maintenance heartbeat")
        assert len(alerts("went down")) == before
        api.pause_maintenance(maintenance["id"])
        wait_for(
            lambda: len(alerts("went down")) == before + 1,
            timeout=140,
            description="post-maintenance DOWN provider event",
        )
        local.up = True
        wait_for(
            lambda: len(alerts("is up")) == initial_up + 2,
            timeout=65,
            description="post-maintenance UP provider event",
        )
    finally:
        local.up = True
        api.pause_maintenance(maintenance["id"])
        api.pause_monitor(monitor_id)


def test_live_down_up_and_maintenance_suppression(live):
    alert_cycle(live, "verify-alerts", FAKE_ENV)


def test_real_discord_delivery(live, real_webhook):
    if not real_webhook:
        pytest.skip("Real Discord delivery needs explicit --discord-env-file")
    alert_cycle(live, "verify-discord", {"TEST_WEBHOOK": real_webhook})
    receipts = [r for r in live["local"].receipts if r.get("transport") == "real-discord"]
    assert len(receipts) >= 4 and all(r["status"] in {200, 204} for r in receipts)


def test_live_two_factor(live, monkeypatch, tmp_path, capsys):
    api, password = live["api"], live["password"]
    uri = api.prepare_2fa(password)["uri"]
    secret = parse_qs(urlsplit(uri).query)["secret"][0]
    assert api.verify_token(totp(secret), password)["valid"]
    api.save_2fa(password)
    before = len(api.get_monitors())
    try:
        for code in ("", totp(secret, -20), "invalid"):
            with UptimeKumaApi(live["url"], timeout=10) as fresh:
                try:
                    result = fresh.login(live["username"], password, token=code)
                    assert not result.get("token"), "Invalid 2FA input authenticated"
                except UptimeKumaException:
                    pass
        assert len(api.get_monitors()) == before
        # Exercise the real CLI against this same isolated server with 2FA enabled.
        import yaml
        from kumaops.cli import main

        cfg_path = tmp_path / "cli.yaml"
        cfg_path.write_text(yaml.safe_dump(config(live, "verify-cli")), encoding="utf-8")
        for key, value in {
            "KUMA_URL": live["url"],
            "KUMA_USERNAME": live["username"],
            "KUMA_PASSWORD": password,
            **FAKE_ENV,
        }.items():
            monkeypatch.setenv(key, value)
        arguments = ["--config", str(cfg_path), "--allow-http"]
        last_code = None
        for mode in ("--plan", "--apply", "--plan"):
            code = wait_for(
                lambda: totp(secret) if totp(secret) != last_code else None,
                timeout=45,
                description="a fresh unused authenticator code",
            )
            monkeypatch.setenv("KUMA_TOTP_CODE", code)
            assert main([mode, *arguments]) == 0
            last_code = code
            if mode == "--plan":
                with UptimeKumaApi(live["url"], timeout=10) as fresh:
                    with pytest.raises(UptimeKumaException):
                        fresh.login(live["username"], password, token=code)
        output = capsys.readouterr()
        assert "Plan: 0 additive action(s)" in output.out
        assert password not in output.out + output.err
    finally:
        api.disable_2fa(password)
