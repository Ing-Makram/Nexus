"""Settings package.

Also exposes :func:`resolve_settings_module`, the single strategy that the
process entrypoints (``wsgi``, ``asgi``, ``celery``) use to choose a settings
module. It mirrors ``manage.py``:

* an explicit ``DJANGO_SETTINGS_MODULE`` always wins;
* otherwise ``ENVIRONMENT=production`` selects the production settings;
* anything else (including an unset ``ENVIRONMENT``) selects development.

``pytest`` sets ``DJANGO_SETTINGS_MODULE`` in ``pyproject.toml`` and is
unaffected.
"""

import os

_ENVIRONMENT_TO_SETTINGS = {
    "production": "config.settings.production",
    "development": "config.settings.development",
}

_DEFAULT_SETTINGS_MODULE = "config.settings.development"


def resolve_settings_module() -> str:
    explicit = os.environ.get("DJANGO_SETTINGS_MODULE")
    if explicit:
        return explicit
    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
    return _ENVIRONMENT_TO_SETTINGS.get(environment, _DEFAULT_SETTINGS_MODULE)
