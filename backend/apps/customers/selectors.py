from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import QuerySet

from apps.customers.models import Customer

if TYPE_CHECKING:
    from apps.accounts.models import User


def customers_for_user(user: User) -> QuerySet[Customer]:
    """Every customer that belongs to an organization the user is a member of.

    This is the single tenant-scoping primitive for customers: API views must
    never query ``Customer.objects`` directly.
    """
    return Customer.objects.filter(organization__memberships__user=user)
