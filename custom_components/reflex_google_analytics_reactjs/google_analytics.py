"""Reflex custom component for Google Analytics 4, built on react-ga4.

The React side lives in ``google_analytics.jsx``, a small bridge shipped with
this package as a shared asset. It initializes react-ga4 once, sends a
``page_view`` on every client-side navigation, keeps consent mode in sync and
exposes ``window.__reflexGA`` for the helpers in ``actions.py``.

Example:
    ```python
    import reflex as rx
    import reflex_google_analytics_reactjs as rga

    app = rx.App()
    rga.install(app)  # reads google_analytics.toml next to rxconfig.py

    def index():
        return rx.button("Sign up", on_click=rga.sign_up(method="email"))
    ```
"""

from __future__ import annotations

import os
from typing import Any

import reflex as rx
from reflex.components.component import Component
from reflex.event import passthrough_event_spec
from reflex.vars.base import Var

from .config import GoogleAnalyticsConfig, load_config
from .constants import APP_WRAP_NAME, APP_WRAP_ORDER, REACT_GA4_VERSION

_JSX_ASSET = rx.asset("google_analytics.jsx", shared=True)

ConfigSource = GoogleAnalyticsConfig | str | os.PathLike[str] | None


class GoogleAnalytics(Component):
    """Loads gtag.js through react-ga4 and tracks page views.

    It renders its children (if any) and nothing else, so it can sit anywhere
    on a page or wrap the whole app through :func:`install`. Mount it once:
    react-ga4 is a singleton, later instances only add their event listeners.
    """

    library = _JSX_ASSET.importable_path

    tag = "ReflexGoogleAnalytics"

    lib_dependencies: list[str] = [f"react-ga4@{REACT_GA4_VERSION}"]

    # ------------------------------------------------------------------ ids
    # GA4 measurement id, ``G-XXXXXXXXXX``.
    measurement_id: Var[str]

    # Several Google products on one tag: ``[{"trackingId": "G-..."}, {"trackingId": "AW-...",
    # "gtagOptions": {...}}]``. Takes precedence over ``measurement_id``.
    trackers: Var[list[dict[str, Any]]]

    # ------------------------------------------------------------- behaviour
    # Master switch. When False nothing is loaded and every action is a no-op.
    enabled: Var[bool]

    # react-ga4 test mode: gtag.js is never loaded, commands are only queued and
    # reported to ``on_command``. Use it in development and tests.
    test_mode: Var[bool]

    # Flag hits for GA4 DebugView (Admin > DebugView).
    debug_mode: Var[bool]

    # Send a page_view on each client-side navigation (the automatic one from
    # ``config`` is turned off so the landing page is not counted twice).
    track_page_views: Var[bool]

    # Include the query string / the hash in the tracked page path.
    include_search: Var[bool]
    include_hash: Var[bool]

    # Routes that never get a page_view. ``/admin`` is exact, ``/admin/*`` a prefix.
    exclude_paths: Var[list[str]]

    # Skip initialization when the browser sends Do-Not-Track or Global Privacy Control.
    respect_do_not_track: Var[bool]

    # ----------------------------------------------------------------- tag
    # Alternative gtag.js URL (server-side tagging or a first-party proxy).
    gtag_url: Var[str]

    # CSP nonce for the injected gtag.js <script>.
    nonce: Var[str]

    # Legacy analytics.js-style options react-ga4 maps to gtag (``cookieDomain``, ``userId``...).
    ga_options: Var[dict[str, Any]]

    # Raw ``gtag("config", id, {...})`` parameters (``cookie_flags``, ``groups``...).
    gtag_options: Var[dict[str, Any]]

    # Signed-in user id sent with ``config``.
    user_id: Var[str]

    # Initial ``user_properties``.
    user_properties: Var[dict[str, Any]]

    # ------------------------------------------------------------- consent
    # Consent mode v2 defaults, sent before ``config``:
    # ``{"analytics_storage": "denied", ..., "wait_for_update": 500}``.
    default_consent: Var[dict[str, Any]]

    # The current consent choice. Bind it to a State var and every change is
    # sent as ``gtag("consent", "update", ...)``.
    consent: Var[dict[str, str]]

    # Redact ad click identifiers while ad_storage is denied.
    ads_data_redaction: Var[bool]

    # Pass gclid/dclid through URLs while cookies are denied.
    url_passthrough: Var[bool]

    # -------------------------------------------------------------- events
    # Fired once after mounting with the tracker status:
    # ``{initialized, disabled, disabled_reason, test_mode, measurement_id, measurement_ids, opted_out, last_page}``.
    on_ready: rx.EventHandler[passthrough_event_spec(dict[str, Any])]

    # Fired after each automatic page view: ``{page_path, page_title, page_location}``.
    on_page_view: rx.EventHandler[passthrough_event_spec(dict[str, Any])]

    # Fired for every gtag command: ``{command, args, test_mode, timestamp}``.
    # Leave it unset in production: each command is a round trip to the backend.
    on_command: rx.EventHandler[passthrough_event_spec(dict[str, Any])]

    @classmethod
    def create(cls, *children: Any, config: Any = None, **props: Any) -> Component:
        """Create the component, merging in a :class:`GoogleAnalyticsConfig`.

        Args:
            *children: Rendered as-is (handy when wrapping the app).
            config: A config object, a path to a ``.toml``/``.json`` file, ``None``
                to auto-discover ``google_analytics.toml`` (plus ``GOOGLE_ANALYTICS_*``
                env vars), or ``False`` to rely on explicit props only.
            **props: Component props; they win over values from the config.

        Returns:
            The component.
        """
        if config is not False:
            resolved = config if isinstance(config, GoogleAnalyticsConfig) else load_config(config)
            props = {**resolved.to_props(), **props}
        return super().create(*children, **props)


google_analytics = GoogleAnalytics.create


def install(
    app: rx.App,
    config: ConfigSource | bool = None,
    *,
    order: int = APP_WRAP_ORDER,
    **props: Any,
) -> rx.App:
    """Mount Google Analytics around every page of ``app``.

    The component is added to ``app.extra_app_wraps``, so it is rendered once
    for the whole app and survives navigation (no re-initialization per page).

    Args:
        app: The Reflex app.
        config: See :meth:`GoogleAnalytics.create`.
        order: Position among the app wraps (lower = closer to the pages).
        **props: Extra component props, including event triggers such as
            ``on_page_view=State.handler``.

    Returns:
        The same app, for chaining.
    """
    resolved: GoogleAnalyticsConfig | bool
    resolved = config if config is False or isinstance(config, GoogleAnalyticsConfig) else load_config(config)

    def _wrap(_stateful: bool) -> Component:
        return GoogleAnalytics.create(config=resolved, **props)

    app.extra_app_wraps[(order, APP_WRAP_NAME)] = _wrap
    return app
