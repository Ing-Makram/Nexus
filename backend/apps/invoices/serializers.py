from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.customers.models import Customer
from apps.customers.selectors import customers_for_user
from apps.invoices.models import Invoice
from apps.orders.models import Order
from apps.orders.selectors import orders_for_user
from apps.organizations.models import Organization
from apps.organizations.selectors import organizations_for_user


class InvoiceSerializer(serializers.ModelSerializer):
    """Read/write representation of an invoice.

    - ``organization`` is writable only on create, restricted to organizations
      the caller belongs to, and immutable afterwards.
    - ``customer`` (required) and ``order`` (optional) are restricted to the
      caller's records and must belong to the invoice's organization.
    - ``invoice_number`` is trimmed and must be unique within the organization.
    - amount / status / date-ordering validation mirrors the model rules.
    """

    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.none())
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.none())
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.none(), required=False, allow_null=True
    )
    # Optional: a blank value means "assign the next INV-NNNN" (see the service).
    invoice_number = serializers.CharField(required=False, allow_blank=True, max_length=50)
    created_by = serializers.SlugRelatedField(slug_field="email", read_only=True)

    class Meta:
        model = Invoice
        # The unique-per-organization number is validated explicitly below with a
        # field-keyed error rather than DRF's non-field UniqueTogetherValidator.
        validators = []
        fields = [
            "id",
            "organization",
            "customer",
            "order",
            "invoice_number",
            "status",
            "issue_date",
            "due_date",
            "total_amount",
            "notes",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if self.instance is not None:
            self.fields["organization"].read_only = True

        if user is not None and getattr(user, "is_authenticated", False):
            if self.instance is None:
                self.fields["organization"].queryset = organizations_for_user(user)
            self.fields["customer"].queryset = customers_for_user(user)
            self.fields["order"].queryset = orders_for_user(user)

    def validate_invoice_number(self, value: str) -> str:
        return value.strip()

    def validate_total_amount(self, value: Decimal) -> Decimal:
        if value < 0:
            raise serializers.ValidationError("Total amount cannot be negative.")
        return value

    def _effective(self, attrs: dict[str, Any], field: str) -> Any:
        if field in attrs:
            return attrs[field]
        return getattr(self.instance, field, None)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        organization = self._effective(attrs, "organization")
        customer = self._effective(attrs, "customer")
        order = self._effective(attrs, "order")
        issue_date: date | None = self._effective(attrs, "issue_date")
        due_date: date | None = self._effective(attrs, "due_date")

        if organization is not None and customer is not None:
            if customer.organization_id != organization.id:
                raise serializers.ValidationError(
                    {"customer": "Customer must belong to the selected organization."}
                )
        if order is not None:
            if organization is not None and order.organization_id != organization.id:
                raise serializers.ValidationError(
                    {"order": "Order must belong to the selected organization."}
                )
            if customer is not None and order.customer_id != customer.id:
                raise serializers.ValidationError(
                    {"order": "Order must belong to the selected customer."}
                )
        if issue_date is not None and due_date is not None and due_date < issue_date:
            raise serializers.ValidationError(
                {"due_date": "Due date cannot be before the issue date."}
            )

        number = self._effective(attrs, "invoice_number")
        if organization is not None and number:
            clash = Invoice.objects.filter(organization=organization, invoice_number=number)
            if self.instance is not None:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"invoice_number": "An invoice with this number already exists."}
                )

        return attrs
