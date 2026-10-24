"""A route listed in exclude_paths: navigating here sends no page_view."""

from __future__ import annotations

import reflex as rx

from ..layout import page_shell, section


def admin() -> rx.Component:
    return page_shell(
        "Admin panel",
        "This route matches exclude_paths = ['/admin/*'], so it does not produce a page_view.",
        section(
            "Excluded route",
            rx.text("Check the command log: landing here added no page_view.", size="2"),
            icon="eye-off",
        ),
    )


rx.page(route="/admin/panel", title="Admin | GA4 demo")(admin)
