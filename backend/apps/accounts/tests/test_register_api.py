from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

pytestmark = pytest.mark.django_db

STRONG_PASSWORD = "sp1ral-galaxy-42"


@pytest.fixture
def api():
    return APIClient()


def test_register_creates_user_and_returns_a_session(api):
    resp = api.post(
        reverse("accounts:register"),
        {
            "email": "New.User@Example.com",
            "password": STRONG_PASSWORD,
            "first_name": "New",
            "last_name": "User",
        },
        format="json",
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["access"]
    assert body["refresh"]
    assert body["user"]["email"] == "New.User@example.com"  # domain normalised
    assert body["user"]["first_name"] == "New"
    assert "password" not in body["user"]
    assert "password" not in body

    user = User.objects.get(email="New.User@example.com")
    assert user.check_password(STRONG_PASSWORD)


def test_registered_user_can_log_in(api):
    api.post(
        reverse("accounts:register"),
        {"email": "member@example.com", "password": STRONG_PASSWORD},
        format="json",
    )

    resp = api.post(
        reverse("accounts:login"),
        {"email": "member@example.com", "password": STRONG_PASSWORD},
        format="json",
    )
    assert resp.status_code == 200


def test_register_rejects_duplicate_email(api):
    User.objects.create_user(email="taken@example.com", password=STRONG_PASSWORD)

    resp = api.post(
        reverse("accounts:register"),
        {"email": "taken@example.com", "password": STRONG_PASSWORD},
        format="json",
    )
    assert resp.status_code == 400
    assert "email" in resp.json()


def test_concurrent_duplicate_registration_is_a_400_not_a_500(api):
    """The serializer's existence check can be raced; the database constraint
    is the final authority and must still surface as a 400."""
    User.objects.create_user(email="race@example.com", password=STRONG_PASSWORD)

    # Simulate the check passing (as it would for a request that ran its
    # validation before the first INSERT committed).
    with patch(
        "apps.accounts.serializers.RegisterSerializer.validate_email",
        side_effect=lambda self, value: User.objects.normalize_email(value),
        autospec=True,
    ):
        resp = api.post(
            reverse("accounts:register"),
            {"email": "race@example.com", "password": STRONG_PASSWORD},
            format="json",
        )

    assert resp.status_code == 400
    assert "email" in resp.json()
    assert User.objects.filter(email="race@example.com").count() == 1


def test_register_rejects_duplicate_email_case_insensitively(api):
    User.objects.create_user(email="taken@example.com", password=STRONG_PASSWORD)

    resp = api.post(
        reverse("accounts:register"),
        {"email": "TAKEN@example.com", "password": STRONG_PASSWORD},
        format="json",
    )
    assert resp.status_code == 400


def test_register_rejects_weak_password(api):
    resp = api.post(
        reverse("accounts:register"),
        {"email": "weak@example.com", "password": "12345"},
        format="json",
    )
    assert resp.status_code == 400
    assert "password" in resp.json()
    assert not User.objects.filter(email="weak@example.com").exists()


def test_register_requires_email_and_password(api):
    resp = api.post(reverse("accounts:register"), {}, format="json")
    assert resp.status_code == 400
    assert "email" in resp.json()
    assert "password" in resp.json()
