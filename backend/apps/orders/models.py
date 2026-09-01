from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import AuthoredModel, TimestampedModel


class OrderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class Order(TimestampedModel, AuthoredModel):
    """An order placed by a customer within an organization (the tenant).

    Tenant ownership is the required ``organization`` foreign key. The
    ``customer`` is expected to belong to that same organization; this is
    checked in :meth:`clean` (a full database-level guarantee would need a
    composite foreign key and is out of scope for the model layer).
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="orders",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT,
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0),
                name="order_total_amount_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(status__in=OrderStatus.values),
                name="order_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "customer"]),
        ]

    def __str__(self) -> str:
        return f"Order #{self.pk} · {self.customer} · {self.status}"

    def clean(self) -> None:
        super().clean()
        if (
            self.customer_id
            and self.organization_id
            and self.customer.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"customer": "Customer must belong to the same organization as the order."}
            )
