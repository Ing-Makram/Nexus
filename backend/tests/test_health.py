"""Smoke tests for the backend infrastructure.

These intentionally cover only wiring (URLs resolve, the app boots, the
health endpoint responds) and not any business behaviour.
"""

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
