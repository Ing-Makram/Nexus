from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.customers.models import Customer
from apps.invoices.models import Invoice, InvoiceStatus
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def customer():
    org = Organization.objects.create(name="Acme")
    return Customer.objects.create(organization=org, name="Jane")


def make_invoice(customer, number, status, due_offset_days):
    return Invoice.objects.create(
        organization=customer.organization,
        customer=customer,
        invoice_number=number,
        issue_date=timezone.now().date() - timedelta(days=60),
        due_date=timezone.now().date() + timedelta(days=due_offset_days),
        total_amount=Decimal("10.00"),
        status=status,
    )


def test_mark_overdue_invoices_only_touches_sent_and_past_due(customer):
    past_sent = make_invoice(customer, "A", InvoiceStatus.SENT, -1)
    future_sent = make_invoice(customer, "B", InvoiceStatus.SENT, +5)
    past_paid = make_invoice(customer, "C", InvoiceStatus.PAID, -1)
    no_due = Invoice.objects.create(
        organization=customer.organization,
        customer=customer,
        invoice_number="D",
        issue_date=timezone.now().date(),
        total_amount=Decimal("10.00"),
        status=InvoiceStatus.SENT,
    )

    out = StringIO()
    call_command("mark_overdue_invoices", stdout=out)
    assert "Marked 1 invoice(s) overdue." in out.getvalue()

    for invoice, expected in [
        (past_sent, InvoiceStatus.OVERDUE),
        (future_sent, InvoiceStatus.SENT),
        (past_paid, InvoiceStatus.PAID),
        (no_due, InvoiceStatus.SENT),
    ]:
        invoice.refresh_from_db()
        assert invoice.status == expected
