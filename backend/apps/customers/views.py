from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.customers.models import Customer
from apps.customers.selectors import customers_for_user
from apps.customers.serializers import CustomerSerializer
from apps.customers.services import (
    WRITABLE_FIELDS,
    create_customer,
    delete_customer,
    update_customer,
)


class CustomerViewSet(viewsets.ModelViewSet):
    """CRUD for customers, strictly scoped to the caller's organizations.

    ``get_queryset`` only ever returns customers in organizations the caller
    belongs to, so any cross-tenant request resolves to 404.
    """

    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Customer]:
        queryset = customers_for_user(self.request.user).select_related("organization").distinct()
        organization = self.request.query_params.get("organization")
        if organization and organization.isdigit():
            queryset = queryset.filter(organization_id=organization)
        return queryset

    def perform_create(self, serializer: CustomerSerializer) -> None:
        data = serializer.validated_data
        serializer.instance = create_customer(
            organization=data["organization"],
            actor=self.request.user,
            name=data["name"],
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            company=data.get("company", ""),
            address=data.get("address", ""),
        )

    def perform_update(self, serializer: CustomerSerializer) -> None:
        fields = {
            key: value for key, value in serializer.validated_data.items() if key in WRITABLE_FIELDS
        }
        serializer.instance = update_customer(customer=serializer.instance, **fields)

    def perform_destroy(self, instance: Customer) -> None:
        delete_customer(customer=instance)
