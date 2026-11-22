import json
from unittest.mock import Mock

import pytest
import yaml

from kumaops.cli import main
from kumaops.config import ConfigError, load_config
from kumaops.engine import apply, plan
from kumaops.operations import apply_lock


@pytest.fixture
def session(monkeypatch, api, env, cfg, tmp_path):
    import uptime_kuma_api

    for key, value in {
        **env,
        "KUMA_URL": "https://kuma.example.com",
        "KUMA_USERNAME": "test",
        "KUMA_PASSWORD": "private-password",
        "KUMA_TOTP_CODE": "123456",
    }.items():
        monkeypatch.setenv(key, value)
    api.login = Mock(return_value={"token": "session"})
    api.info = Mock(return_value={"version": "2.5.9"})
    api.disconnect = Mock()
    constructor = Mock(return_value=api)
    monkeypatch.setattr(uptime_kuma_api, "UptimeKumaApi", constructor)
    file = tmp_path / "config.yaml"
    file.write_text(yaml.safe_dump(cfg))
    return api, cfg, env, file, constructor


def test_init_is_offline_installable_and_never_overwrites(tmp_path, monkeypatch, capsys):
    import uptime_kuma_api

    constructor = Mock(side_effect=AssertionError("offline"))
    monkeypatch.setattr(uptime_kuma_api, "UptimeKumaApi", constructor)
    file = tmp_path / "config.yaml"
    assert main(["--init", "--config", str(file), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "initialized"
    assert load_config(file)["namespace"] == "my-lab"
    original = file.read_bytes()
    assert main(["--init", "--config", str(file)]) == 2
    assert file.read_bytes() == original
    constructor.assert_not_called()


def test_init_existing_environment_does_not_create_config(tmp_path):
    (tmp_path / ".env").write_text("DO_NOT_REPLACE=true")
    file = tmp_path / "config.yaml"
    assert main(["--init", "--config", str(file)]) == 2
    assert not file.exists()
    assert (tmp_path / ".env").read_text() == "DO_NOT_REPLACE=true"


def test_ci_check_reports_missing_then_clean_then_drift(session, capsys):
    api, cfg, env, file, _ = session
    arguments = ["--config", str(file), "--format", "json", "--non-interactive"]
    assert main(["--check", *arguments]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "changes"
    assert api.writes == []
    assert main(["--apply", *arguments]) == 0
    assert json.loads(capsys.readouterr().out)["applied"] == 6
    assert main(["--check", *arguments]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "in_sync"
    next(r for r in api.rows["monitor"] if r["type"] == "http")["url"] = (
        "https://private-drift.example.com/?token=DO_NOT_PRINT"
    )
    count = len(api.writes)
    assert main(["--check", *arguments]) == 3
    output = capsys.readouterr().out
    report = json.loads(output)
    assert report["status"] == "conflict"
    assert report["actions"][0]["fields"] == ["url"]
    assert "DO_NOT_PRINT" not in output and "private-drift" not in output
    assert "NOT_A_REAL_TOKEN" not in output and "private-password" not in output
    assert main(["--apply", *arguments]) == 2
    assert len(api.writes) == count


def test_drift_report_collects_multiple_resources_and_blocks_before_create(api, cfg, env):
    apply(api, cfg, env, plan(api, cfg, env))
    api.rows["monitor"][1]["interval"] = 99
    api.rows["notification"][0]["discordWebhookUrl"] = "https://private.example.com/secret"
    api.links[1].append({"id": 999})
    actions = plan(api, cfg, env, allow_drift=True)
    assert len([a for a in actions if a.verb == "conflict"]) == 3
    count = len(api.writes)
    with pytest.raises(ConfigError):
        apply(api, cfg, env, actions)
    assert len(api.writes) == count


def test_json_error_redacts_upstream_exception(session, capsys):
    api, _, _, file, _ = session
    api.get_monitors = Mock(side_effect=RuntimeError("private-webhook-and-password"))
    assert main(["--plan", "--config", str(file), "--format", "json"]) == 1
    output = capsys.readouterr()
    assert not output.err
    assert json.loads(output.out)["status"] == "error"
    assert "private-webhook-and-password" not in output.out
    api.disconnect.assert_called_once()


def test_ca_bundle_and_timeout_forwarded(session, tmp_path):
    _, _, _, file, constructor = session
    bundle = tmp_path / "ca.pem"
    bundle.write_text("test fixture")
    assert (
        main(["--plan", "--config", str(file), "--ca-bundle", str(bundle), "--timeout", "23"]) == 0
    )
    assert constructor.call_args.kwargs == {"timeout": 23, "ssl_verify": str(bundle.resolve())}


def test_noninteractive_never_requests_credentials(monkeypatch, tmp_path):
    from kumaops.cli import credentials

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("getpass.getpass", Mock(side_effect=AssertionError("must not ask")))
    with pytest.raises(ConfigError):
        credentials({}, False, non_interactive=True)


def test_apply_lock_excludes_same_target_and_cleans_up(tmp_path):
    with apply_lock(tmp_path, "https://kuma.example.com/", "demo"):
        with pytest.raises(ConfigError):
            with apply_lock(tmp_path, "https://kuma.example.com", "demo"):
                pytest.fail("Duplicate apply allowed")
        with apply_lock(tmp_path, "https://other.example.com", "demo"):
            pass
    assert not list(tmp_path.rglob("*.lock"))
    with pytest.raises(RuntimeError):
        with apply_lock(tmp_path, "https://kuma.example.com", "demo"):
            raise RuntimeError("test")
    assert not list(tmp_path.rglob("*.lock"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("maxretries", True),
        ("retryInterval", 1),
        ("timeout", 61),
        ("method", "POST"),
        ("expiryNotification", "true"),
        ("accepted_statuscodes", ["299-200"]),
        ("accepted_statuscodes", ["201-204"]),
        ("accepted_statuscodes", [200]),
        ("type", []),
        ("group", []),
        ("url", "https://example.com/hidden\nvalue"),
    ],
)
def test_monitor_options_are_validated(cfg, tmp_path, field, value):
    cfg["monitors"]["website"][field] = value
    file = tmp_path / "config.yaml"
    file.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ConfigError):
        load_config(file)


def test_yaml_aliases_rejected_without_echoing_input(tmp_path):
    file = tmp_path / "config.yaml"
    file.write_text("version: 1\nnamespace: &private-secret demo\ngroups: *private-secret")
    with pytest.raises(ConfigError) as caught:
        load_config(file)
    assert "private-secret" not in str(caught.value)


def test_missing_config_has_setup_guidance(tmp_path, capsys):
    assert main(["--validate", "--config", str(tmp_path / "missing.yaml"), "--format", "json"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert "--init" in report["message"]
