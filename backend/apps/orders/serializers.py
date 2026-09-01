from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.customers.models import Customer
from apps.customers.selectors import customers_for_user
from apps.orders.models import Order
from apps.organizations.models import Organization
from apps.organizations.selectors import organizations_for_user


class OrderSerializer(serializers.ModelSerializer):
    """Read/write representation of an order.

    - ``organization`` is writable only on create, restricted to organizations
      the caller belongs to, and immutable afterwards.
    - ``customer`` is restricted to the caller's customers and must belong to
      the order's organization.
    - ``status`` / ``total_amount`` validation mirrors the model rules
      (choices, non-negative total, same-organization customer).
    """

    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.none())
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.none())
    created_by = serializers.SlugRelatedField(slug_field="email", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "organization",
            "customer",
            "status",
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
            # Organization is immutable once the order exists.
            self.fields["organization"].read_only = True

        if user is not None and getattr(user, "is_authenticated", False):
            if self.instance is None:
                self.fields["organization"].queryset = organizations_for_user(user)
            self.fields["customer"].queryset = customers_for_user(user)

    def validate_total_amount(self, value: Decimal) -> Decimal:
        if value < 0:
            raise serializers.ValidationError("Total amount cannot be negative.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        organization = attrs.get("organization") or getattr(self.instance, "organization", None)
        customer = attrs.get("customer") or getattr(self.instance, "customer", None)
        if (
            organization is not None
            and customer is not None
            and customer.organization_id != organization.id
        ):
            raise serializers.ValidationError(
                {"customer": "Customer must belong to the selected organization."}
            )
        return attrs
