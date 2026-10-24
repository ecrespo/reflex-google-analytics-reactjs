"""Send Google Analytics hits from Python.

Every helper returns an ``rx.call_script`` event that talks to the
``window.__reflexGA`` API registered by the component, so it can be used
directly as a trigger or returned/yielded from an event handler::

    rx.button("Buy", on_click=rga.event("click_buy", {"plan": "pro"}))

    class State(rx.State):
        @rx.event
        def checkout(self):
            ...
            return rga.purchase(transaction_id=order.id, value=order.total, currency="EUR", items=items)

Calls made before gtag.js is initialized are queued, and when tracking is
disabled (``enabled=False``, no measurement id, Do-Not-Track) they are no-ops.
Arguments must be plain Python values (str, int, float, bool, list, dict):
read State values inside a handler and return the helper from there.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from typing import Any, TypedDict

import reflex as rx
from reflex.event import EventSpec

from .constants import BROWSER_API, CONSENT_TYPES, DENIED, GRANTED

# GA4 naming rules: letter first, then letters/digits/underscores, at most 40 chars.
_EVENT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
_RESERVED_PREFIXES = ("google_", "ga_", "firebase_")
# Names GA4 reserves for automatically collected events.
_RESERVED_NAMES = frozenset(
    {
        "ad_activeview",
        "ad_click",
        "ad_exposure",
        "ad_query",
        "ad_reward",
        "adunit_exposure",
        "app_background",
        "app_clear_data",
        "app_exception",
        "app_remove",
        "app_store_refund",
        "app_store_subscription_cancel",
        "app_store_subscription_convert",
        "app_store_subscription_renew",
        "app_update",
        "app_upgrade",
        "dynamic_link_app_open",
        "dynamic_link_app_update",
        "dynamic_link_first_open",
        "error",
        "first_open",
        "first_visit",
        "in_app_purchase",
        "notification_dismiss",
        "notification_foreground",
        "notification_open",
        "notification_receive",
        "os_update",
        "session_start",
        "session_start_with_rollout",
        "user_engagement",
    }
)


class Item(TypedDict, total=False):
    """A GA4 ecommerce item. ``item_id`` or ``item_name`` is required."""

    item_id: str
    item_name: str
    affiliation: str
    coupon: str
    discount: float
    index: int
    item_brand: str
    item_category: str
    item_category2: str
    item_category3: str
    item_list_id: str
    item_list_name: str
    item_variant: str
    location_id: str
    price: float
    quantity: int


def validate_event_name(name: str) -> str:
    """Return ``name`` if GA4 accepts it as an event name, else raise ``ValueError``."""
    if not isinstance(name, str) or not _EVENT_NAME.match(name):
        raise ValueError(
            f"Invalid GA4 event name {name!r}: start with a letter, use letters, digits and "
            "underscores only, at most 40 characters"
        )
    if name.startswith(_RESERVED_PREFIXES) or name in _RESERVED_NAMES:
        raise ValueError(f"{name!r} is reserved by Google Analytics")
    return name


def _clean(params: Mapping[str, Any] | None) -> dict[str, Any]:
    return {key: value for key, value in (params or {}).items() if value is not None}


def _call(method: str, *args: Any, callback: Any = None) -> EventSpec:
    js_args = ", ".join(json.dumps(arg, default=str) for arg in args)
    script = (
        f"(() => {{ const ga = {BROWSER_API};"
        " if (!ga) { console.warn('reflex-google-analytics: component not mounted'); return null; }"
        f" return ga.{method}({js_args}); }})()"
    )
    if callback is not None:
        return rx.call_script(script, callback=callback)
    return rx.call_script(script)


# ------------------------------------------------------------------ generic
def gtag(command: str, *args: Any) -> EventSpec:
    """Raw ``gtag(command, ...args)``, e.g. ``gtag("set", {"currency": "EUR"})``."""
    return _call("gtag", command, *args)


def event(name: str, params: Mapping[str, Any] | None = None, /, **extra: Any) -> EventSpec:
    """A GA4 event: ``event("tutorial_begin")`` or ``event("level_up", level=3)``."""
    return _call("event", validate_event_name(name), _clean({**(params or {}), **extra}))


def page_view(path: str | None = None, title: str | None = None, **params: Any) -> EventSpec:
    """A manual page_view (virtual pages, modals, wizard steps).

    Defaults to the current location and ``document.title``.
    """
    return _call("pageView", path, title, _clean(params))


def set_params(**fields: Any) -> EventSpec:
    """``gtag("set", {...})``: parameters attached to every following event."""
    return _call("set", _clean(fields))


def set_user_id(user_id: str | None) -> EventSpec:
    """Associate hits with a signed-in user (``None`` clears it). Never send PII."""
    return _call("setUserId", user_id)


def set_user_properties(**properties: Any) -> EventSpec:
    """``gtag("set", "user_properties", {...})``. Register them as custom dimensions in GA4."""
    return _call("setUserProperties", _clean(properties))


# ---------------------------------------------------------------- consent
def _consent_values(types: Iterable[str], value: str) -> dict[str, str]:
    chosen = tuple(types) or CONSENT_TYPES
    unknown = sorted(set(chosen) - set(CONSENT_TYPES))
    if unknown:
        raise ValueError(f"Unknown consent types {unknown}; expected some of {list(CONSENT_TYPES)}")
    return dict.fromkeys(chosen, value)


def update_consent(**values: str) -> EventSpec:
    """``gtag("consent", "update", {...})``, e.g. ``update_consent(analytics_storage="granted")``."""
    for key, value in values.items():
        if key not in CONSENT_TYPES:
            raise ValueError(f"Unknown consent type {key!r}")
        if value not in (GRANTED, DENIED):
            raise ValueError(f"{key}: expected 'granted' or 'denied', got {value!r}")
    return _call("consent", "update", values)


def grant_consent(*types: str) -> EventSpec:
    """Grant the given consent types (all seven when called without arguments)."""
    return _call("consent", "update", _consent_values(types, GRANTED))


def deny_consent(*types: str) -> EventSpec:
    """Deny the given consent types (all seven when called without arguments)."""
    return _call("consent", "update", _consent_values(types, DENIED))


def opt_out() -> EventSpec:
    """Stop sending hits from this browser (``ga-disable-<ID>``), remembered in localStorage."""
    return _call("optOut")


def opt_in() -> EventSpec:
    """Undo :func:`opt_out`."""
    return _call("optIn")


# ----------------------------------------------------------------- reading
def get_field(field: str, callback: Any) -> EventSpec:
    """Read a gtag field (``client_id``, ``session_id``, ``gclid``) into ``callback``.

    Resolves to ``None`` in test mode or when tracking is disabled.
    """
    return _call("get", field, callback=callback)


def get_client_id(callback: Any) -> EventSpec:
    """Read the GA client id into ``callback`` (``None`` in test mode)."""
    return get_field("client_id", callback)


def get_status(callback: Any) -> EventSpec:
    """Send the tracker status dict (same shape as ``on_ready``) to ``callback``."""
    return _call("status", callback=callback)


# ---------------------------------------------------- recommended events
def login(method: str | None = None) -> EventSpec:
    return event("login", method=method)


def sign_up(method: str | None = None) -> EventSpec:
    return event("sign_up", method=method)


def search(search_term: str) -> EventSpec:
    return event("search", search_term=search_term)


def share(
    method: str | None = None, content_type: str | None = None, item_id: str | None = None
) -> EventSpec:
    return event("share", method=method, content_type=content_type, item_id=item_id)


def select_content(content_type: str, content_id: str) -> EventSpec:
    return event("select_content", content_type=content_type, content_id=content_id)


def generate_lead(value: float | None = None, currency: str | None = None, **params: Any) -> EventSpec:
    return event("generate_lead", value=value, currency=currency, **params)


def tutorial_begin() -> EventSpec:
    return event("tutorial_begin")


def tutorial_complete() -> EventSpec:
    return event("tutorial_complete")


def exception(description: str, fatal: bool = False) -> EventSpec:
    """Report an error (shows up as the ``exception`` event)."""
    return event("exception", description=description, fatal=fatal)


def _ecommerce(
    name: str,
    items: Iterable[Item | Mapping[str, Any]] | None,
    value: float | None,
    currency: str | None,
    **params: Any,
) -> EventSpec:
    item_list = [dict(item) for item in items or []]
    for item in item_list:
        if not item.get("item_id") and not item.get("item_name"):
            raise ValueError(f"{name}: every item needs an item_id or an item_name")
    if value is not None and not currency:
        raise ValueError(f"{name}: GA4 requires currency when value is set")
    return event(name, items=item_list or None, value=value, currency=currency, **params)


def view_item(items: Iterable[Item], value: float | None = None, currency: str | None = None) -> EventSpec:
    return _ecommerce("view_item", items, value, currency)


def view_item_list(
    items: Iterable[Item], item_list_id: str | None = None, item_list_name: str | None = None
) -> EventSpec:
    return _ecommerce(
        "view_item_list", items, None, None, item_list_id=item_list_id, item_list_name=item_list_name
    )


def add_to_cart(items: Iterable[Item], value: float | None = None, currency: str | None = None) -> EventSpec:
    return _ecommerce("add_to_cart", items, value, currency)


def remove_from_cart(
    items: Iterable[Item], value: float | None = None, currency: str | None = None
) -> EventSpec:
    return _ecommerce("remove_from_cart", items, value, currency)


def begin_checkout(
    items: Iterable[Item], value: float | None = None, currency: str | None = None, coupon: str | None = None
) -> EventSpec:
    return _ecommerce("begin_checkout", items, value, currency, coupon=coupon)


def purchase(
    transaction_id: str,
    value: float,
    currency: str,
    items: Iterable[Item],
    *,
    tax: float | None = None,
    shipping: float | None = None,
    coupon: str | None = None,
    affiliation: str | None = None,
) -> EventSpec:
    if not transaction_id:
        raise ValueError("purchase: transaction_id is required (GA4 deduplicates on it)")
    return _ecommerce(
        "purchase",
        items,
        value,
        currency,
        transaction_id=transaction_id,
        tax=tax,
        shipping=shipping,
        coupon=coupon,
        affiliation=affiliation,
    )


def refund(
    transaction_id: str,
    value: float | None = None,
    currency: str | None = None,
    items: Iterable[Item] | None = None,
) -> EventSpec:
    return _ecommerce("refund", items, value, currency, transaction_id=transaction_id)
