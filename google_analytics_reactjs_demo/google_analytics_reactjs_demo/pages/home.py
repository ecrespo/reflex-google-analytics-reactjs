"""Landing page: how the component is mounted and the page views it records."""

from __future__ import annotations

import reflex as rx

from ..layout import page_shell, section
from ..state import LogState

SNIPPET = """import reflex as rx
import reflex_google_analytics_reactjs as rga

app = rx.App()
# Reads google_analytics.toml (+ GOOGLE_ANALYTICS_* env vars) and wraps
# every page: one initialization, one page_view per navigation.
rga.install(app)
"""


def index() -> rx.Component:
    return page_shell(
        "Google Analytics 4 in Reflex",
        "react-ga4 wrapped as a Reflex component: config file, automatic page views, "
        "consent mode v2 and GA4 events from Python.",
        section(
            "One-line setup",
            rx.code_block(SNIPPET, language="python", width="100%"),
            rx.text(
                "Move between the pages in the menu: every route change sends a ",
                rx.code("page_view"),
                " with the path and the title. /admin/panel is in exclude_paths and is not tracked.",
                size="2",
            ),
            icon="plug",
        ),
        section(
            "Tracker status",
            rx.code_block(LogState.status_json, language="json", width="100%"),
            rx.button("Refresh status", size="2", variant="soft", on_click=LogState.refresh_status),
            icon="activity",
        ),
        section(
            "Recorded page views",
            rx.cond(
                LogState.page_views.length() > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Path"), rx.table.column_header_cell("Title")
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            LogState.page_views,
                            lambda pv: rx.table.row(
                                rx.table.cell(rx.code(pv["path"])),
                                rx.table.cell(pv["title"]),
                                class_name="page-view-row",
                            ),
                        )
                    ),
                    width="100%",
                    size="1",
                ),
                rx.text("None yet.", color=rx.color("gray", 10), size="2"),
            ),
            icon="route",
        ),
    )


rx.page(route="/", title="Home | GA4 demo")(index)
