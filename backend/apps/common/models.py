from __future__ import annotations

from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    """Reusable created/updated audit columns for tenant-owned models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuthoredModel(models.Model):
    """Records which user created the row.

    Audit only: ``SET_NULL`` + ``null=True`` so the record survives the user's
    deletion, and ``editable=False`` so it is only ever set by a service.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
    )

    class Meta:
        abstract = True
