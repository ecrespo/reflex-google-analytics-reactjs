# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`reflex-google-analytics-reactjs` is a Reflex custom component (published to PyPI) that wraps **react-ga4 3.0.1** to add Google Analytics 4 to Reflex apps. The importable package is `reflex_google_analytics_reactjs` under `custom_components/` (setuptools `packages.find where = ["custom_components"]`). `google_analytics_reactjs_demo/` is a separate Reflex app that exercises it.

## Commands

```bash
uv sync && uv pip install -e .          # dev setup (package must be installed editable for the demo/tests)
uv run pre-commit install --install-hooks   # hooks: file checks, ruff, uv-lock on commit; pytest on pre-push
uv run pre-commit run --all-files
uv run pytest                            # all tests (testpaths = tests, -q --strict-markers)
uv run pytest tests/test_config.py::test_name   # single test
uv run ruff check .                      # lint (line-length 110, py310 target; .pyi excluded)
uv run ruff format .
uv run reflex component build            # regenerates google_analytics.pyi + builds sdist/wheel into dist/

cd google_analytics_reactjs_demo && uv run reflex run   # demo; must run from this dir (config discovery is cwd-relative)
GOOGLE_ANALYTICS_MEASUREMENT_ID=G-YOURID GOOGLE_ANALYTICS_TEST_MODE=false uv run reflex run   # real hits
```

## Architecture

Three layers that must stay in sync:

1. **Config (`config.py`)** — `GoogleAnalyticsConfig` dataclass, validated in `__post_init__` (tag id regex, `exclude_paths` must start with `/`, unknown keys rejected). `load_config()` / `find_config_file()` resolve in order: `$GOOGLE_ANALYTICS_CONFIG` → `google_analytics.toml` in the app dir → `[tool.reflex-google-analytics]` in `pyproject.toml` (JSON also supported). `with_env()` then overlays `GOOGLE_ANALYTICS_<FIELD>` env vars (bools parsed, dicts/lists as JSON). `to_props()` converts to component props; `only_in_production` forces `test_mode` unless Reflex runs in prod mode.

2. **Component (`google_analytics.py`)** — `GoogleAnalytics` points `library` at the bundled `google_analytics.jsx` via `rx.asset(..., shared=True)` and pins `react-ga4@{REACT_GA4_VERSION}` in `lib_dependencies`. `create(config=...)` merges config props under explicit props (explicit wins; `config=False` disables loading). `install(app)` registers it in `app.extra_app_wraps` so it mounts once above all pages and survives navigation.

3. **JSX bridge (`google_analytics.jsx`)** — `ReflexGoogleAnalytics` initializes react-ga4 once (consent defaults/`set` before `js`+`config`, with `send_page_view: false`), emits a `page_view` on each React Router `useLocation()` change, syncs the `consent` prop to `gtag("consent","update")`, and exposes an imperative API at `window.__reflexGA` (calls before init are queued). It reports commands to the `onCommand` trigger.

**Actions (`actions.py`)** don't touch State: every helper (`event`, `purchase`, `grant_consent`, `opt_out`, ...) returns an `rx.call_script` built by `_call(method, *args)` that JSON-encodes args and invokes `window.__reflexGA.<method>(...)`. Adding a new action means adding the matching method in the JSX bridge. Event names go through `validate_event_name()` (GA4 rules, reserved names/prefixes) before anything is sent.

Shared constants (consent types, `BROWSER_API`, env prefix, tag-id pattern, app-wrap order) live in `constants.py`.

## Conventions

- Adding/changing a component prop: update the `Var` in `google_analytics.py`, the JSX destructuring/handling, `GoogleAnalyticsConfig` + `to_props()` if it's configurable from file, then regenerate `google_analytics.pyi` with `reflex component build` (the `.pyi` is generated, don't hand-edit). `tests/test_component.py` asserts props compile to the camelCase names the bridge expects.
- Public API is re-exported explicitly in `__init__.py` (`__all__`); keep both lists updated.
- Bumping react-ga4 requires changing `REACT_GA4_VERSION` (tests assert the pinned value).
- Version lives only in `pyproject.toml` (`__version__` reads installed metadata); record releases in `CHANGELOG.md`.
- Everything (library, demo UI, docs) is in English. README images use absolute `raw.githubusercontent.com/.../main/docs/screenshots/...` URLs so they render on PyPI too; relative paths break there.
- Releases: bump `pyproject.toml` version + `CHANGELOG.md`, then a GitHub release `vX.Y.Z` triggers `.github/workflows/publish.yml` (PyPI Trusted Publishing; manual run → TestPyPI). The tag must match the version. Keep `UV_VERSION` in the workflows and the `uv-pre-commit` rev in `.pre-commit-config.yaml` aligned.
