from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import QuerySet
from rest_framework.exceptions import PermissionDenied

from apps.organizations.models import Membership, Organization

if TYPE_CHECKING:
    from apps.accounts.models import User


def organizations_for_user(user: User) -> QuerySet[Organization]:
    """Every organization the user is a member of.

    This is the single tenant-scoping primitive: API views must never query
    ``Organization.objects`` directly.
    """
    return Organization.objects.filter(memberships__user=user)


def membership_for(user: User, organization: Organization) -> Membership | None:
    return Membership.objects.filter(user=user, organization=organization).first()


def require_membership(organization: Organization, actor: User) -> None:
    """Raise ``PermissionDenied`` unless ``actor`` is a member of ``organization``.

    The shared authorization guard used by the customers/orders/invoices write
    services before they touch organization-scoped data.
    """
    if membership_for(actor, organization) is None:
        raise PermissionDenied("You are not a member of this organization.")


def members_of(organization: Organization) -> QuerySet[Membership]:
    """Every membership in an organization, ready for serialization."""
    return (
        Membership.objects.filter(organization=organization)
        .select_related("user")
        .order_by("user__email")
    )


def membership_of_user(organization: Organization, user_id: int) -> Membership | None:
    return (
        Membership.objects.filter(organization=organization, user_id=user_id)
        .select_related("user")
        .first()
    )
