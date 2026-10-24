"""reflex-google-analytics-reactjs: Google Analytics 4 for Reflex, powered by react-ga4."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version

from . import actions
from .actions import (
    Item,
    add_to_cart,
    begin_checkout,
    deny_consent,
    event,
    exception,
    generate_lead,
    get_client_id,
    get_field,
    get_status,
    grant_consent,
    gtag,
    login,
    opt_in,
    opt_out,
    page_view,
    purchase,
    refund,
    remove_from_cart,
    search,
    select_content,
    set_params,
    set_user_id,
    set_user_properties,
    share,
    sign_up,
    tutorial_begin,
    tutorial_complete,
    update_consent,
    validate_event_name,
    view_item,
    view_item_list,
)
from .config import (
    ConfigError,
    ConsentDefaults,
    GoogleAnalyticsConfig,
    find_config_file,
    load_config,
)
from .constants import (
    CONSENT_TYPES,
    DEFAULT_CONFIG_FILENAME,
    DENIED,
    DENY_ALL_CONSENT,
    GRANTED,
    REACT_GA4_VERSION,
)
from .google_analytics import GoogleAnalytics, google_analytics, install

# pyproject.toml is the single source of truth for the version.
try:
    __version__ = _package_version("reflex-google-analytics-reactjs")
except PackageNotFoundError:  # pragma: no cover - source tree without an install
    __version__ = "0.0.0.dev0"

__all__ = [
    "CONSENT_TYPES",
    "DEFAULT_CONFIG_FILENAME",
    "DENIED",
    "DENY_ALL_CONSENT",
    "GRANTED",
    "REACT_GA4_VERSION",
    "ConfigError",
    "ConsentDefaults",
    "GoogleAnalytics",
    "GoogleAnalyticsConfig",
    "Item",
    "actions",
    "add_to_cart",
    "begin_checkout",
    "deny_consent",
    "event",
    "exception",
    "find_config_file",
    "generate_lead",
    "get_client_id",
    "get_field",
    "get_status",
    "google_analytics",
    "grant_consent",
    "gtag",
    "install",
    "load_config",
    "login",
    "opt_in",
    "opt_out",
    "page_view",
    "purchase",
    "refund",
    "remove_from_cart",
    "search",
    "select_content",
    "set_params",
    "set_user_id",
    "set_user_properties",
    "share",
    "sign_up",
    "tutorial_begin",
    "tutorial_complete",
    "update_consent",
    "validate_event_name",
    "view_item",
    "view_item_list",
]
