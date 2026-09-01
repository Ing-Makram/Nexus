"""Liveness and readiness probes for container orchestration.

Deliberately plain Django views (no DRF, no auth, no serializers): a probe must
stay cheap and dependency-free. They expose only a fixed status string - never
configuration, credentials, or exception details.

Note: the pre-existing ``/api/health/`` endpoint (``config.urls``) is kept as-is
for backwards compatibility; these are the orchestration-facing probes.
"""

import logging

from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger("nexus.health")


@require_GET
def liveness(request):
    """Process is up. No I/O - must never depend on the database."""
    return JsonResponse({"status": "alive"})


@require_GET
def readiness(request):
    """Ready to serve traffic: Django is configured and the database answers."""
    try:
        connections["default"].cursor().execute("SELECT 1")
    except OperationalError:
        # A normal operational condition, not an application crash: log at
        # WARNING with no traceback so it does not become monitoring noise.
        logger.warning("Readiness check failed: database unavailable")
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})
