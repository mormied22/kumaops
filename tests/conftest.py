from copy import deepcopy
from pathlib import Path

import pytest

from kumaops.config import load_config


@pytest.fixture
def cfg():
    return load_config(Path(__file__).parents[1] / "examples" / "config.yaml")


@pytest.fixture
def env():
    return {"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/EXAMPLE/NOT_A_REAL_TOKEN"}


class FakeKuma:
    """Mimics documented client shapes; intentionally does not emulate a real server."""

    def __init__(self):
        self.rows = {"monitor": [], "notification": [], "maintenance": []}
        self.links = {}
        self.writes = []
        self.fail_link = False
        self.uncertain = False
        self._event_data = {}

    def _call(self, event):
        assert event in {"getMonitorList", "getMaintenanceList"}
        return {}

    def create(self, kind, payload):
        row = deepcopy(payload)
        row.pop("applyExisting", None)
        row["id"] = len(self.rows[kind]) + 1
        self.rows[kind].append(row)
        self.writes.append((kind, row["id"]))
        if self.uncertain:
            raise TimeoutError("Simulated lost acknowledgement")
        return {
            {"monitor": "monitorID", "notification": "id", "maintenance": "maintenanceID"}[
                kind
            ]: row["id"]
        }

    def add_monitor(self, **payload):
        return self.create("monitor", payload)

    def add_notification(self, **payload):
        return self.create("notification", payload)

    def add_maintenance(self, **payload):
        return self.create("maintenance", payload)

    def get_monitors(self):
        return deepcopy(self.rows["monitor"])

    def get_notifications(self):
        return deepcopy(self.rows["notification"])

    def get_maintenances(self):
        return deepcopy(self.rows["maintenance"])

    def get_monitor_maintenance(self, id_):
        return deepcopy(self.links.get(id_, []))

    def add_monitor_maintenance(self, id_, monitors):
        if self.fail_link:
            raise TimeoutError("Link failed")
        self.links[id_] = deepcopy(monitors)
        self.writes.append(("link", id_))
        return {"ok": True}


@pytest.fixture
def api():
    return FakeKuma()
