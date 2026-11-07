"""State-free additive planning. Resource names are stable reserved identities."""

from dataclasses import dataclass, field
from enum import Enum

from .config import http_url, require


@dataclass(frozen=True)
class Ref:
    kind: str
    key: str


@dataclass
class Action:
    verb: str
    ref: Ref
    payload: dict = field(repr=False)  # May contain a webhook; never print this.

    def summary(self):
        return f"{self.verb.upper()} {self.ref.kind}/{self.ref.key}"


def canonical(value, key=""):
    if isinstance(value, Enum):
        return value.value
    if key == "notificationIDList" and isinstance(value, dict):
        return sorted(int(k) for k, enabled in value.items() if enabled)
    if isinstance(value, list):
        result = [canonical(v) for v in value]
        if key in {"notificationIDList", "weekdays"}:
            return sorted(result, key=str)
        if key == "dateRange":
            return [v for v in result if v not in (None, "")]
        return result
    if isinstance(value, dict):
        return {k: canonical(v, k) for k, v in value.items() if k != "seconds" or v != 0}
    return value


def desired(cfg, env):
    def name(key):
        return f"KumaOps / {cfg['namespace']} / {key}"

    resources = []
    marker = f"Managed by KumaOps: {cfg['namespace']}"
    for key, item in cfg["notifications"].items():
        webhook = env.get(item["webhook_env"], "")
        require(
            http_url(webhook)
            and webhook.startswith("https://discord.com/api/webhooks/")
            and len(webhook.split("/")) == 7
            and bool(webhook.split("/")[-1])
            and "?" not in webhook,
            "Missing or invalid Discord webhook environment value",
        )
        resources.append(
            (
                Ref("notification", key),
                {
                    "name": name(key),
                    "type": "discord",
                    "isDefault": False,
                    "applyExisting": False,
                    "discordWebhookUrl": webhook,
                    "discordPrefixMessage": item.get("prefix", "Status changed"),
                },
            )
        )
    for key in cfg["groups"]:
        resources.append(
            (
                Ref("monitor", key),
                {
                    "name": name(key),
                    "type": "group",
                    "description": marker,
                    "parent": None,
                    "notificationIDList": [],
                },
            )
        )
    for key, item in cfg["monitors"].items():
        payload = {
            "name": name(key),
            "type": item["type"],
            "description": marker,
            "interval": item.get("interval", 60),
            "parent": Ref("monitor", item["group"]) if "group" in item else None,
            "notificationIDList": [Ref("notification", n) for n in item.get("notifications", [])],
        }
        for field_name in ("url", "hostname", "port"):
            if field_name in item:
                payload[field_name] = item[field_name]
        resources.append((Ref("monitor", key), payload))
    for key, item in cfg["maintenance"].items():
        resources.append(
            (
                Ref("maintenance", key),
                {
                    "title": name(key),
                    "description": marker,
                    "strategy": "recurring-weekday",
                    "active": item.get("active", False),
                    "intervalDay": 1,
                    "dateRange": [item["start_date"] + " 00:00:00"],
                    "timeRange": [
                        {"hours": int(item[t][:2]), "minutes": int(item[t][3:])}
                        for t in ("start", "end")
                    ],
                    "weekdays": item["weekdays"],
                    "daysOfMonth": [],
                    "timezoneOption": item["timezone"],
                },
            )
        )
    return resources


def resolve(value, ids):
    if isinstance(value, Ref):
        return ids.get(value, value)
    if isinstance(value, list):
        return [resolve(v, ids) for v in value]
    if isinstance(value, dict):
        return {k: resolve(v, ids) for k, v in value.items()}
    return value


def plan(api, cfg, env):
    resources = desired(cfg, env)
    rows = {
        "monitor": api.get_monitors(),
        "notification": api.get_notifications(),
        "maintenance": api.get_maintenances(),
    }
    for listing in rows.values():
        require(
            isinstance(listing, list)
            and all(
                isinstance(r, dict) and type(r.get("id")) is int and r["id"] > 0 for r in listing
            ),
            "Unexpected API list shape; refusing to plan",
        )
        require(len({r["id"] for r in listing}) == len(listing), "Duplicate API IDs")
    ids, matched = {}, {}
    for ref, payload in resources:
        identity = "title" if ref.kind == "maintenance" else "name"
        matches = [r for r in rows[ref.kind] if r.get(identity) == payload[identity]]
        require(len(matches) < 2, f"Ambiguous identity: {ref.kind}/{ref.key}")
        if matches:
            ids[ref], matched[ref] = matches[0]["id"], matches[0]
    actions = []
    for ref, payload in resources:
        payload = resolve(payload, ids)
        if ref not in ids:
            actions.append(Action("create", ref, payload))
            continue
        row = matched[ref]
        # applyExisting is a write-time instruction, not a persisted setting.
        fields = set(payload) - {"applyExisting"}
        drift = [k for k in fields if canonical(row.get(k), k) != canonical(payload[k], k)]
        require(not drift, f"Drift or identity collision: {ref.kind}/{ref.key}; no writes allowed")
    for key, item in cfg["maintenance"].items():
        ref = Ref("maintenance", key)
        expected = [resolve(Ref("monitor", m), ids) for m in item["monitors"]]
        current = []
        if ref in ids:
            linked = api.get_monitor_maintenance(ids[ref])
            require(
                isinstance(linked, list)
                and all(isinstance(r, dict) and type(r.get("id")) is int for r in linked),
                "Invalid maintenance links",
            )
            current = [r["id"] for r in linked]
        require(set(current) <= set(expected), f"Unexpected maintenance links: maintenance/{key}")
        if set(current) != set(expected):
            # Only append missing links, never remove any existing assignment.
            actions.append(
                Action(
                    "link",
                    ref,
                    {"id": ids.get(ref, ref), "monitors": [{"id": m} for m in expected]},
                )
            )
    return actions


def apply(api, cfg, env, reviewed):
    """Replan before every write. Acknowledgement failures are never retried."""
    pending = plan(api, cfg, env)
    require(pending == reviewed, "Plan changed before apply; run --plan again")
    count = 0
    while pending:
        action = pending[0]
        require(not unresolved(action.payload), "Unresolved dependency; refusing write")
        if action.verb == "create":
            response = getattr(api, "add_" + action.ref.kind)(**action.payload)
            id_key = {"monitor": "monitorID", "notification": "id", "maintenance": "maintenanceID"}[
                action.ref.kind
            ]
            require(
                isinstance(response, dict)
                and response.get("ok") is not False
                and type(response.get(id_key)) is int
                and response[id_key] > 0,
                "Uncertain create result; inspect server and re-plan; do not blindly retry",
            )
        else:
            response = api.add_monitor_maintenance(action.payload["id"], action.payload["monitors"])
            require(
                isinstance(response, dict) and response.get("ok") is not False,
                "Uncertain link result; inspect server and re-plan",
            )
        count += 1
        following = plan(api, cfg, env)
        require(
            not any(a.ref == action.ref and a.verb == action.verb for a in following),
            "Write not visible as expected; inspect server and re-plan",
        )
        # Other changes, including concurrent creates, can only reduce the pending list.
        require(
            {(a.verb, a.ref) for a in following} <= {(a.verb, a.ref) for a in pending},
            "Concurrent drift detected; inspect server and re-plan",
        )
        pending = following
    return count


def unresolved(value):
    if isinstance(value, Ref):
        return True
    if isinstance(value, dict):
        return any(unresolved(v) for v in value.values())
    if isinstance(value, list):
        return any(unresolved(v) for v in value)
    return False
