"""reflex-google-analytics-reactjs demo app.

Six pages (home, events, ecommerce, consent, configuration and an excluded
admin route) plus a live log of every gtag command the component issues.

    cd google_analytics_reactjs_demo && uv run reflex run

The tracker is configured by google_analytics.toml in this directory. It ships
with test_mode = true, so nothing is sent to Google; set a real id with
GOOGLE_ANALYTICS_MEASUREMENT_ID and GOOGLE_ANALYTICS_TEST_MODE=false.
"""

from __future__ import annotations

import reflex as rx
import reflex_google_analytics_reactjs as rga

from . import pages  # noqa: F401  - importing the modules registers their @rx.page
from .state import ConsentState, LogState

app = rx.App(
    style={"font_family": "Inter, ui-sans-serif, system-ui, sans-serif"},
)

# One component around every page. The event triggers feed the log panel and
# `consent` follows the banner choice stored in ConsentState.
rga.install(
    app,
    consent=ConsentState.consent,
    on_ready=LogState.on_ready,
    on_page_view=LogState.on_page_view,
    on_command=LogState.on_command,
)
