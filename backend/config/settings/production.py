"""Production settings.

Everything here is environment-driven. Production never falls back to an
insecure default: a missing required variable raises ``ImproperlyConfigured``
at import time so a misconfigured deployment fails fast instead of booting
with development credentials.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False


def _require_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"The {name} environment variable must be set in production.")
    return value


def _env_list(name):
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def _env_int(name, default):
    raw = os.environ.get(name)
    return int(raw) if raw else default


def _env_bool(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# --- Required configuration - no insecure fallbacks -----------------------

SECRET_KEY = _require_env("SECRET_KEY")

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "The ALLOWED_HOSTS environment variable must be set (comma-separated) in production."
    )

# Full origins including scheme, e.g. "https://app.example.com".
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")

# --- Static files -------------------------------------------------------

# WhiteNoise serves collected static files straight from the Gunicorn worker,
# so the reverse proxy needs no knowledge of Django's static layout.
# Inserted directly after SecurityMiddleware, per WhiteNoise's documentation.
_security_mw = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
MIDDLEWARE = [
    *MIDDLEWARE[: _security_mw + 1],
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[_security_mw + 1 :],
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# --- HTTPS / reverse proxy ----------------------------------------------

# NEXUS runs behind a TLS-terminating proxy (nginx / load balancer) that
# forwards the original scheme in this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", True)
# Load-balancer health probes commonly hit these over plain HTTP; never 301 them.
SECURE_REDIRECT_EXEMPT = [r"^health/$", r"^health/ready/$"]

# --- HTTP Strict Transport Security ------------------------------------

SECURE_HSTS_SECONDS = _env_int("SECURE_HSTS_SECONDS", 31_536_000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# --- Cookies ----------------------------------------------------------

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True

# --- Additional hardening -------------------------------------------

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# --- Database -------------------------------------------------------

# Persistent connections (seconds) - avoids reconnecting on every request.
# Copy the mapping from base so reloading this module never mutates it.
DATABASES = {**DATABASES}
DATABASES["default"] = {
    **DATABASES["default"],
    "CONN_MAX_AGE": _env_int("CONN_MAX_AGE", 60),
}

# --- Observability -------------------------------------------------

# Machine-readable logs in production unless an operator overrides LOG_FORMAT.
# Rebuild only the nested dicts we touch so reloading never mutates base's.
if os.environ.get("LOG_FORMAT") is None:
    LOGGING = {**LOGGING, "handlers": {**LOGGING["handlers"]}}
    LOGGING["handlers"]["console"] = {
        **LOGGING["handlers"]["console"],
        "formatter": "json",
    }


def _sentry_drop_health_noise(event, _hint):
    """Keep liveness/readiness probes out of the error monitor."""
    url = (event.get("request") or {}).get("url") or ""
    return None if "/health/" in url else event


# Optional error monitoring. Activates ONLY when SENTRY_DSN is set; production
# boots normally without it. The DSN and every knob come from the environment -
# nothing is hardcoded.
SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
if SENTRY_DSN:
    try:
        import sentry_sdk
    except ImportError:  # pragma: no cover - sentry-sdk is in requirements.txt
        import warnings

        warnings.warn(
            "SENTRY_DSN is set but sentry-sdk is not installed; error monitoring disabled.",
            stacklevel=2,
        )
    else:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
            release=os.environ.get("SENTRY_RELEASE") or None,
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE") or 0.0),
            # Never attach cookies, auth headers, the client IP, or the body.
            send_default_pii=False,
            before_send=_sentry_drop_health_noise,
            before_send_transaction=_sentry_drop_health_noise,
        )
