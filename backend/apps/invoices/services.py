from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.invoices.models import Invoice, InvoiceStatus
from apps.organizations.models import Organization
from apps.organizations.selectors import membership_for

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from apps.accounts.models import User
    from apps.customers.models import Customer
    from apps.orders.models import Order

_AUTO_NUMBER_PREFIX = "INV-"

# Fields a caller may change on an existing invoice. ``organization`` is
# deliberately absent: an invoice never moves to another organization.
WRITABLE_FIELDS = (
    "customer",
    "order",
    "invoice_number",
    "status",
    "issue_date",
    "due_date",
    "total_amount",
    "notes",
)


def _require_membership(organization: Organization, actor: User) -> None:
    if membership_for(actor, organization) is None:
        raise PermissionDenied("You are not a member of this organization.")


def _next_invoice_number(organization: Organization) -> str:
    """The next ``INV-NNNN`` number for an organization.

    Callers hold a row lock on the organization (see :func:`create_invoice`) so
    concurrent creates cannot pick the same number.
    """
    highest = 0
    numbers = Invoice.objects.filter(
        organization=organization, invoice_number__startswith=_AUTO_NUMBER_PREFIX
    ).values_list("invoice_number", flat=True)
    for number in numbers:
        suffix = number[len(_AUTO_NUMBER_PREFIX) :]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{_AUTO_NUMBER_PREFIX}{highest + 1:04d}"


def _validate(invoice: Invoice) -> None:
    """Run full model validation (status choices, non-negative total, unique
    invoice number per organization, due-date ordering, and the
    same-organization customer/order rules) and surface it as a DRF error."""
    try:
        invoice.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict) from exc


@transaction.atomic
def create_invoice(
    *,
    organization: Organization,
    actor: User,
    customer: Customer,
    issue_date: date,
    total_amount: Decimal,
    invoice_number: str = "",
    order: Order | None = None,
    status: str = InvoiceStatus.DRAFT,
    due_date: date | None = None,
    notes: str = "",
) -> Invoice:
    _require_membership(organization, actor)

    number = invoice_number.strip()
    if not number:
        # Lock the organization row so concurrent creates serialise on numbering.
        Organization.objects.select_for_update().filter(pk=organization.pk).first()
        number = _next_invoice_number(organization)

    invoice = Invoice(
        organization=organization,
        customer=customer,
        order=order,
        invoice_number=number,
        status=status,
        issue_date=issue_date,
        due_date=due_date,
        total_amount=total_amount,
        notes=notes,
        created_by=actor,
    )
    _validate(invoice)
    invoice.save()
    return invoice


@transaction.atomic
def update_invoice(*, invoice: Invoice, actor: User, **fields: object) -> Invoice:
    _require_membership(invoice.organization, actor)

    if "organization" in fields or "organization_id" in fields:
        raise ValidationError(
            {"organization": "An invoice cannot be moved to another organization."}
        )

    for key, value in fields.items():
        if key in WRITABLE_FIELDS:
            setattr(invoice, key, value)

    _validate(invoice)
    invoice.save()
    return invoice


@transaction.atomic
def delete_invoice(*, invoice: Invoice, actor: User) -> None:
    _require_membership(invoice.organization, actor)
    invoice.delete()
