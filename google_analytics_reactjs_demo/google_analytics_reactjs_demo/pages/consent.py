"""Consent mode v2: defaults from the TOML, updates from the banner, opt-out."""

from __future__ import annotations

import reflex as rx
import reflex_google_analytics_reactjs as rga

from ..layout import page_shell, section
from ..state import ConsentState


def consent() -> rx.Component:
    return page_shell(
        "Consent",
        "The defaults ([consent] in google_analytics.toml) are sent before config. "
        "The banner choice lives in ConsentState and reaches the component through the consent prop.",
        section(
            "Current state",
            rx.table.root(
                rx.table.body(
                    rx.foreach(
                        ConsentState.consent_rows,
                        lambda row: rx.table.row(
                            rx.table.cell(rx.code(row[0])),
                            rx.table.cell(
                                rx.badge(row[1], color_scheme=rx.cond(row[1] == "granted", "green", "red"))
                            ),
                        ),
                    )
                ),
                size="1",
                width="100%",
            ),
            rx.hstack(
                rx.button("Accept all", on_click=ConsentState.choose("all")),
                rx.button("Analytics only", variant="soft", on_click=ConsentState.choose("analytics")),
                rx.button(
                    "Reject", variant="soft", color_scheme="gray", on_click=ConsentState.choose("none")
                ),
                rx.button("Ask again", variant="ghost", on_click=ConsentState.reset_choice),
                wrap="wrap",
            ),
            icon="shield-check",
        ),
        section(
            "Direct update",
            rx.text("Without going through the State, using the action helpers:", size="2"),
            rx.hstack(
                rx.button(
                    "grant_consent('analytics_storage')",
                    variant="outline",
                    on_click=rga.grant_consent("analytics_storage"),
                ),
                rx.button(
                    "deny_consent()", variant="outline", color_scheme="red", on_click=rga.deny_consent()
                ),
                wrap="wrap",
            ),
            icon="toggle-right",
        ),
        section(
            "Visitor opt-out",
            rx.text(
                "rga.opt_out() sets window['ga-disable-<ID>'] (Google's official mechanism) and remembers it in "
                "localStorage for later visits.",
                size="2",
            ),
            rx.hstack(
                rx.switch(checked=ConsentState.opted_out, on_change=lambda _v: ConsentState.toggle_opt_out()),
                rx.text(rx.cond(ConsentState.opted_out, "Opt-out active", "Measurement allowed")),
                align="center",
            ),
            icon="ban",
        ),
    )


rx.page(route="/consent", title="Consent | GA4 demo")(consent)
