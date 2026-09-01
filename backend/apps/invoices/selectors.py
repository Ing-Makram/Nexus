from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import QuerySet

from apps.invoices.models import Invoice

if TYPE_CHECKING:
    from apps.accounts.models import User


def invoices_for_user(user: User) -> QuerySet[Invoice]:
    """Every invoice in an organization the user is a member of.

    This is the single tenant-scoping primitive for invoices: services and
    (future) API code must never query ``Invoice.objects`` directly.
    """
    return Invoice.objects.filter(organization__memberships__user=user).select_related(
        "organization", "customer", "order"
    )


def invoice_for_user(user: User, invoice_id: int) -> Invoice | None:
    """The invoice with ``invoice_id`` if it belongs to one of the user's
    organizations, otherwise ``None``."""
    return invoices_for_user(user).filter(pk=invoice_id).first()
