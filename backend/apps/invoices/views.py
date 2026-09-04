from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated

from apps.common.mixins import PermissionsByActionMixin
from apps.common.query_params import parse_date_param
from apps.invoices.models import Invoice, InvoiceStatus
from apps.invoices.permissions import CanManageInvoices, CanReadInvoices
from apps.invoices.selectors import invoices_for_user
from apps.invoices.serializers import InvoiceSerializer
from apps.invoices.services import (
    WRITABLE_FIELDS,
    create_invoice,
    delete_invoice,
    update_invoice,
)


class InvoiceViewSet(PermissionsByActionMixin, viewsets.ModelViewSet):
    """CRUD for invoices, strictly scoped to the caller's organizations.

    Tenant isolation: ``get_queryset`` only returns invoices from organizations
    the caller belongs to, so any cross-tenant request resolves to 404. Any
    member may read; owners and admins may create, update and delete. All
    writes go through the service layer.
    """

    serializer_class = InvoiceSerializer

    _permissions_by_action: dict[str, list[type[BasePermission]]] = {
        "create": [IsAuthenticated, CanManageInvoices],
        "retrieve": [IsAuthenticated, CanReadInvoices],
        "update": [IsAuthenticated, CanManageInvoices],
        "partial_update": [IsAuthenticated, CanManageInvoices],
        "destroy": [IsAuthenticated, CanManageInvoices],
    }

    def get_queryset(self) -> QuerySet[Invoice]:
        queryset = invoices_for_user(self.request.user)
        organization = self.request.query_params.get("organization")
        if organization and organization.isdigit():
            queryset = queryset.filter(organization_id=organization)
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        date_from = parse_date_param(self.request.query_params.get("date_from"))
        if date_from:
            queryset = queryset.filter(issue_date__gte=date_from)
        date_to = parse_date_param(self.request.query_params.get("date_to"))
        if date_to:
            queryset = queryset.filter(issue_date__lte=date_to)
        return queryset

    def perform_create(self, serializer: InvoiceSerializer) -> None:
        data = serializer.validated_data
        serializer.instance = create_invoice(
            organization=data["organization"],
            actor=self.request.user,
            customer=data["customer"],
            issue_date=data["issue_date"],
            total_amount=data["total_amount"],
            invoice_number=data.get("invoice_number", ""),
            order=data.get("order"),
            status=data.get("status", InvoiceStatus.DRAFT),
            due_date=data.get("due_date"),
            notes=data.get("notes", ""),
        )

    def perform_update(self, serializer: InvoiceSerializer) -> None:
        fields = {
            key: value for key, value in serializer.validated_data.items() if key in WRITABLE_FIELDS
        }
        serializer.instance = update_invoice(
            invoice=serializer.instance, actor=self.request.user, **fields
        )

    def perform_destroy(self, instance: Invoice) -> None:
        delete_invoice(invoice=instance, actor=self.request.user)
