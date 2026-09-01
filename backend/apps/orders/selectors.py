from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import QuerySet

from apps.orders.models import Order

if TYPE_CHECKING:
    from apps.accounts.models import User


def orders_for_user(user: User) -> QuerySet[Order]:
    """Every order in an organization the user is a member of.

    This is the single tenant-scoping primitive for orders: services and
    (future) API code must never query ``Order.objects`` directly.
    """
    return Order.objects.filter(organization__memberships__user=user).select_related(
        "organization", "customer"
    )


def order_for_user(user: User, order_id: int) -> Order | None:
    """The order with ``order_id`` if it belongs to one of the user's
    organizations, otherwise ``None``."""
    return orders_for_user(user).filter(pk=order_id).first()
