import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_create_user_uses_email_and_hashes_password():
    user = User.objects.create_user(email="Alice@Example.com", password="s3cret-pass")

    assert user.email == "Alice@example.com"  # domain normalised
    assert user.username is None
    assert user.check_password("s3cret-pass")
    assert user.password != "s3cret-pass"
    assert user.is_staff is False
    assert user.is_superuser is False


def test_create_user_without_email_raises():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="x")


def test_create_superuser():
    admin = User.objects.create_superuser(email="admin@example.com", password="pw")

    assert admin.is_staff is True
    assert admin.is_superuser is True


def test_username_field_is_email():
    assert User.USERNAME_FIELD == "email"
    assert User.REQUIRED_FIELDS == []
