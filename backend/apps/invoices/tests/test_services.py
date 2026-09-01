from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.customers.models import Customer
from apps.invoices.models import Invoice, InvoiceStatus
from apps.invoices.services import create_invoice, delete_invoice, update_invoice
from apps.orders.models import Order
from apps.organizations.models import Membership, Organization, Role

pytestmark = pytest.mark.django_db

ISSUE_DATE = date(2026, 1, 1)


def make_user(django_user_model, email):
    return django_user_model.objects.create_user(email=email, password="pw12345!")


@pytest.fixture
def alice(django_user_model):
    return make_user(django_user_model, "alice@example.com")


@pytest.fixture
def bob(django_user_model):
    return make_user(django_user_model, "bob@example.com")


@pytest.fixture
def org_a(alice):
    org = Organization.objects.create(name="Org A")
    Membership.objects.create(organization=org, user=alice, role=Role.OWNER)
    return org


@pytest.fixture
def org_b(bob):
    org = Organization.objects.create(name="Org B")
    Membership.objects.create(organization=org, user=bob, role=Role.OWNER)
    return org


@pytest.fixture
def customer_a(org_a):
    return Customer.objects.create(organization=org_a, name="Acme")


@pytest.fixture
def customer_b(org_b):
    return Customer.objects.create(organization=org_b, name="Beta")


@pytest.fixture
def order_a(org_a, customer_a):
    return Order.objects.create(
        organization=org_a, customer=customer_a, total_amount=Decimal("10.00")
    )


@pytest.fixture
def invoice_a(org_a, customer_a, alice):
    return create_invoice(
        organization=org_a,
        actor=alice,
        customer=customer_a,
        invoice_number="INV-001",
        issue_date=ISSUE_DATE,
        total_amount=Decimal("100.00"),
    )


# --- create ------------------------------------------------------


def test_create_invoice(org_a, customer_a, alice):
    invoice = create_invoice(
        organization=org_a,
        actor=alice,
        customer=customer_a,
        invoice_number="INV-100",
        issue_date=ISSUE_DATE,
        total_amount=Decimal("250.00"),
    )

    assert invoice.pk is not None
    assert invoice.organization == org_a
    assert invoice.customer == customer_a
    assert invoice.status == InvoiceStatus.DRAFT
    assert invoice.order is None
    assert invoice.due_date is None
    assert invoice.created_by == alice


def test_create_invoice_with_all_fields(org_a, customer_a, order_a, alice):
    invoice = create_invoice(
        organization=org_a,
        actor=alice,
        customer=customer_a,
        invoice_number="INV-101",
        issue_date=ISSUE_DATE,
        total_amount=Decimal("1.00"),
        order=order_a,
        status=InvoiceStatus.SENT,
        due_date=ISSUE_DATE + timedelta(days=14),
        notes="Net 14",
    )
    assert invoice.order == order_a
    assert invoice.status == InvoiceStatus.SENT
    assert invoice.notes == "Net 14"


def test_create_invoice_requires_membership(org_a, customer_a, bob):
    with pytest.raises(PermissionDenied):
        create_invoice(
            organization=org_a,
            actor=bob,
            customer=customer_a,
            invoice_number="INV-1",
            issue_date=ISSUE_DATE,
            total_amount=Decimal("1.00"),
        )
    assert Invoice.objects.count() == 0


def test_create_invoice_customer_must_belong_to_the_same_organization(org_a, customer_b, alice):
    with pytest.raises(ValidationError) as exc:
        create_invoice(
            organization=org_a,
            actor=alice,
            customer=customer_b,
            invoice_number="INV-1",
            issue_date=ISSUE_DATE,
            total_amount=Decimal("1.00"),
        )
    assert "customer" in exc.value.detail
    assert Invoice.objects.count() == 0


def test_create_invoice_order_must_belong_to_the_same_organization(
    org_a, org_b, customer_a, customer_b, alice
):
    foreign_order = Order.objects.create(
        organization=org_b, customer=customer_b, total_amount=Decimal("1.00")
    )
    with pytest.raises(ValidationError) as exc:
        create_invoice(
            organization=org_a,
            actor=alice,
            customer=customer_a,
            order=foreign_order,
            invoice_number="INV-1",
            issue_date=ISSUE_DATE,
            total_amount=Decimal("1.00"),
        )
    assert "order" in exc.value.detail


def test_create_invoice_rejects_negative_total(org_a, customer_a, alice):
    with pytest.raises(ValidationError):
        create_invoice(
            organization=org_a,
            actor=alice,
            customer=customer_a,
            invoice_number="INV-1",
            issue_date=ISSUE_DATE,
            total_amount=Decimal("-1.00"),
        )


def test_create_invoice_rejects_invalid_status(org_a, customer_a, alice):
    with pytest.raises(ValidationError):
        create_invoice(
            organization=org_a,
            actor=alice,
            customer=customer_a,
            invoice_number="INV-1",
            issue_date=ISSUE_DATE,
            total_amount=Decimal("1.00"),
            status="refunded",
        )


def test_create_invoice_auto_generates_a_number_when_omitted(org_a, customer_a, alice):
    first = create_invoice(
        organization=org_a,
        actor=alice,
        customer=customer_a,
        issue_date=ISSUE_DATE,
        total_amount=Decimal("1.00"),
    )
    second = create_invoice(
        organization=org_a,
        actor=alice,
        customer=customer_a,
        invoice_number="   ",
        issue_date=ISSUE_DATE,
        total_amount=Decimal("1.00"),
    )

    assert first.invoice_number == "INV-0001"
    assert second.invoice_number == "INV-0002"


def test_auto_numbering_is_per_organization(org_a, org_b, customer_a, customer_b, alice, bob):
    a = create_invoice(
        organization=org_a,
        actor=alice,
        customer=customer_a,
        issue_date=ISSUE_DATE,
        total_amount=Decimal("1.00"),
    )
    b = create_invoice(
        organization=org_b,
        actor=bob,
        customer=customer_b,
        issue_date=ISSUE_DATE,
        total_amount=Decimal("1.00"),
    )

    assert a.invoice_number == "INV-0001"
    assert b.invoice_number == "INV-0001"


def test_create_invoice_rejects_due_date_before_issue_date(org_a, customer_a, alice):
    with pytest.raises(ValidationError):
        create_invoice(
            organization=org_a,
            actor=alice,
            customer=customer_a,
            invoice_number="INV-1",
            issue_date=ISSUE_DATE,
            due_date=ISSUE_DATE - timedelta(days=1),
            total_amount=Decimal("1.00"),
        )


def test_create_invoice_rejects_duplicate_number_in_the_same_organization(
    org_a, customer_a, alice, invoice_a
):
    with pytest.raises(ValidationError):
        create_invoice(
            organization=org_a,
            actor=alice,
            customer=customer_a,
            invoice_number="INV-001",
            issue_date=ISSUE_DATE,
            total_amount=Decimal("1.00"),
        )
    assert Invoice.objects.count() == 1


# --- update ------------------------------------------------------


def test_update_invoice(invoice_a, alice):
    updated = update_invoice(
        invoice=invoice_a,
        actor=alice,
        status=InvoiceStatus.PAID,
        total_amount=Decimal("120.00"),
        notes="Paid in full",
    )
    updated.refresh_from_db()
    assert updated.status == InvoiceStatus.PAID
    assert updated.total_amount == Decimal("120.00")
    assert updated.notes == "Paid in full"


def test_update_invoice_requires_membership(invoice_a, bob):
    with pytest.raises(PermissionDenied):
        update_invoice(invoice=invoice_a, actor=bob, status=InvoiceStatus.SENT)
    invoice_a.refresh_from_db()
    assert invoice_a.status == InvoiceStatus.DRAFT


def test_update_invoice_cannot_change_organization(invoice_a, alice, org_b):
    with pytest.raises(ValidationError) as exc:
        update_invoice(invoice=invoice_a, actor=alice, organization=org_b)
    assert "organization" in exc.value.detail
    invoice_a.refresh_from_db()
    assert invoice_a.organization_id != org_b.id


def test_update_invoice_customer_must_stay_in_the_same_organization(invoice_a, alice, customer_b):
    with pytest.raises(ValidationError):
        update_invoice(invoice=invoice_a, actor=alice, customer=customer_b)


def test_update_invoice_can_reassign_customer_within_the_organization(invoice_a, alice, org_a):
    other = Customer.objects.create(organization=org_a, name="Second")
    update_invoice(invoice=invoice_a, actor=alice, customer=other)
    invoice_a.refresh_from_db()
    assert invoice_a.customer == other


def test_update_invoice_rejects_invalid_data(invoice_a, alice):
    with pytest.raises(ValidationError):
        update_invoice(invoice=invoice_a, actor=alice, total_amount=Decimal("-5.00"))
    invoice_a.refresh_from_db()
    assert invoice_a.total_amount == Decimal("100.00")


def test_update_invoice_rejects_duplicate_number(org_a, customer_a, alice, invoice_a):
    second = create_invoice(
        organization=org_a,
        actor=alice,
        customer=customer_a,
        invoice_number="INV-002",
        issue_date=ISSUE_DATE,
        total_amount=Decimal("1.00"),
    )
    with pytest.raises(ValidationError):
        update_invoice(invoice=second, actor=alice, invoice_number="INV-001")


# --- delete ------------------------------------------------------


def test_delete_invoice(invoice_a, alice):
    delete_invoice(invoice=invoice_a, actor=alice)
    assert Invoice.objects.count() == 0


def test_delete_invoice_requires_membership(invoice_a, bob):
    with pytest.raises(PermissionDenied):
        delete_invoice(invoice=invoice_a, actor=bob)
    assert Invoice.objects.count() == 1
