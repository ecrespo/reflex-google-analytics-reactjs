/**
 * React bridge between Reflex and react-ga4 (Google Analytics 4 / gtag.js),
 * used by the `reflex-google-analytics-reactjs` custom component.
 *
 * Responsibilities:
 * - Initialize react-ga4 exactly once per browser session, in the order gtag.js
 *   expects: consent defaults and `set` commands first, then `js` + `config`.
 * - Send a `page_view` on every client-side navigation (React Router location
 *   change), with the automatic `send_page_view` of `config` turned off so
 *   GA4 never counts the first page twice.
 * - Expose a small imperative API on `window.__reflexGA` so the Python helpers
 *   in `actions.py` (`rx.call_script`) can send events, update consent, set the
 *   user id, opt out, and read the client id. Calls made before initialization
 *   are queued and replayed afterwards.
 * - Report every gtag command to the optional `onCommand` trigger as a
 *   JSON-safe payload, so a Reflex app can inspect what is being sent
 *   (handy together with `testMode`, which never contacts Google).
 *
 * The component renders its children untouched (it can wrap the whole app via
 * `App.extra_app_wraps`) and adds no DOM of its own.
 */
import { useEffect, useRef } from "react";
import { useLocation } from "react-router";
import ReactGA from "react-ga4";

const API_KEY = "__reflexGA";
const OPT_OUT_STORAGE_KEY = "reflex-ga:opt-out";

/* ------------------------------------------------------------------ helpers */

/** Make any gtag argument safe to ship to the Reflex backend. */
const toJsonSafe = (value, depth = 0) => {
  if (value === undefined) return null;
  if (value === null || typeof value !== "object") {
    return typeof value === "function" ? "[function]" : value;
  }
  if (value instanceof Date) return value.toISOString();
  if (depth > 6) return "[nested]";
  if (Array.isArray(value)) return value.map((item) => toJsonSafe(item, depth + 1));
  const out = {};
  for (const [key, item] of Object.entries(value)) {
    if (item !== undefined) out[key] = toJsonSafe(item, depth + 1);
  }
  return out;
};

const isPlainObject = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value);

/** Drop `undefined`/`null` entries so gtag never receives empty parameters. */
const compact = (object) => {
  if (!isPlainObject(object)) return {};
  const out = {};
  for (const [key, item] of Object.entries(object)) {
    if (item !== undefined && item !== null) out[key] = item;
  }
  return out;
};

const readStorage = (key) => {
  try {
    return window.localStorage.getItem(key);
  } catch (_error) {
    return null;
  }
};

const writeStorage = (key, value) => {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch (_error) {
    /* storage unavailable (private mode, sandboxed iframe): ignore */
  }
};

/** `/admin` matches `/admin` only; `/admin/*` matches `/admin` and everything below. */
const pathIsExcluded = (path, patterns) =>
  (patterns || []).some((pattern) => {
    if (typeof pattern !== "string" || !pattern) return false;
    if (pattern.endsWith("*")) {
      const prefix = pattern.slice(0, -1);
      return path.startsWith(prefix) || path === prefix.replace(/\/$/, "");
    }
    return path === pattern;
  });

const doNotTrackEnabled = () => {
  if (typeof navigator === "undefined") return false;
  const dnt = navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack;
  return dnt === "1" || dnt === "yes" || navigator.globalPrivacyControl === true;
};

/* ------------------------------------------------- the shared browser state */

const state = {
  initialized: false,
  disabled: false,
  disabledReason: null,
  testMode: false,
  includeSearch: true,
  includeHash: false,
  locationOverridden: false,
  measurementId: null,
  measurementIds: [],
  pending: [],
  listeners: new Set(),
  lastPage: null,
};

/** Every gtag command react-ga4 issues goes through `_gtag`; observe it once. */
if (!ReactGA.__reflexPatched) {
  const original = ReactGA._gtag;
  ReactGA._gtag = (...args) => {
    original(...args);
    const payload = {
      command: typeof args[0] === "string" ? args[0] : String(args[0]),
      args: toJsonSafe(args.slice(1)),
      test_mode: state.testMode,
      timestamp: new Date().toISOString(),
    };
    state.listeners.forEach((listener) => {
      try {
        listener(payload);
      } catch (error) {
        console.error("reflex-google-analytics: onCommand listener failed", error);
      }
    });
  };
  ReactGA.__reflexPatched = true;
}

/** Run now if GA is ready, queue if it is still initializing, drop if disabled. */
const whenReady = (fn) => {
  if (state.disabled) return false;
  if (state.initialized) {
    fn();
    return true;
  }
  state.pending.push(fn);
  return true;
};

/**
 * `page_location` for a tracked path. Built from the origin plus the path we
 * already filtered with `includeSearch`/`includeHash`, so query strings (reset
 * tokens, emails...) never reach Google through the full `location.href`.
 */
const pageLocation = (page) => {
  if (typeof page === "string" && page.startsWith("/")) return window.location.origin + page;
  // Anything else (relative or absolute URL, no path at all): filter it, never fall back to href.
  const url = new URL(typeof page === "string" && page ? page : window.location.href, window.location.href);
  if (!state.includeSearch) url.search = "";
  if (!state.includeHash) url.hash = "";
  return url.href;
};

/**
 * Make later events (not only page views) report the filtered location too.
 * Once an override exists it is refreshed on every navigation, even when the
 * new URL needs no filtering, so events never carry a previous page's location.
 */
const syncPageLocation = (location) => {
  if (location === window.location.href && !state.locationOverridden) return;
  ReactGA.gtag("set", { page_location: location });
  state.locationOverridden = true;
};

const setOptOutFlags = (value) => {
  state.measurementIds.forEach((id) => {
    window[`ga-disable-${id}`] = value;
  });
};

const api = {
  /** Low level: `gtag(command, ...args)`. */
  gtag: (...args) => whenReady(() => ReactGA.gtag(...args)),

  /** GA4 event: `event("login", {method: "Google"})`. */
  event: (name, params) =>
    whenReady(() => {
      const clean = compact(params);
      if (Object.keys(clean).length) ReactGA.gtag("event", name, clean);
      else ReactGA.gtag("event", name);
    }),

  /** Manual page view. Defaults to the current location and document title. */
  pageView: (path, title, extra) =>
    whenReady(() => {
      const page = path || window.location.pathname + (state.includeSearch ? window.location.search : "");
      const location = pageLocation(page);
      // Later events belong to the real route, not to this (possibly virtual) page.
      syncPageLocation(pageLocation(null));
      ReactGA.send({
        hitType: "pageview",
        page,
        title: title || document.title,
        location,
        ...compact(extra),
      });
      state.lastPage = page;
    }),

  /** `gtag("set", fields)`, e.g. `{currency: "EUR"}` or `{user_properties: {...}}`. */
  set: (fields) => whenReady(() => ReactGA.gtag("set", compact(fields))),

  /** Associate (or clear, with `null`) the signed-in user id on every product. */
  setUserId: (userId) =>
    whenReady(() => {
      state.measurementIds.forEach((id) =>
        ReactGA.gtag("config", id, { user_id: userId ?? null, send_page_view: false }),
      );
    }),

  setUserProperties: (properties) =>
    whenReady(() => ReactGA.gtag("set", "user_properties", compact(properties))),

  /** Consent mode v2: `consent("update", {analytics_storage: "granted"})`. */
  consent: (mode, values) => {
    if (state.disabled) return false;
    // Consent commands are safe (and expected) before `config`, so they skip the queue.
    ReactGA.gtag("consent", mode || "update", compact(values));
    return true;
  },

  /** Official GA opt-out: `window['ga-disable-<ID>'] = true`, remembered in localStorage. */
  optOut: () => {
    writeStorage(OPT_OUT_STORAGE_KEY, "1");
    setOptOutFlags(true);
    return true;
  },

  optIn: () => {
    writeStorage(OPT_OUT_STORAGE_KEY, null);
    setOptOutFlags(false);
    return true;
  },

  isOptedOut: () => readStorage(OPT_OUT_STORAGE_KEY) === "1",

  /** Resolves with gtag's field value (e.g. `client_id`, `session_id`). */
  get: (field) =>
    new Promise((resolve) => {
      const ok = whenReady(() => {
        if (state.testMode) {
          resolve(null); // gtag.js is not loaded in test mode, nobody would answer
          return;
        }
        const timer = setTimeout(() => resolve(null), 4000);
        ReactGA.gtag("get", state.measurementId, field || "client_id", (value) => {
          clearTimeout(timer);
          resolve(value ?? null);
        });
      });
      if (!ok) resolve(null);
    }),

  status: () => ({
    initialized: state.initialized,
    disabled: state.disabled,
    disabled_reason: state.disabledReason,
    test_mode: state.testMode,
    measurement_id: state.measurementId,
    measurement_ids: [...state.measurementIds],
    opted_out: api.isOptedOut(),
    last_page: state.lastPage,
  }),
};

if (typeof window !== "undefined") {
  window[API_KEY] = api;
}

/* -------------------------------------------------------------- component */

const disable = (reason) => {
  state.disabled = true;
  state.disabledReason = reason;
  state.pending = [];
};

const initialize = (props) => {
  const {
    measurementId,
    trackers,
    enabled = true,
    testMode = false,
    debugMode = false,
    trackPageViews = true,
    includeSearch = true,
    includeHash = false,
    respectDoNotTrack = false,
    gtagUrl,
    nonce,
    gaOptions,
    gtagOptions,
    defaultConsent,
    adsDataRedaction = false,
    urlPassthrough = false,
    userId,
    userProperties,
  } = props;

  const configs = Array.isArray(trackers) && trackers.length
    ? trackers.map((tracker) =>
        typeof tracker === "string" ? { trackingId: tracker } : { ...tracker, trackingId: tracker.trackingId || tracker.tracking_id },
      )
    : measurementId
      ? [{ trackingId: measurementId }]
      : [];

  if (!enabled) return disable("disabled");
  if (!configs.length) return disable("missing_measurement_id");
  if (respectDoNotTrack && doNotTrackEnabled()) return disable("do_not_track");

  state.testMode = !!testMode;
  state.includeSearch = !!includeSearch;
  state.includeHash = !!includeHash;
  state.measurementIds = configs.map((config) => config.trackingId);
  state.measurementId = state.measurementIds[0];

  if (api.isOptedOut()) setOptOutFlags(true);

  // In test mode even the pre-`config` commands stay inside react-ga4's queue.
  ReactGA._testMode = state.testMode;

  // 1. Consent mode defaults and global settings must precede `config`.
  if (isPlainObject(defaultConsent) && Object.keys(defaultConsent).length) {
    ReactGA.gtag("consent", "default", compact(defaultConsent));
  }
  if (adsDataRedaction) ReactGA.gtag("set", "ads_data_redaction", true);
  if (urlPassthrough) ReactGA.gtag("set", "url_passthrough", true);

  // 2. `js` + `config` for every product, with our own page view tracking.
  const options = { ...compact(gtagOptions) };
  if (trackPageViews) options.send_page_view = false;
  if (debugMode) options.debug_mode = true; // GA only checks presence: never send `false`
  if (userId) options.user_id = userId;
  const initialLocation = pageLocation(null);
  if (initialLocation !== window.location.href && !options.page_location) {
    options.page_location = initialLocation;
    state.locationOverridden = true;
  }

  ReactGA.initialize(configs, {
    testMode: state.testMode,
    gtagUrl: gtagUrl || undefined,
    nonce: nonce || undefined,
    gaOptions: isPlainObject(gaOptions) && Object.keys(gaOptions).length ? gaOptions : undefined,
    gtagOptions: Object.keys(options).length ? options : undefined,
  });

  if (isPlainObject(userProperties) && Object.keys(userProperties).length) {
    ReactGA.gtag("set", "user_properties", compact(userProperties));
  }

  state.initialized = true;
  const queued = state.pending;
  state.pending = [];
  queued.forEach((fn) => fn());
};

export function ReflexGoogleAnalytics({ children, onReady, onPageView, onCommand, ...props }) {
  const location = useLocation();
  const listenerRef = useRef(onCommand);
  listenerRef.current = onCommand;

  // Command listener first, so `js`/`config` are reported too.
  useEffect(() => {
    const listener = (payload) => listenerRef.current?.(payload);
    state.listeners.add(listener);
    return () => state.listeners.delete(listener);
  }, []);

  // Initialize once per page load (StrictMode and remounts are no-ops).
  useEffect(() => {
    if (!state.initialized && !state.disabled) initialize(props);
    onReady?.(api.status());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep consent in sync when the prop is driven by a Reflex State var.
  const consentKey = JSON.stringify(props.consent ?? null);
  const firstConsent = useRef(true);
  useEffect(() => {
    if (!isPlainObject(props.consent) || !Object.keys(props.consent).length) return;
    if (firstConsent.current && !state.initialized) return;
    firstConsent.current = false;
    api.consent("update", props.consent);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [consentKey]);

  // One page view per client-side navigation.
  const { trackPageViews = true, includeSearch = true, includeHash = false, excludePaths } = props;
  const page =
    location.pathname + (includeSearch ? location.search : "") + (includeHash ? location.hash : "");
  useEffect(() => {
    if (!trackPageViews || state.disabled || !state.initialized) return;
    if (page === state.lastPage) return; // StrictMode double effects, same-page rerenders
    if (pathIsExcluded(location.pathname, excludePaths)) {
      // No page_view here, but events fired on this route still get a filtered location.
      syncPageLocation(pageLocation(null));
      state.lastPage = page;
      return;
    }
    // Let Reflex update <title> for the new route before reading it. `lastPage`
    // is only claimed when the hit is actually sent, so a StrictMode cleanup
    // cannot swallow the page view.
    // On the very first load Reflex sets <title> a few hundred ms after hydration:
    // wait for it (up to ~1.5 s) so the landing page_view carries page_title.
    let timer;
    let attempts = 0;
    const send = () => {
      if (page === state.lastPage) return;
      if (!document.title && attempts++ < 30) {
        timer = setTimeout(send, 50);
        return;
      }
      state.lastPage = page;
      const payload = { page_path: page, page_title: document.title, page_location: pageLocation(page) };
      syncPageLocation(payload.page_location);
      ReactGA.send({ hitType: "pageview", page, title: payload.page_title, location: payload.page_location });
      onPageView?.(payload);
    };
    timer = setTimeout(send, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, trackPageViews]);

  return children ?? null;
}
