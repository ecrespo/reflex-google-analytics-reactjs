"""Recommended GA4 events, a custom event form, user id and manual page views."""

from __future__ import annotations

import reflex as rx
import reflex_google_analytics_reactjs as rga

from ..layout import page_shell, section
from ..state import EventsState


def events() -> rx.Component:
    return page_shell(
        "Events",
        "Each button returns an rx.call_script to window.__reflexGA; the event name is validated in Python "
        "against GA4's rules before it is sent.",
        section(
            "Recommended events",
            rx.hstack(
                rx.button("login", on_click=rga.login(method="Google"), id="btn-login"),
                rx.button("sign_up", on_click=rga.sign_up(method="email")),
                rx.button("search", on_click=rga.search("arepas")),
                rx.button(
                    "share", on_click=rga.share(method="whatsapp", content_type="article", item_id="a-42")
                ),
                rx.button("select_content", on_click=rga.select_content("video", "intro")),
                rx.button("generate_lead", on_click=rga.generate_lead(value=25, currency="USD")),
                rx.button("tutorial_begin", on_click=rga.tutorial_begin()),
                rx.button(
                    "exception", color_scheme="red", variant="soft", on_click=rga.exception("demo error")
                ),
                wrap="wrap",
                spacing="2",
            ),
            icon="zap",
        ),
        section(
            "Custom event",
            rx.hstack(
                rx.input(
                    value=EventsState.name,
                    on_change=EventsState.set_name,
                    placeholder="event_name",
                    id="custom-name",
                ),
                rx.input(
                    value=EventsState.param_key, on_change=EventsState.set_param_key, placeholder="parameter"
                ),
                rx.input(
                    value=EventsState.param_value, on_change=EventsState.set_param_value, placeholder="value"
                ),
                rx.button("Send", on_click=EventsState.send_custom, id="custom-send"),
                wrap="wrap",
                spacing="2",
            ),
            rx.cond(
                EventsState.error != "",
                rx.callout(EventsState.error, icon="triangle-alert", color_scheme="red", size="1"),
            ),
            rx.text(
                "Try an invalid name such as '1-event' or 'ga_reserved'.",
                size="1",
                color=rx.color("gray", 10),
            ),
            icon="pencil",
        ),
        section(
            "User",
            rx.hstack(
                rx.input(
                    value=EventsState.user_id,
                    on_change=EventsState.set_user_id_input,
                    placeholder="user id (no PII)",
                ),
                rx.button("set_user_id", on_click=EventsState.apply_user_id),
                rx.button(
                    "user_properties",
                    variant="soft",
                    on_click=rga.set_user_properties(plan="pro", country="VE"),
                ),
                rx.button(
                    "client_id", variant="outline", on_click=rga.get_client_id(EventsState.receive_client_id)
                ),
                wrap="wrap",
                spacing="2",
            ),
            rx.cond(
                EventsState.client_id != "", rx.text("client_id: ", rx.code(EventsState.client_id), size="2")
            ),
            icon="user",
        ),
        section(
            "Manual page view",
            rx.text("For modals, wizard steps or views that do not change the route.", size="2"),
            rx.button(
                "Send /events/virtual-modal",
                variant="soft",
                on_click=rga.page_view("/events/virtual-modal", "Virtual modal"),
            ),
            icon="file",
        ),
    )


rx.page(route="/events", title="Events | GA4 demo")(events)
