import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from kumaops.cli import credentials, main
from kumaops.config import ConfigError


def test_offline_validate_does_not_connect(monkeypatch, capsys):
    import uptime_kuma_api

    constructor = Mock(side_effect=AssertionError("must not connect"))
    monkeypatch.setattr(uptime_kuma_api, "UptimeKumaApi", constructor)
    path = Path(__file__).parents[1] / "examples" / "config.yaml"
    assert main(["--validate", "--config", str(path)]) == 0
    constructor.assert_not_called()
    assert "offline" in capsys.readouterr().out


def test_hidden_2fa_prompt(monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    prompt = Mock(return_value="123456")
    monkeypatch.setattr("getpass.getpass", prompt)
    assert credentials({"KUMA_USERNAME": "example", "KUMA_PASSWORD": "test"}, True) == (
        "example",
        "test",
        "123456",
    )
    prompt.assert_called_once()


def test_2fa_env_noninteractive(monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert (
        credentials(
            {"KUMA_USERNAME": "example", "KUMA_PASSWORD": "test", "KUMA_TOTP_CODE": "123456"}, False
        )[2]
        == "123456"
    )
    with pytest.raises(ConfigError):
        credentials(
            {"KUMA_USERNAME": "example", "KUMA_PASSWORD": "test", "KUMA_TOTP_CODE": "bad"}, False
        )


def test_error_redaction_and_disconnect(monkeypatch, capsys):
    import uptime_kuma_api

    for key, value in {
        "KUMA_URL": "https://kuma.example.com",
        "KUMA_USERNAME": "example",
        "KUMA_PASSWORD": "secret-test-password",
    }.items():
        monkeypatch.setenv(key, value)
    client = Mock()
    client.login.side_effect = RuntimeError("secret-test-password webhook-token private-host")
    monkeypatch.setattr(uptime_kuma_api, "UptimeKumaApi", Mock(return_value=client))
    path = Path(__file__).parents[1] / "examples" / "config.yaml"
    assert main(["--plan", "--config", str(path)]) == 1
    output = capsys.readouterr()
    assert "secret-test-password" not in output.err
    assert "webhook-token" not in output.err
    client.disconnect.assert_called_once()


def test_2fa_replay_error_is_actionable_and_redacted(monkeypatch, capsys):
    import uptime_kuma_api

    for key, value in {
        "KUMA_URL": "https://kuma.example.com",
        "KUMA_USERNAME": "example",
        "KUMA_PASSWORD": "secret-test-password",
    }.items():
        monkeypatch.setenv(key, value)
    client = Mock()
    client.login.side_effect = uptime_kuma_api.UptimeKumaException("private-server-message")
    monkeypatch.setattr(uptime_kuma_api, "UptimeKumaApi", Mock(return_value=client))
    path = Path(__file__).parents[1] / "examples" / "config.yaml"
    assert main(["--plan", "--config", str(path)]) == 2
    error = capsys.readouterr().err
    assert "fresh unused 2FA code" in error
    assert "private-server-message" not in error
    client.disconnect.assert_called_once()
