"""Strict schema: no arbitrary API payloads or secret interpolation."""

import re
from datetime import date, time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml


class ConfigError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ConfigError("YAML keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor("tag:yaml.org,2002:map", unique_mapping)


def require(ok, message):
    if not ok:
        raise ConfigError(message)


def mapping(value, allowed):
    require(isinstance(value, dict), "Expected a mapping")
    require(not (set(value) - set(allowed)), "Unknown configuration field")


def text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 512


def http_url(value):
    if not text(value):
        return False
    try:
        parts = urlsplit(value)
        _ = parts.port  # Access validates malformed and out-of-range ports.
        return (
            parts.scheme in {"https", "http"}
            and bool(parts.hostname)
            and parts.username is None
            and parts.password is None
            and not parts.fragment
        )
    except ValueError:
        return False


def references(value, choices):
    require(
        isinstance(value, list) and all(isinstance(v, str) for v in value),
        "References must be a list of keys",
    )
    require(
        len(set(value)) == len(value) and set(value) <= set(choices),
        "Unknown or duplicate reference",
    )


def load_config(path):
    try:
        raw = path.read_text(encoding="utf-8")
        require(len(raw) <= 100_000, "Configuration is too large")
        cfg = yaml.load(raw, Loader=UniqueLoader)
    except (yaml.YAMLError, RecursionError, TypeError) as from_error:
        raise ConfigError("Invalid YAML; check syntax and quote dates/times") from from_error
    mapping(cfg, {"version", "namespace", "notifications", "groups", "monitors", "maintenance"})
    require(type(cfg.get("version")) is int and cfg["version"] == 1, "Expected version: 1")
    require(
        isinstance(cfg.get("namespace"), str)
        and re.fullmatch(r"[a-z][a-z0-9-]{0,31}", cfg["namespace"]),
        "Invalid namespace",
    )
    for section in ("notifications", "groups", "monitors", "maintenance"):
        cfg.setdefault(section, {})
        require(isinstance(cfg[section], dict), "Sections must be mappings")
        for key in cfg[section]:
            require(re.fullmatch(r"[a-z][a-z0-9-]{0,47}", key), "Invalid resource key")
    require(not (set(cfg["groups"]) & set(cfg["monitors"])), "Group and monitor keys overlap")
    for item in cfg["notifications"].values():
        mapping(item, {"webhook_env", "prefix"})
        require(
            isinstance(item.get("webhook_env"), str)
            and re.fullmatch(r"[A-Z][A-Z0-9_]*", item["webhook_env"]),
            "Invalid webhook_env",
        )
        require(text(item.get("prefix", "Status changed")), "Invalid Discord prefix")
    for item in cfg["groups"].values():
        mapping(item, set())
    for item in cfg["monitors"].values():
        mapping(item, {"type", "url", "hostname", "port", "interval", "group", "notifications"})
        kind = item.get("type")
        require(kind in {"http", "ping", "port"}, "Supported monitors: http, ping, port")
        require(
            type(item.get("interval", 60)) is int and 20 <= item.get("interval", 60) <= 86400,
            "Invalid interval",
        )
        if kind == "http":
            require(http_url(item.get("url")), "HTTP monitor needs a valid URL without credentials")
            require("hostname" not in item and "port" not in item, "Unexpected HTTP fields")
        else:
            require(
                text(item.get("hostname")) and "url" not in item, "Network monitor needs hostname"
            )
            if kind == "port":
                require(
                    type(item.get("port")) is int and 1 <= item["port"] <= 65535,
                    "Port must be 1..65535",
                )
            else:
                require("port" not in item, "Ping cannot specify port")
        require("group" not in item or item["group"] in cfg["groups"], "Unknown group")
        references(item.get("notifications", []), cfg["notifications"])
    for item in cfg["maintenance"].values():
        mapping(item, {"timezone", "weekdays", "start_date", "start", "end", "active", "monitors"})
        try:
            ZoneInfo(item["timezone"])
            date.fromisoformat(item["start_date"])
            for field in ("start", "end"):
                require(
                    isinstance(item[field], str) and re.fullmatch(r"\d{2}:\d{2}", item[field]),
                    "Time must be quoted HH:MM",
                )
                time.fromisoformat(item[field])
        except (KeyError, ValueError, TypeError, ZoneInfoNotFoundError) as exc:
            raise ConfigError("Invalid maintenance date, time or IANA timezone") from exc
        require(item["start"] < item["end"], "Maintenance must end later on the same day")
        days = item.get("weekdays")
        require(
            isinstance(days, list)
            and bool(days)
            and all(type(d) is int and 0 <= d <= 6 for d in days)
            and len(days) == len(set(days)),
            "Invalid weekdays",
        )
        require(type(item.get("active", False)) is bool, "active must be boolean")
        references(item.get("monitors", []), cfg["monitors"])
        require(bool(item.get("monitors")), "Maintenance needs monitors")
    return cfg
