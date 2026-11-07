"""Offline contract checks against the pinned client, not live integration tests."""

from contextlib import nullcontext
from unittest.mock import Mock

from uptime_kuma_api import Event, UptimeKumaApi

from kumaops.client import LiveAdapter
from kumaops.engine import Ref, desired, resolve


def test_payloads_accepted_by_pinned_client_builders(cfg, env):
    client = UptimeKumaApi.__new__(UptimeKumaApi)
    client.info = Mock(return_value={"version": "2.0.0"})
    client.wait_for_event = Mock(side_effect=lambda *args: nullcontext())
    client._call = Mock(return_value={"ok": True})
    ids = {Ref("monitor", "services"): 11, Ref("notification", "discord"): 12}
    # Execute installed public methods and their validation/conversion, replacing only transport.
    for ref, payload in desired(cfg, env):
        getattr(client, "add_" + ref.kind)(**resolve(payload, ids))
    events = [call.args[0] for call in client._call.call_args_list]
    assert events == ["addNotification", "add", "add", "add", "addMaintenance"]
    monitor_payload = client._call.call_args_list[2].args[1]
    assert monitor_payload["parent"] == 11
    assert monitor_payload["notificationIDList"] == {12: True}


def test_maintenance_creation_delegates_once():
    api = Mock()
    api.wait_for_event.return_value = nullcontext()
    adapter = LiveAdapter(api)
    adapter.add_maintenance(title="example")
    api.add_maintenance.assert_called_once_with(title="example")


def test_adapter_invalidates_cached_snapshot_before_request():
    api = Mock()
    api._event_data = {Event.MONITOR_LIST: {"old": {}}, Event.MAINTENANCE_LIST: {"old": {}}}

    def request(event):
        field = Event.MONITOR_LIST if event == "getMonitorList" else Event.MAINTENANCE_LIST
        assert api._event_data[field] is None
        api._event_data[field] = {"new": {"id": 1}}

    api._call.side_effect = request
    api.get_monitors.side_effect = lambda: list(api._event_data[Event.MONITOR_LIST].values())
    api.get_maintenances.side_effect = lambda: list(
        api._event_data[Event.MAINTENANCE_LIST].values()
    )
    adapter = LiveAdapter(api)
    assert adapter.get_monitors() == [{"id": 1}]
    assert adapter.get_maintenances() == [{"id": 1}]
