"""Constants shared by the component, the config loader and the actions."""

from __future__ import annotations

import re

# react-ga4 release this package is built and tested against.
REACT_GA4_VERSION = "3.0.1"

# Default gtag.js loader. Override with ``gtag_url`` (e.g. a first-party proxy).
DEFAULT_GTAG_URL = "https://www.googletagmanager.com/gtag/js"

# Name of the config file looked up next to ``rxconfig.py``.
DEFAULT_CONFIG_FILENAME = "google_analytics.toml"

# Environment variables. ``GOOGLE_ANALYTICS_CONFIG`` points at a config file;
# the others override single fields of whatever file was loaded.
ENV_PREFIX = "GOOGLE_ANALYTICS_"
ENV_CONFIG_PATH = f"{ENV_PREFIX}CONFIG"

# Table used inside pyproject.toml / a shared TOML file.
PYPROJECT_TABLE = ("tool", "reflex-google-analytics")
TOML_TABLE = "google_analytics"

# Order of the app wrap installed by ``install``. Low numbers sit closest to the
# pages, inside every provider Reflex adds, so event triggers can reach State.
APP_WRAP_ORDER = 1
APP_WRAP_NAME = "GoogleAnalytics"

# Browser registry populated by the JSX bridge.
BROWSER_API = "window.__reflexGA"

# GA4 measurement ids (G-), Google tag ids (GT-), Google Ads (AW-) and
# Floodlight (DC-) can all be configured through gtag.js.
MEASUREMENT_ID_PATTERN = re.compile(r"^(G|GT|AW|DC)-[A-Z0-9]+$")

# Consent mode v2.
CONSENT_TYPES = (
    "ad_storage",
    "ad_user_data",
    "ad_personalization",
    "analytics_storage",
    "functionality_storage",
    "personalization_storage",
    "security_storage",
)
CONSENT_VALUES = ("granted", "denied")
GRANTED = "granted"
DENIED = "denied"

# A conservative "deny until the user says yes" default (EEA-style).
DENY_ALL_CONSENT: dict[str, str] = {
    "ad_storage": DENIED,
    "ad_user_data": DENIED,
    "ad_personalization": DENIED,
    "analytics_storage": DENIED,
    "functionality_storage": GRANTED,
    "personalization_storage": DENIED,
    "security_storage": GRANTED,
}
