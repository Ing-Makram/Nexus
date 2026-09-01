"""Read-only aggregation for the organization dashboard.

There is no service layer here: the dashboard never writes. Every queryset is
built from the existing per-app tenant-scoping selectors, so tenant isolation is
inherited - this module never touches ``*.objects`` directly.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Count, QuerySet, Sum

from apps.customers.selectors import customers_for_user
from apps.invoices.models import InvoiceStatus
from apps.invoices.selectors import invoices_for_user
from apps.orders.selectors import orders_for_user

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.organizations.models import Organization

_ZERO = Decimal("0.00")
_RECENT_LIMIT = 5

# Invoice statuses that represent money still owed to the organization.
_OUTSTANDING_STATUSES = (InvoiceStatus.SENT, InvoiceStatus.OVERDUE)


def _counts_by_status(queryset: QuerySet) -> dict[str, int]:
    return {
        row["status"]: row["count"] for row in queryset.values("status").annotate(count=Count("id"))
    }


def _money(value: Decimal | None) -> str:
    """A stable 2dp string regardless of DB backend (SQLite drops trailing zeros)."""
    return str((value or _ZERO).quantize(_ZERO))


def _sum(queryset: QuerySet) -> str:
    return _money(queryset.aggregate(total=Sum("total_amount"))["total"])


def dashboard_stats(*, user: User, organization: Organization) -> dict:
    """Aggregate figures for one organization the ``user`` belongs to."""
    customers = customers_for_user(user).filter(organization=organization)
    orders = orders_for_user(user).filter(organization=organization)
    invoices = invoices_for_user(user).filter(organization=organization)

    invoice_status_counts = _counts_by_status(invoices)

    recent_orders = [
        {
            "id": order.id,
            "customer": order.customer.name,
            "status": order.status,
            "total_amount": _money(order.total_amount),
            "created_at": order.created_at.isoformat(),
        }
        for order in orders[:_RECENT_LIMIT]
    ]
    recent_invoices = [
        {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "customer": invoice.customer.name,
            "status": invoice.status,
            "total_amount": _money(invoice.total_amount),
            "issue_date": invoice.issue_date.isoformat(),
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        }
        for invoice in invoices[:_RECENT_LIMIT]
    ]

    return {
        "organization": organization.id,
        "customers": {"total": customers.count()},
        "orders": {
            "total": orders.count(),
            "by_status": _counts_by_status(orders),
        },
        "invoices": {
            "total": invoices.count(),
            "by_status": invoice_status_counts,
            # "total invoiced" excludes voided invoices - they were never billed.
            "total_amount": _sum(invoices.exclude(status=InvoiceStatus.VOID)),
            "paid_amount": _sum(invoices.filter(status=InvoiceStatus.PAID)),
            "outstanding_amount": _sum(invoices.filter(status__in=_OUTSTANDING_STATUSES)),
            "overdue_count": invoice_status_counts.get(InvoiceStatus.OVERDUE, 0),
        },
        "recent_orders": recent_orders,
        "recent_invoices": recent_invoices,
    }
