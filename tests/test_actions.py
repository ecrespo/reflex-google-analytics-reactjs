"""Python helpers must produce the right window.__reflexGA calls."""

import json

import pytest
import reflex as rx
import reflex_google_analytics_reactjs as rga


class CallbackState(rx.State):
    @rx.event
    def receive(self, value: str):
        pass


def script_of(spec) -> str:
    for name, var in spec.args:
        if name._js_expr == "javascript_code":
            return var._var_value
    raise AssertionError("not a call_script event")


def test_event_serializes_name_and_params():
    script = script_of(rga.event("level_up", {"level": 3}, character="mage", skipped=None))
    assert "window.__reflexGA" in script
    assert 'ga.event("level_up", {"level": 3, "character": "mage"})' in script


@pytest.mark.parametrize("name", ["1bad", "has-dash", "x" * 41, "ga_custom", "google_x", "session_start", ""])
def test_invalid_event_names_are_rejected(name):
    with pytest.raises(ValueError):
        rga.event(name)


def test_valid_event_name():
    assert rga.validate_event_name("Custom_Event_2") == "Custom_Event_2"


def test_page_view_and_user_helpers():
    assert 'ga.pageView("/virtual", "Virtual", {})' in script_of(rga.page_view("/virtual", "Virtual"))
    assert "ga.pageView(null, null, {})" in script_of(rga.page_view())
    assert 'ga.setUserId("u-1")' in script_of(rga.set_user_id("u-1"))
    assert "ga.setUserId(null)" in script_of(rga.set_user_id(None))
    assert 'ga.setUserProperties({"plan": "pro"})' in script_of(rga.set_user_properties(plan="pro"))
    assert 'ga.set({"currency": "EUR"})' in script_of(rga.set_params(currency="EUR"))
    assert 'ga.gtag("set", "allow_google_signals", false)' in script_of(
        rga.gtag("set", "allow_google_signals", False)
    )


def test_consent_helpers():
    granted = script_of(rga.grant_consent("analytics_storage"))
    assert 'ga.consent("update", {"analytics_storage": "granted"})' in granted
    denied_all = script_of(rga.deny_consent())
    for consent_type in rga.CONSENT_TYPES:
        assert f'"{consent_type}": "denied"' in denied_all
    assert '"ad_storage": "granted"' in script_of(rga.update_consent(ad_storage="granted"))
    with pytest.raises(ValueError):
        rga.grant_consent("cookies")
    with pytest.raises(ValueError):
        rga.update_consent(ad_storage="yes")
    assert "ga.optOut()" in script_of(rga.opt_out())
    assert "ga.optIn()" in script_of(rga.opt_in())


def test_readers_use_a_callback():
    spec = rga.get_client_id(CallbackState.receive)
    assert 'ga.get("client_id")' in script_of(spec)
    callback = {k._js_expr: v for k, v in spec.args}["callback"]
    assert "receive" in str(callback)
    assert "ga.status()" in script_of(rga.get_status(CallbackState.receive))


def test_recommended_events():
    assert 'ga.event("login", {"method": "Google"})' in script_of(rga.login("Google"))
    assert 'ga.event("search", {"search_term": "arepas"})' in script_of(rga.search("arepas"))
    assert 'ga.event("tutorial_begin", {})' in script_of(rga.tutorial_begin())


def test_purchase_payload():
    items = [rga.Item(item_id="SKU1", item_name="Arepa", price=6.5, quantity=2)]
    script = script_of(rga.purchase("T-1", 13.0, "USD", items, tax=2.08))
    payload = json.loads(script.split('ga.event("purchase", ', 1)[1].rsplit("); })()", 1)[0])
    assert payload == {
        "items": [{"item_id": "SKU1", "item_name": "Arepa", "price": 6.5, "quantity": 2}],
        "value": 13.0,
        "currency": "USD",
        "transaction_id": "T-1",
        "tax": 2.08,
    }


def test_ecommerce_validation():
    with pytest.raises(ValueError, match="currency"):
        rga.add_to_cart([{"item_id": "A"}], value=3)
    with pytest.raises(ValueError, match="item_id or an item_name"):
        rga.view_item([{"price": 1}])
    with pytest.raises(ValueError, match="transaction_id"):
        rga.purchase("", 1, "USD", [{"item_id": "A"}])
