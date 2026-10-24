"""Shell shared by every page: navbar, consent banner and the gtag command log."""

from __future__ import annotations

import reflex as rx

from .state import ConsentState, LogState

PAGES = [
    ("/", "Home"),
    ("/events", "Events"),
    ("/ecommerce", "Ecommerce"),
    ("/consent", "Consent"),
    ("/configuration", "Configuration"),
    ("/admin/panel", "Admin (excluded)"),
]


def navbar() -> rx.Component:
    return rx.hstack(
        rx.hstack(
            rx.icon("chart-no-axes-combined", size=22, color=rx.color("amber", 10)),
            rx.heading("reflex-google-analytics-reactjs", size="4"),
            align="center",
            spacing="2",
        ),
        rx.spacer(),
        rx.hstack(
            *[rx.link(label, href=href, size="2", weight="medium") for href, label in PAGES],
            spacing="5",
            wrap="wrap",
        ),
        rx.color_mode.button(size="1"),
        width="100%",
        align="center",
        spacing="4",
        padding="1rem 1.5rem",
        border_bottom=f"1px solid {rx.color('gray', 5)}",
        background=rx.color("gray", 1),
        position="sticky",
        top="0",
        z_index="50",
    )


def consent_banner() -> rx.Component:
    """A minimal consent banner: its answer drives `consent` on the component."""
    return rx.cond(
        ConsentState.banner_open,
        rx.box(
            rx.hstack(
                rx.icon("cookie", size=22, color=rx.color("amber", 10)),
                rx.vstack(
                    rx.text("This site uses Google Analytics", weight="bold"),
                    rx.text(
                        "Until you answer, consent mode v2 denies storage "
                        "(the defaults come from google_analytics.toml).",
                        size="2",
                        color=rx.color("gray", 11),
                    ),
                    spacing="1",
                ),
                rx.spacer(),
                rx.button(
                    "Reject", variant="soft", color_scheme="gray", on_click=ConsentState.choose("none")
                ),
                rx.button("Analytics only", variant="soft", on_click=ConsentState.choose("analytics")),
                rx.button("Accept all", on_click=ConsentState.choose("all"), id="accept-all"),
                align="center",
                spacing="3",
                wrap="wrap",
            ),
            position="fixed",
            bottom="1rem",
            left="1rem",
            right="1rem",
            padding="1rem 1.25rem",
            border_radius="12px",
            background=rx.color("gray", 1),
            border=f"1px solid {rx.color('amber', 6)}",
            box_shadow="0 10px 30px rgba(0,0,0,.12)",
            z_index="60",
        ),
    )


def _command_badge(command: rx.Var[str]) -> rx.Component:
    return rx.badge(
        command,
        color_scheme=rx.match(
            command,
            ("event", "amber"),
            ("config", "blue"),
            ("consent", "green"),
            ("set", "violet"),
            "gray",
        ),
        variant="soft",
    )


def command_log() -> rx.Component:
    """Every gtag command react-ga4 issued, newest first (reported by `on_command`)."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("terminal", size=18),
                rx.heading("gtag commands", size="3"),
                rx.badge(LogState.command_count.to_string(), variant="surface"),
                rx.spacer(),
                rx.button("Clear", size="1", variant="ghost", on_click=LogState.clear),
                width="100%",
                align="center",
            ),
            rx.text(
                "In test_mode commands are queued in react-ga4 and never leave the browser.",
                size="1",
                color=rx.color("gray", 10),
            ),
            rx.scroll_area(
                rx.vstack(
                    rx.foreach(
                        LogState.commands,
                        lambda entry: rx.box(
                            rx.hstack(
                                rx.text(entry["n"], size="1", color=rx.color("gray", 9), width="2rem"),
                                _command_badge(entry["command"]),
                                rx.code(entry["target"], size="1"),
                                rx.spacer(),
                                rx.text(entry["time"], size="1", color=rx.color("gray", 9)),
                                width="100%",
                                align="center",
                                spacing="2",
                            ),
                            rx.cond(
                                entry["params"] != "",
                                rx.text(
                                    entry["params"],
                                    size="1",
                                    font_family="ui-monospace, monospace",
                                    color=rx.color("gray", 11),
                                    white_space="pre-wrap",
                                    word_break="break-all",
                                    padding_left="2rem",
                                ),
                            ),
                            padding_y="6px",
                            border_bottom=f"1px dashed {rx.color('gray', 4)}",
                            width="100%",
                            class_name="gtag-command",
                        ),
                    ),
                    spacing="0",
                    width="100%",
                ),
                type="auto",
                scrollbars="vertical",
                style={"height": "calc(100vh - 220px)"},
            ),
            width="100%",
            spacing="2",
        ),
        width="100%",
    )


def page_shell(title: str, description: str, *content: rx.Component) -> rx.Component:
    return rx.box(
        navbar(),
        rx.flex(
            rx.vstack(
                rx.heading(title, size="7"),
                rx.text(description, color=rx.color("gray", 11), size="3"),
                rx.divider(),
                *content,
                spacing="4",
                flex="1 1 520px",
                min_width="0",
            ),
            rx.box(command_log(), flex="0 1 460px", min_width="300px", position="sticky", top="80px"),
            gap="1.5rem",
            padding="1.5rem",
            align="start",
            wrap="wrap",
            max_width="1400px",
            margin="0 auto",
        ),
        consent_banner(),
        min_height="100vh",
        background=rx.color("gray", 2),
    )


def section(title: str, *children: rx.Component, icon: str = "circle") -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=18, color=rx.color("amber", 10)),
                rx.heading(title, size="4"),
                align="center",
            ),
            *children,
            spacing="3",
            width="100%",
        ),
        width="100%",
    )
