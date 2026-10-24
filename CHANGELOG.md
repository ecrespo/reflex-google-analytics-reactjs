# Changelog

## 0.1.0 - 2026-10-24

First release.

- `GoogleAnalytics` component (`google_analytics`) wrapping react-ga4 3.0.1 through a shared JSX bridge.
- `install(app)` mounts the component once in `app.extra_app_wraps`.
- `GoogleAnalyticsConfig` and `load_config()`: `google_analytics.toml`, `[tool.reflex-google-analytics]` in
  `pyproject.toml` or JSON, validated, with `GOOGLE_ANALYTICS_*` environment overrides.
- Automatic page views on React Router navigation, with `exclude_paths`, `include_search` and `include_hash`.
- Consent mode v2: defaults, a State-bindable `consent` prop, `grant_consent`, `deny_consent`, `update_consent`.
- Actions: `event`, `page_view`, `set_params`, `set_user_id`, `set_user_properties`, `opt_out`, `opt_in`,
  `get_client_id`, `get_field`, `get_status`, `gtag`, recommended and ecommerce events with a typed `Item`.
- `test_mode`, `only_in_production`, `respect_do_not_track`, and the `on_ready`, `on_page_view` and
  `on_command` triggers.
- Demo app with six pages and a live gtag command log.
- pre-commit hooks, CI workflow and PyPI Trusted Publishing workflow.
