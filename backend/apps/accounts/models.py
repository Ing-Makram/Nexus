from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.managers import UserManager


class User(AbstractUser):
    """Custom user model that authenticates with an email address.

    The ``username`` field inherited from ``AbstractUser`` is removed; ``email``
    is the unique login identifier.
    """

    username = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"

    def __str__(self) -> str:
        return self.email
