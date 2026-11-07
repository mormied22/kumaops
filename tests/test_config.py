from pathlib import Path

import pytest
import yaml

from kumaops.config import ConfigError, load_config


@pytest.mark.parametrize(
    "content",
    [
        "version: 1\nversion: 1\nnamespace: demo",
        "version: 1\nnamespace: demo\nmonitors: {a: {type: typo}}",
        "version: 1\nnamespace: demo\nunknown: true",
        "!!python/object:object {}",
    ],
)
def test_invalid_yaml_rejected(tmp_path, content):
    path = tmp_path / "input.yaml"
    path.write_text(content)
    with pytest.raises(ConfigError):
        load_config(path)


@pytest.mark.parametrize(
    "section,key,field,value",
    [
        ("monitors", "website", "group", "missing"),
        ("monitors", "website", "notifications", ["missing"]),
        ("monitors", "website", "interval", True),
        ("monitors", "website", "url", "https://user:password@example.com"),
        ("maintenance", "weekly", "weekdays", [True]),
        ("maintenance", "weekly", "weekdays", [7]),
        ("maintenance", "weekly", "timezone", "Not/AZone"),
        ("maintenance", "weekly", "end", "02:00"),
        ("maintenance", "weekly", "active", "true"),
        ("maintenance", "weekly", "monitors", []),
    ],
)
def test_invalid_fields_rejected(cfg, tmp_path, section, key, field, value):
    cfg[section][key][field] = value
    path = tmp_path / "input.yaml"
    path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ConfigError):
        load_config(path)


def test_sample_config_valid():
    cfg = load_config(Path(__file__).parents[1] / "examples" / "config.yaml")
    assert cfg["maintenance"]["weekly"]["weekdays"] == [0]
