from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models

from apps.common.models import AuthoredModel, TimestampedModel


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SENT = "sent", "Sent"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"
    VOID = "void", "Void"


class Invoice(TimestampedModel, AuthoredModel):
    """An invoice issued by an organization (the tenant) to one of its customers.

    Tenant ownership is the required ``organization`` foreign key. The
    ``customer`` and the optional ``order`` must belong to that same
    organization; this is checked in :meth:`clean` (a full database-level
    guarantee would need composite foreign keys and is out of scope here).
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )

    invoice_number = models.CharField(max_length=50, validators=[MinLengthValidator(1)])
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
    )
    issue_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "invoice_number"],
                name="invoice_number_unique_per_organization",
            ),
            models.CheckConstraint(
                check=~models.Q(invoice_number=""),
                name="invoice_number_not_empty",
            ),
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0),
                name="invoice_total_amount_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(status__in=InvoiceStatus.values),
                name="invoice_status_valid",
            ),
            models.CheckConstraint(
                check=models.Q(due_date__isnull=True)
                | models.Q(due_date__gte=models.F("issue_date")),
                name="invoice_due_date_not_before_issue_date",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "customer"]),
            models.Index(fields=["organization", "due_date"]),
        ]

    def __str__(self) -> str:
        return f"Invoice {self.invoice_number} · {self.customer} · {self.status}"

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if (
            self.customer_id
            and self.organization_id
            and self.customer.organization_id != self.organization_id
        ):
            errors["customer"] = "Customer must belong to the same organization as the invoice."
        if self.order_id:
            if self.organization_id and self.order.organization_id != self.organization_id:
                errors["order"] = "Order must belong to the same organization as the invoice."
            elif self.customer_id and self.order.customer_id != self.customer_id:
                errors["order"] = "Order must belong to the invoice's customer."
        if errors:
            raise ValidationError(errors)
