from pathlib import Path
from unittest.mock import Mock

import pytest

from kumaops.cli import main


@pytest.fixture
def connected(monkeypatch, api, env):
    import uptime_kuma_api

    settings = {
        **env,
        "KUMA_URL": "https://kuma.example.com",
        "KUMA_USERNAME": "example",
        "KUMA_PASSWORD": "test-password",
        "KUMA_TOTP_CODE": "123456",
    }
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    api.login = Mock(return_value={"token": "test-session"})
    api.info = Mock(return_value={"version": "2.0.0"})
    api.disconnect = Mock()
    from contextlib import nullcontext

    api.wait_for_event = Mock(side_effect=lambda *args: nullcontext())
    constructor = Mock(return_value=api)
    monkeypatch.setattr(uptime_kuma_api, "UptimeKumaApi", constructor)
    return api, constructor


def arguments(mode):
    return [mode, "--config", str(Path(__file__).parents[1] / "examples" / "config.yaml")]


def test_live_plan_reads_only(connected, capsys):
    api, constructor = connected
    assert main(arguments("--plan")) == 0
    assert not api.writes
    api.login.assert_called_once_with("example", "test-password", token="123456")
    assert constructor.call_args.kwargs["ssl_verify"] is True
    assert "NOT_A_REAL_TOKEN" not in capsys.readouterr().out


def test_cli_apply_and_rerun(connected, capsys):
    api, _ = connected
    assert main(arguments("--apply")) == 0
    assert len(api.writes) == 6
    assert main(arguments("--apply")) == 0
    assert len(api.writes) == 6
    assert "Applied and verified 0" in capsys.readouterr().out


def test_incomplete_2fa_login_blocks_writes(connected):
    api, _ = connected
    api.login.return_value = {"tokenRequired": True}
    assert main(arguments("--apply")) == 2
    assert not api.writes
    api.disconnect.assert_called_once()


def test_v1_server_blocks_writes(connected):
    api, _ = connected
    api.info.return_value = {"version": "1.23.0"}
    assert main(arguments("--apply")) == 2
    assert not api.writes


def test_http_requires_explicit_opt_in(connected, monkeypatch):
    api, constructor = connected
    monkeypatch.setenv("KUMA_URL", "http://kuma.example.com")
    assert main(arguments("--plan")) == 2
    constructor.assert_not_called()
    assert not api.writes
