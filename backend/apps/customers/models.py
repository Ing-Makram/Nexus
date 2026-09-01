from __future__ import annotations

from django.core.validators import MinLengthValidator
from django.db import models

from apps.common.models import AuthoredModel, TimestampedModel


class Customer(TimestampedModel, AuthoredModel):
    """A customer belonging to exactly one organization (the tenant).

    Tenant ownership is expressed by the required ``organization`` foreign key;
    every query for customers must be scoped through it.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="customers",
    )

    name = models.CharField(max_length=255, validators=[MinLengthValidator(1)])
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    company = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(name=""),
                name="customer_name_not_empty",
            ),
        ]
        indexes = [
            # Customers are always listed within an organization, usually by name.
            models.Index(fields=["organization", "name"]),
            # Look-ups by contact email within an organization.
            models.Index(fields=["organization", "email"]),
        ]

    def __str__(self) -> str:
        return self.name
