import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

pytestmark = pytest.mark.django_db

PASSWORD = "correct-horse-battery"


@pytest.fixture
def user():
    return User.objects.create_user(
        email="user@example.com",
        password=PASSWORD,
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def api():
    return APIClient()


def test_login_returns_tokens_and_user(api, user):
    resp = api.post(
        reverse("accounts:login"),
        {"email": user.email, "password": PASSWORD},
        format="json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["access"]
    assert body["refresh"]
    assert body["user"]["id"] == user.id
    assert body["user"]["email"] == "user@example.com"
    assert body["user"]["first_name"] == "Test"
    assert body["user"]["is_active"] is True
    assert set(body["user"]) == {
        "id",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "date_joined",
    }
    assert "password" not in body["user"]


def test_login_with_bad_password_is_401(api, user):
    resp = api.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "wrong"},
        format="json",
    )
    assert resp.status_code == 401


def test_login_with_unknown_email_is_401(api):
    resp = api.post(
        reverse("accounts:login"),
        {"email": "nobody@example.com", "password": PASSWORD},
        format="json",
    )
    assert resp.status_code == 401


def test_refresh_returns_new_access_token(api, user):
    login = api.post(
        reverse("accounts:login"),
        {"email": user.email, "password": PASSWORD},
        format="json",
    ).json()

    resp = api.post(
        reverse("accounts:refresh"),
        {"refresh": login["refresh"]},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["access"]


def test_me_requires_authentication(api):
    resp = api.get(reverse("accounts:me"))
    assert resp.status_code == 401


def test_me_returns_current_user(api, user):
    access = api.post(
        reverse("accounts:login"),
        {"email": user.email, "password": PASSWORD},
        format="json",
    ).json()["access"]

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    resp = api.get(reverse("accounts:me"))

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "user@example.com"
    assert body["first_name"] == "Test"
    assert "password" not in body


def test_me_rejects_garbage_token(api):
    api.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    resp = api.get(reverse("accounts:me"))
    assert resp.status_code == 401


def test_logout_blacklists_the_refresh_token(api, user):
    session = api.post(
        reverse("accounts:login"),
        {"email": user.email, "password": PASSWORD},
        format="json",
    ).json()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {session['access']}")

    logout = api.post(reverse("accounts:logout"), {"refresh": session["refresh"]}, format="json")
    assert logout.status_code == 205

    # The blacklisted refresh token can no longer be used.
    refreshed = api.post(
        reverse("accounts:refresh"), {"refresh": session["refresh"]}, format="json"
    )
    assert refreshed.status_code == 401


def test_logout_requires_authentication(api):
    assert api.post(reverse("accounts:logout"), {}, format="json").status_code == 401


def test_logout_requires_a_refresh_token(api, user):
    access = api.post(
        reverse("accounts:login"),
        {"email": user.email, "password": PASSWORD},
        format="json",
    ).json()["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    resp = api.post(reverse("accounts:logout"), {}, format="json")
    assert resp.status_code == 400
