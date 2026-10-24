"""Config file loading, validation, env overrides and prop generation."""

import json
from pathlib import Path

import pytest
import reflex_google_analytics_reactjs as rga
from reflex_google_analytics_reactjs.config import GoogleAnalyticsConfig

TOML = """
measurement_id = "G-ABC123"
additional_ids = ["AW-999"]
debug_mode = true
exclude_paths = ["/admin/*"]

[consent]
analytics_storage = "denied"
ad_storage = "denied"
wait_for_update = 500
region = ["ES", "FR"]

[gtag_options]
cookie_flags = "SameSite=None;Secure"

[user_properties]
tier = "gold"
"""


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_top_level_toml(tmp_path):
    config = rga.load_config(write(tmp_path, "ga.toml", TOML), env=False)
    assert config.measurement_id == "G-ABC123"
    assert config.additional_ids == ["AW-999"]
    assert config.consent.to_gtag() == {
        "ad_storage": "denied",
        "analytics_storage": "denied",
        "wait_for_update": 500,
        "region": ["ES", "FR"],
    }
    assert config.source.endswith("ga.toml")


def test_loads_namespaced_table_and_pyproject(tmp_path):
    namespaced = write(tmp_path, "shared.toml", '[google_analytics]\nmeasurement_id = "G-T1"\n')
    assert rga.load_config(namespaced, env=False).measurement_id == "G-T1"
    pyproject = write(tmp_path, "pyproject.toml", '[tool.reflex-google-analytics]\nmeasurement_id = "G-T2"\n')
    assert rga.load_config(pyproject, env=False).measurement_id == "G-T2"


def test_loads_json(tmp_path):
    path = write(tmp_path, "ga.json", json.dumps({"measurement_id": "G-J1", "test_mode": True}))
    config = rga.load_config(path, env=False)
    assert config.measurement_id == "G-J1"
    assert config.test_mode is True


def test_discovery_order(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GOOGLE_ANALYTICS_CONFIG", raising=False)
    assert rga.find_config_file() is None
    assert rga.load_config(env=False) == GoogleAnalyticsConfig()

    write(tmp_path, "pyproject.toml", '[tool.reflex-google-analytics]\nmeasurement_id = "G-PY"\n')
    assert rga.find_config_file().name == "pyproject.toml"

    write(tmp_path, rga.DEFAULT_CONFIG_FILENAME, 'measurement_id = "G-FILE"\n')
    assert rga.load_config(env=False).measurement_id == "G-FILE"

    other = write(tmp_path, "other.toml", 'measurement_id = "G-ENV"\n')
    monkeypatch.setenv("GOOGLE_ANALYTICS_CONFIG", str(other))
    assert rga.load_config(env=False).measurement_id == "G-ENV"


def test_pyproject_without_table_is_ignored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GOOGLE_ANALYTICS_CONFIG", raising=False)
    write(tmp_path, "pyproject.toml", '[project]\nname = "x"\n')
    assert rga.find_config_file() is None


def test_env_overrides(tmp_path):
    path = write(tmp_path, "ga.toml", TOML)
    environ = {
        "GOOGLE_ANALYTICS_MEASUREMENT_ID": "G-PROD42",
        "GOOGLE_ANALYTICS_TEST_MODE": "true",
        "GOOGLE_ANALYTICS_DEBUG_MODE": "0",
        "GOOGLE_ANALYTICS_EXCLUDE_PATHS": "/a,/b/*",
        "GOOGLE_ANALYTICS_CONSENT": '{"analytics_storage": "granted"}',
    }
    config = rga.load_config(path, environ=environ)
    assert config.measurement_id == "G-PROD42"
    assert config.test_mode is True
    assert config.debug_mode is False
    assert config.exclude_paths == ["/a", "/b/*"]
    assert config.consent.to_gtag() == {"analytics_storage": "granted"}
    assert config.source.endswith("+ env")
    # Untouched fields survive the merge.
    assert config.gtag_options == {"cookie_flags": "SameSite=None;Secure"}


@pytest.mark.parametrize(
    "data, message",
    [
        ({"measurement_id": "UA-123-1"}, "not a Google tag id"),
        ({"measurement_id": "G-OK1", "mesurement_id": "typo"}, "unknown keys"),
        ({"additional_ids": ["AW-1"]}, "requires a primary"),
        ({"measurement_id": "G-OK1", "exclude_paths": ["admin"]}, "must start with '/'"),
        ({"measurement_id": "G-OK1", "consent": {"analytics_storage": "yes"}}, "granted' or 'denied"),
        ({"measurement_id": "G-OK1", "consent": {"cookies": "denied"}}, "unknown keys"),
        ({"measurement_id": "G-OK1", "consent": {"wait_for_update": -5}}, "non-negative"),
    ],
)
def test_validation_errors(data, message):
    with pytest.raises(rga.ConfigError, match=message):
        GoogleAnalyticsConfig.from_mapping(data)


def test_bad_env_values():
    config = GoogleAnalyticsConfig(measurement_id="G-OK1")
    with pytest.raises(rga.ConfigError, match="boolean"):
        config.with_env({"GOOGLE_ANALYTICS_ENABLED": "maybe"})
    with pytest.raises(rga.ConfigError, match="JSON"):
        config.with_env({"GOOGLE_ANALYTICS_GTAG_OPTIONS": "{nope"})


def test_missing_file():
    with pytest.raises(rga.ConfigError, match="not found"):
        rga.load_config("/nonexistent/ga.toml")


def test_to_props(tmp_path):
    props = rga.load_config(write(tmp_path, "ga.toml", TOML), env=False).to_props(prod=True)
    assert props["measurement_id"] == "G-ABC123"
    assert props["trackers"] == [{"trackingId": "G-ABC123"}, {"trackingId": "AW-999"}]
    assert props["default_consent"]["wait_for_update"] == 500
    assert props["exclude_paths"] == ["/admin/*"]
    assert props["gtag_options"] == {"cookie_flags": "SameSite=None;Secure"}
    assert props["user_properties"] == {"tier": "gold"}
    assert props["test_mode"] is False
    assert "gtag_url" not in props and "nonce" not in props


def test_only_in_production_forces_test_mode():
    config = GoogleAnalyticsConfig(measurement_id="G-OK1", only_in_production=True)
    assert config.effective_test_mode(prod=False) is True
    assert config.effective_test_mode(prod=True) is False
    assert GoogleAnalyticsConfig(measurement_id="G-OK1", test_mode=True).effective_test_mode(prod=True)


def test_demo_config_file_is_valid():
    demo = Path(__file__).parents[1] / "google_analytics_reactjs_demo" / rga.DEFAULT_CONFIG_FILENAME
    config = rga.load_config(demo, env=False)
    assert config.test_mode is True
    assert config.consent.analytics_storage == "denied"
