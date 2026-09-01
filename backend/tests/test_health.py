"""Smoke tests for the backend infrastructure.

These intentionally cover only wiring (URLs resolve, the app boots, the
health endpoint responds) and not any business behaviour.
"""

import logging
from unittest import mock

from django.db.utils import OperationalError
from django.test import Client
from django.urls import reverse


def test_health_endpoint_returns_ok() -> None:
    client = Client()
    response = client.get(reverse("health-check"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "NEXUS Backend is running",
    }


def test_health_url_is_versionless_api_path() -> None:
    assert reverse("health-check") == "/api/health/"


# --- Orchestration probes (config/health.py) ---------------------------------


def test_liveness_probe_is_public_and_alive() -> None:
    response = Client().get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_probe_reports_ready_when_db_is_reachable(db) -> None:
    response = Client().get("/health/ready/")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


class _BrokenConnections:
    def __getitem__(self, alias):
        raise OperationalError("connection refused")


def test_readiness_probe_returns_503_when_db_is_unavailable() -> None:
    with mock.patch("config.health.connections", _BrokenConnections()):
        response = Client().get("/health/ready/")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    # No internal detail leaked.
    assert "connection refused" not in response.content.decode()


def test_readiness_failure_logs_a_warning_not_an_error(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="nexus.health"):
        with mock.patch("config.health.connections", _BrokenConnections()):
            Client().get("/health/ready/")

    assert any(r.levelno == logging.WARNING for r in caplog.records)
    # A normal DB outage must not be logged as an error or with a traceback
    # (that would become monitoring noise / a Sentry event).
    assert not any(r.levelno >= logging.ERROR for r in caplog.records)
    assert not any(r.exc_info for r in caplog.records)


def test_health_response_carries_a_request_id() -> None:
    assert Client().get("/health/").headers.get("X-Request-ID")
