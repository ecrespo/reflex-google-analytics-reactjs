"""The component must compile to the JSX the bridge understands."""

from types import SimpleNamespace

import reflex as rx
import reflex_google_analytics_reactjs as rga


class DemoState(rx.State):
    consent: dict[str, str] = {}

    @rx.event
    def on_page_view(self, payload: dict):
        pass


def test_library_points_to_the_shared_jsx_bridge():
    assert rga.GoogleAnalytics.library.startswith("$/public/external/reflex_google_analytics_reactjs/")
    assert rga.GoogleAnalytics.library.endswith("google_analytics.jsx")
    assert rga.GoogleAnalytics.tag == "ReflexGoogleAnalytics"


def test_react_ga4_is_pinned():
    assert rga.REACT_GA4_VERSION == "3.0.1"
    component = rga.google_analytics(config=False)
    assert component.lib_dependencies == ["react-ga4@3.0.1"]


def test_props_compile_to_camel_case():
    rendered = str(
        rga.google_analytics(
            config=False,
            measurement_id="G-ABC123",
            test_mode=True,
            track_page_views=False,
            exclude_paths=["/admin/*"],
            default_consent=rga.DENY_ALL_CONSENT,
        )
    )
    for expected in (
        'measurementId:"G-ABC123"',
        "testMode:true",
        "trackPageViews:false",
        "excludePaths:",
        "defaultConsent:",
    ):
        assert expected in rendered
    # gtag parameter names inside dicts must stay snake_case.
    assert '"analytics_storage"' in rendered


def test_config_object_and_explicit_props_merge():
    config = rga.GoogleAnalyticsConfig(measurement_id="G-FROMCFG", debug_mode=True)
    rendered = str(rga.google_analytics(config=config, debug_mode=False))
    assert 'measurementId:"G-FROMCFG"' in rendered
    assert "debugMode:false" in rendered  # explicit prop wins


def test_config_path(tmp_path):
    path = tmp_path / "ga.toml"
    path.write_text('measurement_id = "G-PATH1"\n', encoding="utf-8")
    assert 'measurementId:"G-PATH1"' in str(rga.google_analytics(config=str(path)))


def test_event_triggers_and_state_bound_consent():
    component = rga.google_analytics(
        config=False, consent=DemoState.consent, on_page_view=DemoState.on_page_view
    )
    assert "on_page_view" in component.event_triggers
    assert {"on_ready", "on_page_view", "on_command"} <= set(component.get_event_triggers())
    assert "consent" in str(component)


def test_install_adds_an_app_wrap():
    app = rx.App()
    rga.install(
        app, config=rga.GoogleAnalyticsConfig(measurement_id="G-APP1"), on_page_view=DemoState.on_page_view
    )
    wrap = app.extra_app_wraps[(1, "GoogleAnalytics")]
    component = wrap(True)
    assert isinstance(component, rga.GoogleAnalytics)
    assert 'measurementId:"G-APP1"' in str(component)


def test_install_custom_order_and_disabled_config():
    # install() only touches extra_app_wraps; a stub avoids a second rx.App per process.
    app = SimpleNamespace(extra_app_wraps={})
    rga.install(app, config=False, order=7, measurement_id="G-X1", enabled=False)
    assert "enabled:false" in str(app.extra_app_wraps[(7, "GoogleAnalytics")](True))
