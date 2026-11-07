"""Refresh server snapshots explicitly; the pinned client's list helpers cache events."""

from uptime_kuma_api import Event


class LiveAdapter:
    def __init__(self, api):
        self.api = api

    def __getattr__(self, name):
        return getattr(self.api, name)

    def _refresh(self, event, request, getter):
        # Serial-use adapter. Reset before requesting so a stale cache cannot satisfy the read.
        self.api._event_data[event] = None
        self.api._call(request)
        return getter()

    def get_monitors(self):
        return self._refresh(Event.MONITOR_LIST, "getMonitorList", self.api.get_monitors)

    def get_maintenances(self):
        return self._refresh(
            Event.MAINTENANCE_LIST, "getMaintenanceList", self.api.get_maintenances
        )

    def add_maintenance(self, **payload):
        # Read-back verification is performed by plan() through get_maintenances().
        return self.api.add_maintenance(**payload)
