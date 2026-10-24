"""Shows the config file the app loaded and the props it produced."""

from __future__ import annotations

import json
from pathlib import Path

import reflex as rx
import reflex_google_analytics_reactjs as rga

from ..layout import page_shell, section

_CONFIG_FILE = rga.find_config_file()
_CONFIG = rga.load_config()
_TOML = Path(_CONFIG_FILE).read_text(encoding="utf-8") if _CONFIG_FILE else "# no config file found"
_PROPS = json.dumps(_CONFIG.to_props(), indent=2, ensure_ascii=False)

ENV_ROWS = [
    ("GOOGLE_ANALYTICS_CONFIG", "Path to another .toml/.json file"),
    ("GOOGLE_ANALYTICS_MEASUREMENT_ID", "Real G-XXXXXXXXXX (kept out of the repo)"),
    ("GOOGLE_ANALYTICS_TEST_MODE", "true / false"),
    ("GOOGLE_ANALYTICS_ENABLED", "true / false"),
    ("GOOGLE_ANALYTICS_DEBUG_MODE", "true / false"),
    ("GOOGLE_ANALYTICS_EXCLUDE_PATHS", "/admin/*,/preview"),
    ("GOOGLE_ANALYTICS_CONSENT", 'JSON: {"analytics_storage": "granted"}'),
]


def configuration() -> rx.Component:
    return page_shell(
        "Configuration",
        "rga.load_config() looks for GOOGLE_ANALYTICS_CONFIG, then google_analytics.toml next to rxconfig.py, then "
        "[tool.reflex-google-analytics] in pyproject.toml; environment variables are applied last.",
        section(
            "Loaded file",
            rx.text("Source: ", rx.code(str(_CONFIG.source)), size="2"),
            rx.code_block(_TOML, language="toml", width="100%"),
            icon="file-cog",
        ),
        section(
            "Resulting props",
            rx.code_block(_PROPS, language="json", width="100%"),
            icon="braces",
        ),
        section(
            "Environment variables",
            rx.table.root(
                rx.table.body(
                    *[rx.table.row(rx.table.cell(rx.code(k)), rx.table.cell(v)) for k, v in ENV_ROWS]
                ),
                size="1",
                width="100%",
            ),
            icon="variable",
        ),
    )


rx.page(route="/configuration", title="Configuration | GA4 demo")(configuration)
