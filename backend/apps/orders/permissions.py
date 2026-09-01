from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.organizations.models import Membership, Organization, Role
from apps.organizations.selectors import membership_for


def _order_organization(obj: Any) -> Organization | None:
    """Return the organization an order (or order-scoped object) belongs to.

    Accepts an ``Order``, an ``Organization`` directly, or anything exposing an
    ``organization`` attribute - so future order-scoped resources reuse these
    classes unchanged.
    """
    if isinstance(obj, Organization):
        return obj
    return getattr(obj, "organization", None)


class OrderAccessPermission(BasePermission):
    """Base order permission: an authenticated caller who belongs to the
    order's organization. Object-level, following the organization permission
    style (:mod:`apps.organizations.permissions`)."""

    message = "You do not have access to this order."
    allowed_roles: set[str] | None = None  # None => any member role is enough

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        organization = _order_organization(obj)
        if organization is None:
            return False
        membership = membership_for(request.user, organization)
        if membership is None:
            return False
        return self.allowed_roles is None or membership.role in self.allowed_roles


class CanReadOrders(OrderAccessPermission):
    """Any member of the order's organization may read it."""

    message = "You do not have access to this order."


class CanManageOrders(OrderAccessPermission):
    """Only owners and admins of the order's organization may create, update or
    delete orders."""

    message = "Only organization owners and admins can manage orders."
    allowed_roles = {Role.OWNER, Role.ADMIN}

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not super().has_permission(request, view):
            return False
        if request.method != "POST":
            # retrieve/update/delete are gated by has_object_permission.
            return True
        # Create has no object yet: check the caller's role in the submitted
        # organization. An unknown / out-of-scope organization is deferred to
        # the serializer, which raises the appropriate field error.
        organization_id = request.data.get("organization")
        if not organization_id:
            return True
        membership = Membership.objects.filter(
            user=request.user, organization_id=organization_id
        ).first()
        if membership is None:
            return True
        return membership.role in self.allowed_roles
