from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.organizations.models import Membership, Organization, Role
from apps.organizations.selectors import membership_for


def _invoice_organization(obj: Any) -> Organization | None:
    """Return the organization an invoice (or invoice-scoped object) belongs to.

    Accepts an ``Invoice``, an ``Organization`` directly, or anything exposing
    an ``organization`` attribute.
    """
    if isinstance(obj, Organization):
        return obj
    return getattr(obj, "organization", None)


class InvoiceAccessPermission(BasePermission):
    """Base invoice permission: an authenticated caller who belongs to the
    invoice's organization. Object-level, following the order permission style
    (:mod:`apps.orders.permissions`)."""

    message = "You do not have access to this invoice."
    allowed_roles: set[str] | None = None  # None => any member role is enough

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        organization = _invoice_organization(obj)
        if organization is None:
            return False
        membership = membership_for(request.user, organization)
        if membership is None:
            return False
        return self.allowed_roles is None or membership.role in self.allowed_roles


class CanReadInvoices(InvoiceAccessPermission):
    """Any member of the invoice's organization may read it."""

    message = "You do not have access to this invoice."


class CanManageInvoices(InvoiceAccessPermission):
    """Only owners and admins of the invoice's organization may create, update
    or delete invoices."""

    message = "Only organization owners and admins can manage invoices."
    allowed_roles = {Role.OWNER, Role.ADMIN}

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not super().has_permission(request, view):
            return False
        if request.method != "POST":
            return True
        organization_id = request.data.get("organization")
        if not organization_id:
            return True
        membership = Membership.objects.filter(
            user=request.user, organization_id=organization_id
        ).first()
        if membership is None:
            return True
        return membership.role in self.allowed_roles
