"""Configuration for Google Analytics, loaded from a file and/or the environment.

The usual setup is a ``google_analytics.toml`` next to ``rxconfig.py``::

    measurement_id = "G-XXXXXXXXXX"
    debug_mode = false
    only_in_production = true      # test mode (nothing sent) under `reflex run`
    exclude_paths = ["/admin/*"]

    [consent]                      # consent mode v2 defaults, optional
    analytics_storage = "denied"
    ad_storage = "denied"
    ad_user_data = "denied"
    ad_personalization = "denied"
    wait_for_update = 500

    [gtag_options]                 # anything else `gtag("config", id, {...})` accepts
    cookie_flags = "SameSite=None;Secure"

    [user_properties]
    app_flavor = "web"

The same keys can live under ``[google_analytics]`` in that file, under
``[tool.reflex-google-analytics]`` in ``pyproject.toml``, or in a JSON file.
Environment variables named ``GOOGLE_ANALYTICS_<FIELD>`` override single
fields, which keeps the real measurement id out of version control::

    GOOGLE_ANALYTICS_MEASUREMENT_ID=G-REAL123 reflex run --env prod
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import (
    CONSENT_TYPES,
    CONSENT_VALUES,
    DEFAULT_CONFIG_FILENAME,
    ENV_CONFIG_PATH,
    ENV_PREFIX,
    MEASUREMENT_ID_PATTERN,
    PYPROJECT_TABLE,
    TOML_TABLE,
)

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on 3.10 only
    import tomli as tomllib


class ConfigError(ValueError):
    """Raised for an invalid Google Analytics configuration."""


_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


def _parse_bool(name: str, raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise ConfigError(f"{name}: expected a boolean, got {raw!r}")


def _parse_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    return [str(item) for item in raw]


@dataclass
class ConsentDefaults:
    """Consent mode v2 defaults, sent as ``gtag("consent", "default", ...)``.

    Fields left as ``None`` are not sent, so Google applies its own default for
    them. ``wait_for_update`` (ms) gives a consent banner time to call
    ``update`` before the first hits go out; ``region`` limits these defaults to
    ISO 3166-2 regions (e.g. ``["ES", "FR", "US-CA"]``).
    """

    ad_storage: str | None = None
    ad_user_data: str | None = None
    ad_personalization: str | None = None
    analytics_storage: str | None = None
    functionality_storage: str | None = None
    personalization_storage: str | None = None
    security_storage: str | None = None
    wait_for_update: int | None = None
    region: list[str] | None = None

    def __post_init__(self) -> None:
        for name in CONSENT_TYPES:
            value = getattr(self, name)
            if value is not None and value not in CONSENT_VALUES:
                raise ConfigError(f"consent.{name}: expected 'granted' or 'denied', got {value!r}")
        if self.wait_for_update is not None and (
            not isinstance(self.wait_for_update, int) or self.wait_for_update < 0
        ):
            raise ConfigError("consent.wait_for_update: expected a non-negative integer (ms)")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ConsentDefaults:
        known = {f.name for f in dataclasses.fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ConfigError(f"consent: unknown keys {unknown}; expected some of {sorted(known)}")
        values = dict(data)
        if "region" in values:
            values["region"] = _parse_list(values["region"])
        return cls(**values)

    def to_gtag(self) -> dict[str, Any]:
        """The parameter object for ``gtag("consent", "default", ...)``."""
        return {key: value for key, value in dataclasses.asdict(self).items() if value not in (None, [])}


@dataclass
class GoogleAnalyticsConfig:
    """Everything the ``google_analytics`` component needs to set up gtag.js."""

    # GA4 measurement id (``G-XXXXXXXXXX``). Without it the component stays inert.
    measurement_id: str | None = None
    # More Google products fed by the same tag (``AW-...`` Ads, a second ``G-...``).
    additional_ids: list[str] = field(default_factory=list)
    # Master switch.
    enabled: bool = True
    # react-ga4 test mode: commands are queued and reported, gtag.js is never loaded.
    test_mode: bool = False
    # Force test mode unless the app runs with ``--env prod``.
    only_in_production: bool = False
    # Show hits in GA4 DebugView.
    debug_mode: bool = False
    # Send a page_view on every client-side navigation.
    track_page_views: bool = True
    # Include ``?query`` / ``#hash`` in the tracked page path.
    include_search: bool = True
    include_hash: bool = False
    # Routes not to track. ``/admin`` is exact, ``/admin/*`` is a prefix.
    exclude_paths: list[str] = field(default_factory=list)
    # Do not initialize when the browser sends Do-Not-Track or Global Privacy Control.
    respect_do_not_track: bool = False
    # Alternative gtag.js URL (first-party proxy / server-side tagging).
    gtag_url: str | None = None
    # CSP nonce for the injected gtag.js script.
    nonce: str | None = None
    # Consent mode v2 defaults (None: consent mode not used).
    consent: ConsentDefaults | None = None
    # Consent mode extras.
    ads_data_redaction: bool = False
    url_passthrough: bool = False
    # Extra ``config`` parameters (cookie_domain, cookie_flags, groups, ...).
    gtag_options: dict[str, Any] = field(default_factory=dict)
    # Initial ``user_properties``.
    user_properties: dict[str, Any] = field(default_factory=dict)
    # Where the values came from (for diagnostics; not a config field).
    source: str | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if isinstance(self.consent, Mapping):
            self.consent = ConsentDefaults.from_mapping(self.consent)
        self.additional_ids = _parse_list(self.additional_ids)
        self.exclude_paths = _parse_list(self.exclude_paths)
        if self.measurement_id is not None:
            self.measurement_id = str(self.measurement_id).strip() or None
        self.validate()

    # ------------------------------------------------------------ validation
    def validate(self) -> None:
        """Raise :class:`ConfigError` on malformed ids or paths."""
        for name, value in [("measurement_id", self.measurement_id)] + [
            ("additional_ids", item) for item in self.additional_ids
        ]:
            if value is not None and not MEASUREMENT_ID_PATTERN.match(value):
                raise ConfigError(
                    f"{name}: {value!r} is not a Google tag id (expected G-XXXXXXXXXX, GT-, AW- or DC-)"
                )
        if self.additional_ids and not self.measurement_id:
            raise ConfigError("additional_ids requires a primary measurement_id")
        for path in self.exclude_paths:
            if not path.startswith("/"):
                raise ConfigError(f"exclude_paths: {path!r} must start with '/'")

    # --------------------------------------------------------------- loaders
    @classmethod
    def field_names(cls) -> set[str]:
        return {f.name for f in dataclasses.fields(cls)} - {"source"}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any], *, source: str | None = None) -> GoogleAnalyticsConfig:
        """Build a config from a plain dict, rejecting unknown keys (typos)."""
        unknown = sorted(set(data) - cls.field_names())
        if unknown:
            raise ConfigError(
                f"{source or 'config'}: unknown keys {unknown}; valid keys are {sorted(cls.field_names())}"
            )
        return cls(**dict(data), source=source)

    @classmethod
    def from_file(cls, path: str | os.PathLike[str]) -> GoogleAnalyticsConfig:
        """Load a ``.toml`` or ``.json`` file.

        For TOML the keys may be top level or under ``[google_analytics]``; a
        ``pyproject.toml`` uses ``[tool.reflex-google-analytics]``.
        """
        file = Path(path)
        if not file.is_file():
            raise ConfigError(f"Google Analytics config file not found: {file}")
        if file.suffix.lower() == ".json":
            data = json.loads(file.read_text(encoding="utf-8"))
        else:
            data = tomllib.loads(file.read_text(encoding="utf-8"))
            if file.name == "pyproject.toml":
                for key in PYPROJECT_TABLE:
                    data = data.get(key, {})
            elif TOML_TABLE in data and isinstance(data[TOML_TABLE], dict):
                data = data[TOML_TABLE]
        if not isinstance(data, Mapping):
            raise ConfigError(f"{file}: expected a table/object at the top level")
        return cls.from_mapping(data, source=str(file))

    def with_env(self, environ: Mapping[str, str] | None = None) -> GoogleAnalyticsConfig:
        """Return a copy with ``GOOGLE_ANALYTICS_<FIELD>`` overrides applied."""
        environ = os.environ if environ is None else environ
        changes: dict[str, Any] = {}
        for f in dataclasses.fields(self):
            if f.name in {"source", "consent", "gtag_options", "user_properties"}:
                continue
            raw = environ.get(ENV_PREFIX + f.name.upper())
            if raw is None:
                continue
            current = getattr(self, f.name)
            if isinstance(current, bool):
                changes[f.name] = _parse_bool(ENV_PREFIX + f.name.upper(), raw)
            elif isinstance(current, list):
                changes[f.name] = _parse_list(raw)
            else:
                changes[f.name] = raw.strip() or None
        for name in ("gtag_options", "user_properties", "consent"):
            raw = environ.get(ENV_PREFIX + name.upper())
            if raw:
                try:
                    changes[name] = json.loads(raw)
                except json.JSONDecodeError as error:
                    raise ConfigError(f"{ENV_PREFIX}{name.upper()}: expected JSON ({error})") from error
        if not changes:
            return self
        source = f"{self.source or 'defaults'} + env"
        merged = {f: getattr(self, f) for f in self.field_names()}
        merged.update(changes)
        if isinstance(merged.get("consent"), ConsentDefaults):
            merged["consent"] = dataclasses.asdict(merged["consent"])
        return type(self)(**merged, source=source)

    # ------------------------------------------------------------ rendering
    def effective_test_mode(self, prod: bool | None = None) -> bool:
        """``test_mode``, or forced on outside production with ``only_in_production``."""
        if self.test_mode:
            return True
        if not self.only_in_production:
            return False
        return not (_is_prod_mode() if prod is None else prod)

    def to_props(self, *, prod: bool | None = None) -> dict[str, Any]:
        """Props for :func:`reflex_google_analytics_reactjs.google_analytics`."""
        props: dict[str, Any] = {
            "enabled": self.enabled,
            "test_mode": self.effective_test_mode(prod),
            "debug_mode": self.debug_mode,
            "track_page_views": self.track_page_views,
            "include_search": self.include_search,
            "include_hash": self.include_hash,
            "respect_do_not_track": self.respect_do_not_track,
            "ads_data_redaction": self.ads_data_redaction,
            "url_passthrough": self.url_passthrough,
        }
        if self.measurement_id:
            props["measurement_id"] = self.measurement_id
        if self.additional_ids:
            props["trackers"] = [{"trackingId": tid} for tid in [self.measurement_id, *self.additional_ids]]
        if self.exclude_paths:
            props["exclude_paths"] = list(self.exclude_paths)
        if self.gtag_url:
            props["gtag_url"] = self.gtag_url
        if self.nonce:
            props["nonce"] = self.nonce
        if self.consent is not None and self.consent.to_gtag():
            props["default_consent"] = self.consent.to_gtag()
        if self.gtag_options:
            props["gtag_options"] = dict(self.gtag_options)
        if self.user_properties:
            props["user_properties"] = dict(self.user_properties)
        return props


def _is_prod_mode() -> bool:
    try:
        from reflex.utils.exec import is_prod_mode
    except ImportError:  # pragma: no cover - very old/new Reflex
        return os.environ.get("REFLEX_ENV_MODE", "dev").lower() == "prod"
    return is_prod_mode()


def find_config_file(start: str | os.PathLike[str] | None = None) -> Path | None:
    """The config file that :func:`load_config` would use, if any.

    Order: ``$GOOGLE_ANALYTICS_CONFIG``, ``google_analytics.toml`` in the app
    directory, then ``pyproject.toml`` if it has ``[tool.reflex-google-analytics]``.
    """
    env_path = os.environ.get(ENV_CONFIG_PATH)
    if env_path:
        return Path(env_path)
    base = Path(start) if start is not None else Path.cwd()
    candidate = base / DEFAULT_CONFIG_FILENAME
    if candidate.is_file():
        return candidate
    pyproject = base / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            return None
        if data.get(PYPROJECT_TABLE[0], {}).get(PYPROJECT_TABLE[1]) is not None:
            return pyproject
    return None


def load_config(
    path: str | os.PathLike[str] | None = None,
    *,
    env: bool = True,
    environ: Mapping[str, str] | None = None,
) -> GoogleAnalyticsConfig:
    """Load the Google Analytics config for the current Reflex app.

    Args:
        path: An explicit file. Defaults to :func:`find_config_file`.
        env: Apply ``GOOGLE_ANALYTICS_*`` overrides on top of the file.
        environ: Mapping used instead of ``os.environ`` (tests).

    Returns:
        The merged, validated configuration (an empty, inert one if nothing is set).
    """
    file = Path(path) if path is not None else find_config_file()
    config = GoogleAnalyticsConfig.from_file(file) if file is not None else GoogleAnalyticsConfig()
    return config.with_env(environ) if env else config
