"""GA4 ecommerce: view_item_list, add_to_cart, begin_checkout and purchase."""

from __future__ import annotations

import reflex as rx
import reflex_google_analytics_reactjs as rga

from ..layout import page_shell, section
from ..state import PRODUCTS, ShopState


def _product(product: dict) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(product["item_category"], size="1", color=rx.color("gray", 10)),
            rx.heading(product["item_name"], size="3"),
            rx.text(f"$ {product['price']:.2f}", weight="bold"),
            rx.hstack(
                rx.button(
                    "View",
                    size="1",
                    variant="soft",
                    on_click=rga.view_item([product], value=product["price"], currency="USD"),
                ),
                rx.button("Add", size="1", on_click=ShopState.add(product["item_id"])),
            ),
            spacing="2",
        ),
        flex="1 1 180px",
    )


def ecommerce() -> rx.Component:
    return page_shell(
        "Ecommerce",
        "Items and amounts are built in the State and sent with the typed rga helpers (Item, purchase...).",
        section(
            "Catalog",
            rx.button(
                "view_item_list",
                size="1",
                variant="outline",
                on_click=rga.view_item_list(PRODUCTS, item_list_id="menu", item_list_name="Caracas menu"),
            ),
            rx.flex(*[_product(p) for p in PRODUCTS], gap="12px", wrap="wrap", width="100%"),
            icon="store",
        ),
        section(
            "Cart",
            rx.foreach(
                ShopState.cart,
                lambda item: rx.hstack(
                    rx.text(item["item_name"]),
                    rx.spacer(),
                    rx.badge("x", item["quantity"].to_string()),
                    width="100%",
                ),
            ),
            rx.hstack(
                rx.text("Total: $ ", ShopState.total.to_string(), weight="bold"),
                rx.spacer(),
                rx.button("begin_checkout", variant="soft", on_click=ShopState.checkout),
                rx.button("purchase", on_click=ShopState.pay, id="btn-purchase"),
                width="100%",
                align="center",
            ),
            rx.cond(
                ShopState.last_transaction != "",
                rx.text("Last transaction: ", rx.code(ShopState.last_transaction), size="2"),
            ),
            icon="shopping-cart",
        ),
    )


rx.page(route="/ecommerce", title="Ecommerce | GA4 demo")(ecommerce)
