"""Tests for production settings and the entrypoint settings-module strategy.

These do not run under ``config.settings.production`` (pytest uses
``config.settings.test``); instead they import/reload the production module
with a controlled environment and assert on the resulting module attributes.
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest
from django.core.exceptions import ImproperlyConfigured

PROD = "config.settings.production"

# A CI-safe key that also satisfies `check --deploy` (>=50 chars, >4 unique,
# no "django-insecure-" prefix). Not a real secret.
CI_SECRET_KEY = "n3xus-Ci-Only-K3y_" + "aZ9bY8cX7dW6eV5fU4gT3hS2iR1j".ljust(40, "q")

REQUIRED_ENV = {
    "SECRET_KEY": "a-real-production-secret-value-0123456789",
    "ALLOWED_HOSTS": "nexus.example.com,api.nexus.example.com",
}

BACKEND_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BACKEND_DIR / "config"


def _load_production(env):
    """Import/reload the production settings module under ``env`` only."""
    with mock.patch.dict(os.environ, env, clear=True):
        module = importlib.import_module(PROD)
        return importlib.reload(module)


# --- production settings load --------------------------------------------


def test_production_settings_load_with_required_env():
    settings = _load_production(REQUIRED_ENV)

    assert settings.DEBUG is False
    assert settings.SECRET_KEY == REQUIRED_ENV["SECRET_KEY"]
    assert settings.ALLOWED_HOSTS == ["nexus.example.com", "api.nexus.example.com"]


def test_missing_secret_key_fails_fast_in_production():
    with pytest.raises(ImproperlyConfigured):
        _load_production({"ALLOWED_HOSTS": "nexus.example.com"})


def test_missing_allowed_hosts_fails_fast_in_production():
    with pytest.raises(ImproperlyConfigured):
        _load_production({"SECRET_KEY": "some-secret"})


def test_csrf_trusted_origins_is_read_from_environment():
    settings = _load_production(
        {
            **REQUIRED_ENV,
            "CSRF_TRUSTED_ORIGINS": "https://app.nexus.example.com, https://nexus.example.com",
        }
    )

    assert settings.CSRF_TRUSTED_ORIGINS == [
        "https://app.nexus.example.com",
        "https://nexus.example.com",
    ]


def test_csrf_trusted_origins_defaults_to_empty_when_unset():
    settings = _load_production(REQUIRED_ENV)
    assert settings.CSRF_TRUSTED_ORIGINS == []


def test_secure_production_settings_are_enabled():
    settings = _load_production(REQUIRED_ENV)

    assert settings.SECURE_SSL_REDIRECT is True
    assert settings.SECURE_HSTS_SECONDS >= 31_536_000
    assert settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert settings.SECURE_HSTS_PRELOAD is True
    assert settings.SESSION_COOKIE_SECURE is True
    assert settings.CSRF_COOKIE_SECURE is True
    assert settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert settings.DATABASES["default"]["CONN_MAX_AGE"] == 60


def test_production_never_uses_the_insecure_dev_secret_key():
    settings = _load_production(REQUIRED_ENV)
    assert "insecure" not in settings.SECRET_KEY


def test_conn_max_age_is_environment_driven():
    settings = _load_production({**REQUIRED_ENV, "CONN_MAX_AGE": "120"})
    assert settings.DATABASES["default"]["CONN_MAX_AGE"] == 120


# --- entrypoint settings-module strategy --------------------------------


def test_resolver_prefers_explicit_django_settings_module():
    from config.settings import resolve_settings_module

    with mock.patch.dict(
        os.environ,
        {"DJANGO_SETTINGS_MODULE": "config.settings.custom", "ENVIRONMENT": "production"},
        clear=True,
    ):
        assert resolve_settings_module() == "config.settings.custom"


def test_resolver_selects_production_for_production_environment():
    from config.settings import resolve_settings_module

    with mock.patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
        assert resolve_settings_module() == "config.settings.production"


@pytest.mark.parametrize("env", [{}, {"ENVIRONMENT": "development"}, {"ENVIRONMENT": ""}])
def test_resolver_defaults_to_development(env):
    from config.settings import resolve_settings_module

    with mock.patch.dict(os.environ, env, clear=True):
        assert resolve_settings_module() == "config.settings.development"


def test_wsgi_asgi_celery_use_the_shared_resolver_and_never_hardcode_development():
    for name in ("wsgi.py", "asgi.py", "celery.py"):
        source = (CONFIG_DIR / name).read_text(encoding="utf-8")
        assert "resolve_settings_module()" in source, name
        assert "config.settings.development" not in source, name


def test_wsgi_and_asgi_applications_boot():
    from config.asgi import application as asgi_app
    from config.wsgi import application as wsgi_app

    assert wsgi_app is not None
    assert asgi_app is not None


# --- observability: logging format -------------------------------------


def test_production_defaults_to_json_logging():
    settings = _load_production(REQUIRED_ENV)
    assert settings.LOGGING["handlers"]["console"]["formatter"] == "json"
    assert "request_id" in settings.LOGGING["handlers"]["console"]["filters"]


def test_production_log_format_is_environment_overridable():
    settings = _load_production({**REQUIRED_ENV, "LOG_FORMAT": "plain"})
    assert settings.LOGGING["handlers"]["console"]["formatter"] == "standard"


# --- observability: optional Sentry -----------------------------------


def test_sentry_is_disabled_and_app_boots_without_a_dsn():
    settings = _load_production(REQUIRED_ENV)  # must not raise
    assert settings.SENTRY_DSN == ""


def test_sentry_is_configured_when_a_dsn_is_supplied():
    import sentry_sdk

    fake_dsn = "https://examplePublicKey@o0.ingest.sentry.io/0"
    try:
        settings = _load_production(
            {
                **REQUIRED_ENV,
                "SENTRY_DSN": fake_dsn,
                "SENTRY_ENVIRONMENT": "staging",
                "SENTRY_RELEASE": "nexus@test",
            }
        )
        assert settings.SENTRY_DSN == fake_dsn
        client = sentry_sdk.get_client()
        assert client.is_active()
        assert client.dsn == fake_dsn
        assert client.options["environment"] == "staging"
        assert client.options["send_default_pii"] is False
    finally:
        sentry_sdk.init(dsn="")  # disable the global client again


def test_production_source_hardcodes_no_sentry_credentials():
    source = (CONFIG_DIR / "settings" / "production.py").read_text(encoding="utf-8")
    assert "ingest.sentry.io" not in source
    assert "@sentry.io" not in source
    assert "SENTRY_DSN" in source  # ...it is read from the environment


# --- `manage.py check --deploy` --------------------------------------


def test_check_deploy_passes_with_a_valid_production_environment():
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": PROD,
        "SECRET_KEY": CI_SECRET_KEY,
        "ALLOWED_HOSTS": "nexus.example.com",
        "CSRF_TRUSTED_ORIGINS": "https://nexus.example.com",
        "DB_ENGINE": "django.db.backends.postgresql",
        "DB_NAME": "nexus",
        "DB_USER": "nexus",
        "DB_PASSWORD": "ci-db-password",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
    }
    result = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"check --deploy failed:\n{result.stdout}\n{result.stderr}"
