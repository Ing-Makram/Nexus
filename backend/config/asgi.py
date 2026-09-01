"""
ASGI config for the NEXUS project.

Exposes the ASGI callable as a module-level variable named ``application``.
Uses the same environment-driven settings-module strategy as ``wsgi.py``.
No WebSocket / Channels layer is configured.
"""

import os

from django.core.asgi import get_asgi_application

from config.settings import resolve_settings_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", resolve_settings_module())

application = get_asgi_application()
