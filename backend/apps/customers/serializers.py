from __future__ import annotations

from rest_framework import serializers

from apps.customers.models import Customer
from apps.organizations.models import Organization
from apps.organizations.selectors import organizations_for_user


class CustomerSerializer(serializers.ModelSerializer):
    """Read/write representation of a customer.

    ``organization`` must be one the requesting user belongs to and is
    immutable after creation. ``name`` is trimmed and may not be blank.
    """

    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.none())
    created_by = serializers.SlugRelatedField(slug_field="email", read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "organization",
            "name",
            "email",
            "phone",
            "company",
            "address",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            # Organization is immutable once the customer exists.
            self.fields["organization"].read_only = True
            return
        request = self.context.get("request")
        if request is not None:
            # On create, only organizations the caller belongs to are selectable.
            self.fields["organization"].queryset = organizations_for_user(request.user)

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Name cannot be blank.")
        return cleaned
