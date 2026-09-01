from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.organizations.models import Organization, Role
from apps.organizations.selectors import membership_for


def _resolve_organization(obj: Any) -> Organization | None:
    """Return the Organization an object belongs to.

    Accepts an Organization directly, or any model instance that exposes an
    ``organization`` attribute - which lets future business modules reuse these
    permission classes unchanged.
    """
    if isinstance(obj, Organization):
        return obj
    return getattr(obj, "organization", None)


class IsOrganizationMember(BasePermission):
    """Object-level: the request user must belong to the object's organization."""

    message = "You do not have access to this organization."
    allowed_roles: set[str] | None = None  # None => any role is fine

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        organization = _resolve_organization(obj)
        if organization is None:
            return False
        membership = membership_for(request.user, organization)
        if membership is None:
            return False
        return self.allowed_roles is None or membership.role in self.allowed_roles


class IsOrganizationAdmin(IsOrganizationMember):
    message = "This action requires an organization admin or owner."
    allowed_roles = {Role.OWNER, Role.ADMIN}


class IsOrganizationOwner(IsOrganizationMember):
    message = "This action requires the organization owner."
    allowed_roles = {Role.OWNER}


class IsOrganizationMemberForRoute(BasePermission):
    """Route-level membership check for resources nested under an organization.

    The view must expose ``get_organization()`` (which is itself tenant-scoped,
    so a non-member gets a 404 rather than reaching this check). Reusable by any
    future nested collection under an organization.
    """

    message = "You do not have access to this organization."
    allowed_roles: set[str] | None = None  # None => any role is fine

    def has_permission(self, request: Request, view: APIView) -> bool:
        organization = view.get_organization()  # type: ignore[attr-defined]
        membership = membership_for(request.user, organization)
        if membership is None:
            return False
        return self.allowed_roles is None or membership.role in self.allowed_roles


class CanManageOrganizationMembers(IsOrganizationMemberForRoute):
    message = "Only organization owners and admins can manage members."
    allowed_roles = {Role.OWNER, Role.ADMIN}
