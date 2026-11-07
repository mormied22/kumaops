from copy import deepcopy

import pytest

from kumaops.config import ConfigError
from kumaops.engine import apply, plan


def test_plan_is_read_only_and_redacted(api, cfg, env):
    actions = plan(api, cfg, env)
    assert len(actions) == 6
    assert not api.writes
    assert "NOT_A_REAL_TOKEN" not in repr(actions)
    assert all("https:" not in a.summary() for a in actions)


def test_apply_resolves_ids_and_second_apply_is_noop(api, cfg, env):
    api.rows["monitor"].append({"id": 99, "name": "Unmanaged"})
    assert apply(api, cfg, env, plan(api, cfg, env)) == 6
    assert plan(api, cfg, env) == []
    assert apply(api, cfg, env, []) == 0
    assert api.rows["monitor"][0] == {"id": 99, "name": "Unmanaged"}
    website = api.rows["monitor"][2]
    assert website["notificationIDList"] == [1]
    assert website["parent"] == 2
    assert api.rows["maintenance"][0]["timezoneOption"] == "Europe/London"
    assert api.rows["maintenance"][0]["active"] is False
    assert len(api.links[1]) == 2


def test_drift_aborts_all_writes(api, cfg, env):
    apply(api, cfg, env, plan(api, cfg, env))
    api.rows["monitor"][1]["url"] = "https://changed.example.com"
    before = len(api.writes)
    cfg["monitors"]["extra"] = {"type": "ping", "hostname": "extra.example.com"}
    with pytest.raises(ConfigError, match="Drift"):
        plan(api, cfg, env)
    assert len(api.writes) == before


def test_duplicate_identity_fails(api, cfg, env):
    apply(api, cfg, env, plan(api, cfg, env))
    duplicate = deepcopy(api.rows["notification"][0])
    duplicate["id"] = 55
    api.rows["notification"].append(duplicate)
    with pytest.raises(ConfigError, match="Ambiguous"):
        plan(api, cfg, env)


def test_changed_plan_refused(api, cfg, env):
    reviewed = plan(api, cfg, env)
    cfg["monitors"]["website"]["interval"] = 90
    with pytest.raises(ConfigError, match="Plan changed"):
        apply(api, cfg, env, reviewed)
    assert not api.writes


def test_interrupted_links_recover_without_duplicate_creates(api, cfg, env):
    api.fail_link = True
    with pytest.raises(TimeoutError):
        apply(api, cfg, env, plan(api, cfg, env))
    assert [a.verb for a in plan(api, cfg, env)] == ["link"]
    api.fail_link = False
    assert apply(api, cfg, env, plan(api, cfg, env)) == 1
    assert plan(api, cfg, env) == []


def test_unknown_create_outcome_is_never_retried(api, cfg, env):
    api.uncertain = True
    with pytest.raises(TimeoutError):
        apply(api, cfg, env, plan(api, cfg, env))
    assert len(api.writes) == 1
    assert not any(a.ref.kind == "notification" for a in plan(api, cfg, env))


def test_unexpected_links_are_preserved_and_block_apply(api, cfg, env):
    apply(api, cfg, env, plan(api, cfg, env))
    api.links[1].append({"id": 999})
    with pytest.raises(ConfigError, match="Unexpected maintenance links"):
        plan(api, cfg, env)
    assert api.links[1][-1] == {"id": 999}


def test_notification_map_and_maintenance_return_normalization(api, cfg, env):
    apply(api, cfg, env, plan(api, cfg, env))
    api.rows["monitor"][1]["notificationIDList"] = {"1": True}
    maintenance = api.rows["maintenance"][0]
    maintenance["dateRange"].append(None)
    for slot in maintenance["timeRange"]:
        slot["seconds"] = 0
    assert plan(api, cfg, env) == []


def test_invalid_secret_not_in_error(api, cfg):
    with pytest.raises(ConfigError) as caught:
        plan(api, cfg, {"DISCORD_WEBHOOK_URL": "sensitive-value"})
    assert "sensitive-value" not in str(caught.value)
    assert not api.writes


def test_tcp_monitor(api, cfg, env):
    cfg["monitors"]["database"] = {"type": "port", "hostname": "db.example.com", "port": 5432}
    apply(api, cfg, env, plan(api, cfg, env))
    row = next(r for r in api.rows["monitor"] if r["name"].endswith("/ database"))
    assert row["type"] == "port" and row["port"] == 5432
    assert plan(api, cfg, env) == []
