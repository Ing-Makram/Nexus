from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.organizations.models import Membership, Organization, Role
from apps.organizations.selectors import membership_for, membership_of_user

if TYPE_CHECKING:
    from apps.accounts.models import User

# Roles a caller may assign through the membership API. "owner" is deliberately
# excluded: the owner is set once, at creation, and is protected thereafter.
ASSIGNABLE_ROLES = {Role.MEMBER, Role.ADMIN}
MANAGER_ROLES = {Role.OWNER, Role.ADMIN}


@transaction.atomic
def create_organization(*, name: str, user: User) -> Organization:
    """Create an organization and make ``user`` its owner, atomically."""
    organization = Organization.objects.create(name=name, created_by=user)
    Membership.objects.create(organization=organization, user=user, role=Role.OWNER)
    return organization


def _require_manager(organization: Organization, actor: User) -> Membership:
    membership = membership_for(actor, organization)
    if membership is None or membership.role not in MANAGER_ROLES:
        raise PermissionDenied("Only organization owners and admins can manage members.")
    return membership


def _require_target(organization: Organization, user_id: int) -> Membership:
    target = membership_of_user(organization, user_id)
    if target is None:
        raise NotFound("This user is not a member of the organization.")
    return target


def _guard_target_mutation(actor_membership: Membership, target: Membership) -> None:
    """Enforce the owner-protection and admin rules shared by role change and
    removal."""
    if target.role == Role.OWNER:
        raise PermissionDenied("The organization owner cannot be modified or removed.")
    if target.role == Role.ADMIN and actor_membership.role != Role.OWNER:
        raise PermissionDenied("Only the owner can modify or remove an admin.")


@transaction.atomic
def add_member(*, organization: Organization, actor: User, email: str, role: str) -> Membership:
    _require_manager(organization, actor)
    if role not in ASSIGNABLE_ROLES:
        raise ValidationError({"role": "Role must be 'admin' or 'member'."})

    user_model = get_user_model()
    try:
        user = user_model.objects.get(email__iexact=email.strip())
    except user_model.DoesNotExist as exc:
        raise ValidationError({"email": "No user exists with this email address."}) from exc

    if Membership.objects.filter(organization=organization, user=user).exists():
        raise ValidationError({"email": "This user is already a member of the organization."})

    return Membership.objects.create(organization=organization, user=user, role=role)


@transaction.atomic
def change_member_role(
    *, organization: Organization, actor: User, target_user_id: int, role: str
) -> Membership:
    actor_membership = _require_manager(organization, actor)
    if role not in ASSIGNABLE_ROLES:
        raise ValidationError({"role": "Role must be 'admin' or 'member'."})

    target = _require_target(organization, target_user_id)
    _guard_target_mutation(actor_membership, target)

    target.role = role
    target.save(update_fields=["role", "updated_at"])
    return target


@transaction.atomic
def remove_member(*, organization: Organization, actor: User, target_user_id: int) -> None:
    actor_membership = _require_manager(organization, actor)
    target = _require_target(organization, target_user_id)
    _guard_target_mutation(actor_membership, target)
    target.delete()
