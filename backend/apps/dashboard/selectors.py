"""Read-only aggregation for the organization dashboard.

There is no service layer here: the dashboard never writes. Every queryset is
built from the existing per-app tenant-scoping selectors, so tenant isolation is
inherited - this module never touches ``*.objects`` directly.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Count, QuerySet, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.customers.selectors import customers_for_user
from apps.invoices.models import InvoiceStatus
from apps.invoices.selectors import invoices_for_user
from apps.orders.selectors import orders_for_user

if TYPE_CHECKING:
    from datetime import date

    from apps.accounts.models import User
    from apps.organizations.models import Organization

_ZERO = Decimal("0.00")
_RECENT_LIMIT = 5

# The date-range windows the timeseries endpoint will build, in days.
TIMESERIES_RANGES = (30, 90)

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


def _count_by_day(queryset: QuerySet, field: str) -> dict[date, int]:
    """Rows per calendar day, keyed by ``date``, for a datetime ``field``."""
    rows = queryset.annotate(day=TruncDate(field)).values("day").annotate(n=Count("id"))
    return {row["day"]: row["n"] for row in rows}


def _sum_by_day(queryset: QuerySet, field: str) -> dict[date, Decimal]:
    """``total_amount`` summed per calendar day, keyed by ``date``."""
    rows = queryset.values(field).annotate(total=Sum("total_amount"))
    return {row[field]: row["total"] for row in rows}


def dashboard_timeseries(*, user: User, organization: Organization, days: int) -> dict:
    """Daily activity for one organization over the last ``days`` calendar days.

    Every bucket is present (zero-filled) so the frontend can plot a continuous
    axis. Orders and customers are bucketed by ``created_at``; invoices by their
    ``issue_date`` (the business date), matching how each is shown elsewhere.
    """
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)

    orders = orders_for_user(user).filter(organization=organization, created_at__date__gte=start)
    invoices = invoices_for_user(user).filter(organization=organization, issue_date__gte=start)
    customers = customers_for_user(user).filter(
        organization=organization, created_at__date__gte=start
    )

    orders_by_day = _count_by_day(orders, "created_at")
    customers_by_day = _count_by_day(customers, "created_at")
    invoices_by_day = {
        row["issue_date"]: row["n"] for row in invoices.values("issue_date").annotate(n=Count("id"))
    }
    invoiced_by_day = _sum_by_day(invoices.exclude(status=InvoiceStatus.VOID), "issue_date")
    paid_by_day = _sum_by_day(invoices.filter(status=InvoiceStatus.PAID), "issue_date")

    points = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        points.append(
            {
                "date": day.isoformat(),
                "orders": orders_by_day.get(day, 0),
                "invoices": invoices_by_day.get(day, 0),
                "customers": customers_by_day.get(day, 0),
                "invoiced_amount": _money(invoiced_by_day.get(day)),
                "paid_amount": _money(paid_by_day.get(day)),
            }
        )

    return {
        "organization": organization.id,
        "start": start.isoformat(),
        "end": today.isoformat(),
        "days": days,
        "points": points,
    }
