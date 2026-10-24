"""Demo state: the gtag command log, consent choice, user id and the cart."""

from __future__ import annotations

import json
import uuid
from typing import Any

import reflex as rx
import reflex_google_analytics_reactjs as rga

MAX_LOG = 80

CONSENT_PRESETS: dict[str, dict[str, str]] = {
    "all": dict.fromkeys(rga.CONSENT_TYPES, rga.GRANTED),
    "none": dict(rga.DENY_ALL_CONSENT),
    "analytics": {**rga.DENY_ALL_CONSENT, "analytics_storage": rga.GRANTED},
}

PRODUCTS: list[dict[str, Any]] = [
    {"item_id": "SKU-ARE-01", "item_name": "Arepa reina pepiada", "item_category": "Food", "price": 6.5},
    {"item_id": "SKU-CAF-02", "item_name": "Guayoyo coffee", "item_category": "Drinks", "price": 2.0},
    {"item_id": "SKU-TEQ-03", "item_name": "Tequenos x12", "item_category": "Food", "price": 9.0},
]


def _summary(args: Any) -> str:
    """One line for the log table: the event/target name, then the parameters."""
    return json.dumps(args, ensure_ascii=False, default=str)


class LogState(rx.State):
    """Everything the component reports back to Python."""

    commands: list[dict[str, str]] = []
    page_views: list[dict[str, str]] = []
    status: dict[str, Any] = {}
    command_count: int = 0

    @rx.event
    def on_command(self, payload: dict[str, Any]):
        self.command_count += 1
        args = payload.get("args") or []
        entry = {
            "n": str(self.command_count),
            "time": str(payload.get("timestamp", ""))[11:19],
            "command": str(payload.get("command", "")),
            "target": str(args[0]) if args else "",
            "params": _summary(args[1] if len(args) == 2 else args[1:]) if len(args) > 1 else "",
        }
        self.commands = [entry, *self.commands][:MAX_LOG]

    @rx.event
    def on_page_view(self, payload: dict[str, Any]):
        entry = {
            "path": str(payload.get("page_path", "")),
            "title": str(payload.get("page_title", "")),
        }
        self.page_views = [entry, *self.page_views][:MAX_LOG]

    @rx.event
    def on_ready(self, status: dict[str, Any]):
        self.status = status

    @rx.event
    def refresh_status(self):
        return rga.get_status(LogState.on_ready)

    @rx.event
    def clear(self):
        self.commands = []
        self.page_views = []
        self.command_count = 0

    @rx.var
    def status_json(self) -> str:
        return json.dumps(self.status, indent=2, ensure_ascii=False)

    @rx.var
    def event_count(self) -> int:
        return sum(1 for entry in self.commands if entry["command"] == "event")


class ConsentState(rx.State):
    """The visitor's choice, remembered in localStorage and bound to the `consent` prop."""

    choice: str = rx.LocalStorage("", name="ga_demo_consent", sync=True)
    opted_out: bool = False

    @rx.var
    def consent(self) -> dict[str, str]:
        # Empty until the visitor answers: the [consent] defaults from the TOML apply.
        return CONSENT_PRESETS.get(self.choice, {})

    @rx.var
    def banner_open(self) -> bool:
        return self.choice == ""

    @rx.var
    def consent_rows(self) -> list[list[str]]:
        current = CONSENT_PRESETS.get(self.choice) or CONSENT_PRESETS["none"]
        return [[key, current[key]] for key in rga.CONSENT_TYPES]

    @rx.event
    def choose(self, preset: str):
        self.choice = preset

    @rx.event
    def reset_choice(self):
        self.choice = ""

    @rx.event
    def toggle_opt_out(self):
        self.opted_out = not self.opted_out
        return rga.opt_out() if self.opted_out else rga.opt_in()


class EventsState(rx.State):
    """Custom events typed in the form, validated in Python before they are sent."""

    name: str = "newsletter_subscribe"
    param_key: str = "plan"
    param_value: str = "monthly"
    user_id: str = ""
    error: str = ""
    client_id: str = ""

    @rx.event
    def set_name(self, value: str):
        self.name = value.strip()

    @rx.event
    def set_param_key(self, value: str):
        self.param_key = value.strip()

    @rx.event
    def set_param_value(self, value: str):
        self.param_value = value

    @rx.event
    def set_user_id_input(self, value: str):
        self.user_id = value.strip()

    @rx.event
    def send_custom(self):
        try:
            rga.validate_event_name(self.name)
        except ValueError as error:
            self.error = str(error)
            return rx.toast.error(self.error)
        self.error = ""
        params = {self.param_key: self.param_value} if self.param_key else {}
        return [rga.event(self.name, params), rx.toast.success(f"Event '{self.name}' sent")]

    @rx.event
    def apply_user_id(self):
        return rga.set_user_id(self.user_id or None)

    @rx.event
    def receive_client_id(self, value: Any):
        self.client_id = str(value) if value else "(no value: test_mode does not load gtag.js)"


class ShopState(rx.State):
    """A tiny cart to exercise the GA4 ecommerce events."""

    cart: list[dict[str, Any]] = []
    last_transaction: str = ""

    @rx.var
    def total(self) -> float:
        return round(sum(item["price"] * item["quantity"] for item in self.cart), 2)

    @rx.var
    def cart_size(self) -> int:
        return sum(item["quantity"] for item in self.cart)

    def _items(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.cart]

    @rx.event
    def add(self, item_id: str):
        product = next(p for p in PRODUCTS if p["item_id"] == item_id)
        for item in self.cart:
            if item["item_id"] == item_id:
                item["quantity"] += 1
                break
        else:
            self.cart.append({**product, "quantity": 1})
        self.cart = list(self.cart)
        return rga.add_to_cart([{**product, "quantity": 1}], value=product["price"], currency="USD")

    @rx.event
    def checkout(self):
        if not self.cart:
            return rx.toast.warning("The cart is empty")
        return rga.begin_checkout(self._items(), value=self.total, currency="USD")

    @rx.event
    def pay(self):
        if not self.cart:
            return rx.toast.warning("The cart is empty")
        transaction_id = f"T-{uuid.uuid4().hex[:8].upper()}"
        event = rga.purchase(
            transaction_id=transaction_id,
            value=self.total,
            currency="USD",
            items=self._items(),
            tax=round(self.total * 0.16, 2),
            shipping=1.5,
        )
        self.last_transaction = transaction_id
        self.cart = []
        return [event, rx.toast.success(f"Purchase {transaction_id} recorded")]
