from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.orders.models import Order, OrderStatus
from apps.organizations.selectors import membership_for

if TYPE_CHECKING:
    from decimal import Decimal

    from apps.accounts.models import User
    from apps.customers.models import Customer
    from apps.organizations.models import Organization

# Fields a caller may change on an existing order. ``organization`` is
# deliberately absent: an order never moves to another organization.
WRITABLE_FIELDS = ("customer", "status", "total_amount", "notes")


def _require_membership(organization: Organization, actor: User) -> None:
    if membership_for(actor, organization) is None:
        raise PermissionDenied("You are not a member of this organization.")


def _validate(order: Order) -> None:
    """Run full model validation (status choices, non-negative total, and the
    same-organization customer rule) and surface it as a DRF error."""
    try:
        order.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict) from exc


@transaction.atomic
def create_order(
    *,
    organization: Organization,
    actor: User,
    customer: Customer,
    total_amount: Decimal,
    status: str = OrderStatus.DRAFT,
    notes: str = "",
) -> Order:
    _require_membership(organization, actor)

    order = Order(
        organization=organization,
        customer=customer,
        status=status,
        total_amount=total_amount,
        notes=notes,
        created_by=actor,
    )
    _validate(order)
    order.save()
    return order


@transaction.atomic
def update_order(*, order: Order, actor: User, **fields: object) -> Order:
    _require_membership(order.organization, actor)

    if "organization" in fields or "organization_id" in fields:
        raise ValidationError({"organization": "An order cannot be moved to another organization."})

    for key, value in fields.items():
        if key in WRITABLE_FIELDS:
            setattr(order, key, value)

    _validate(order)
    order.save()
    return order


@transaction.atomic
def delete_order(*, order: Order, actor: User) -> None:
    _require_membership(order.organization, actor)
    order.delete()
