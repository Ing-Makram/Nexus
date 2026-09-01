from __future__ import annotations

from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models

from apps.common.models import TimestampedModel


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"


class Organization(TimestampedModel):
    name = models.CharField(max_length=120, validators=[MinLengthValidator(2)])
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_organizations",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Membership",
        related_name="organizations",
    )

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]

    def __str__(self) -> str:
        return self.name


class Membership(TimestampedModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_org_membership",
            ),
            models.CheckConstraint(
                check=models.Q(role__in=Role.values),
                name="membership_role_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "role"]),
            models.Index(fields=["organization", "role"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.organization} ({self.role})"
