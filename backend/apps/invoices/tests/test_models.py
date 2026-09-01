from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.customers.models import Customer
from apps.invoices.models import Invoice, InvoiceStatus
from apps.orders.models import Order
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db

ISSUE_DATE = date(2026, 1, 1)


@pytest.fixture
def organization():
    return Organization.objects.create(name="Acme")


@pytest.fixture
def customer(organization):
    return Customer.objects.create(organization=organization, name="Jane Doe")


@pytest.fixture
def order(organization, customer):
    return Order.objects.create(
        organization=organization, customer=customer, total_amount=Decimal("10.00")
    )


def make_invoice(organization, customer, **overrides):
    data = {
        "organization": organization,
        "customer": customer,
        "invoice_number": "INV-001",
        "issue_date": ISSUE_DATE,
        "total_amount": Decimal("100.00"),
    }
    data.update(overrides)
    return Invoice.objects.create(**data)


# --- creation / defaults ---------------------------------------------


def test_create_invoice_with_required_fields(organization, customer):
    invoice = make_invoice(organization, customer)

    assert invoice.pk is not None
    assert invoice.organization == organization
    assert invoice.customer == customer
    assert invoice.order is None
    assert invoice.status == InvoiceStatus.DRAFT
    assert invoice.due_date is None
    assert invoice.notes == ""


def test_create_invoice_with_all_fields(organization, customer, order):
    invoice = make_invoice(
        organization,
        customer,
        order=order,
        invoice_number="INV-042",
        status=InvoiceStatus.SENT,
        issue_date=ISSUE_DATE,
        due_date=ISSUE_DATE + timedelta(days=30),
        total_amount=Decimal("2500.00"),
        notes="Net 30",
    )
    invoice.full_clean()

    assert invoice.order == order
    assert invoice.status == InvoiceStatus.SENT
    assert invoice.due_date == ISSUE_DATE + timedelta(days=30)


# --- required fields ------------------------------------------------


def test_organization_is_required(customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        Invoice.objects.create(
            customer=customer,
            invoice_number="INV-1",
            issue_date=ISSUE_DATE,
            total_amount=Decimal("1.00"),
        )


def test_customer_is_required(organization):
    with pytest.raises(IntegrityError), transaction.atomic():
        Invoice.objects.create(
            organization=organization,
            invoice_number="INV-1",
            issue_date=ISSUE_DATE,
            total_amount=Decimal("1.00"),
        )


def test_issue_date_is_required(organization, customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        Invoice.objects.create(
            organization=organization,
            customer=customer,
            invoice_number="INV-1",
            total_amount=Decimal("1.00"),
        )


def test_total_amount_is_required(organization, customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        Invoice.objects.create(
            organization=organization,
            customer=customer,
            invoice_number="INV-1",
            issue_date=ISSUE_DATE,
        )


def test_invoice_number_is_required(organization, customer):
    invoice = Invoice(
        organization=organization,
        customer=customer,
        issue_date=ISSUE_DATE,
        total_amount=Decimal("1.00"),
    )
    with pytest.raises(ValidationError):
        invoice.full_clean()


def test_blank_invoice_number_is_rejected_by_the_database(organization, customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        make_invoice(organization, customer, invoice_number="")


# --- optional fields ----------------------------------------------


def test_order_is_optional(organization, customer):
    invoice = make_invoice(organization, customer)
    assert invoice.order is None


def test_due_date_is_optional(organization, customer):
    invoice = make_invoice(organization, customer, due_date=None)
    assert invoice.due_date is None


# --- status -----------------------------------------------------


def test_status_choices_are_the_expected_five():
    assert set(InvoiceStatus.values) == {"draft", "sent", "paid", "overdue", "void"}


@pytest.mark.parametrize("status", InvoiceStatus.values)
def test_every_status_choice_is_accepted(organization, customer, status):
    invoice = make_invoice(organization, customer, status=status)
    invoice.full_clean()
    assert invoice.status == status


def test_invalid_status_fails_validation(organization, customer):
    invoice = Invoice(
        organization=organization,
        customer=customer,
        invoice_number="INV-1",
        issue_date=ISSUE_DATE,
        total_amount=Decimal("1.00"),
        status="refunded",
    )
    with pytest.raises(ValidationError):
        invoice.full_clean()


def test_invalid_status_is_rejected_by_the_database(organization, customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        make_invoice(organization, customer, status="refunded")


# --- total_amount --------------------------------------------


def test_total_amount_keeps_two_decimal_places(organization, customer):
    invoice = make_invoice(organization, customer, total_amount=Decimal("1234567890.12"))
    invoice.refresh_from_db()

    assert invoice.total_amount == Decimal("1234567890.12")
    assert invoice.total_amount.as_tuple().exponent == -2


def test_negative_total_amount_is_rejected(organization, customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        make_invoice(organization, customer, total_amount=Decimal("-0.01"))


def test_zero_total_amount_is_allowed(organization, customer):
    invoice = make_invoice(organization, customer, total_amount=Decimal("0.00"))
    assert invoice.total_amount == Decimal("0.00")


# --- dates ---------------------------------------------------


def test_due_date_before_issue_date_is_rejected(organization, customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        make_invoice(
            organization,
            customer,
            issue_date=ISSUE_DATE,
            due_date=ISSUE_DATE - timedelta(days=1),
        )


def test_due_date_equal_to_issue_date_is_allowed(organization, customer):
    invoice = make_invoice(organization, customer, due_date=ISSUE_DATE)
    assert invoice.due_date == ISSUE_DATE


# --- relationships -----------------------------------------


def test_organization_relationship(organization, customer):
    invoice = make_invoice(organization, customer)
    assert list(organization.invoices.all()) == [invoice]


def test_customer_relationship(organization, customer):
    invoice = make_invoice(organization, customer)
    assert list(customer.invoices.all()) == [invoice]


def test_order_relationship_when_set(organization, customer, order):
    invoice = make_invoice(organization, customer, order=order)
    assert list(order.invoices.all()) == [invoice]


def test_customer_must_belong_to_the_same_organization(organization):
    other_org = Organization.objects.create(name="Other")
    foreign_customer = Customer.objects.create(organization=other_org, name="Bob")

    invoice = Invoice(
        organization=organization,
        customer=foreign_customer,
        invoice_number="INV-1",
        issue_date=ISSUE_DATE,
        total_amount=Decimal("1.00"),
    )
    with pytest.raises(ValidationError) as exc:
        invoice.full_clean()
    assert "customer" in exc.value.message_dict


def test_order_must_belong_to_the_same_organization(organization, customer):
    other_org = Organization.objects.create(name="Other")
    other_customer = Customer.objects.create(organization=other_org, name="Bob")
    foreign_order = Order.objects.create(
        organization=other_org, customer=other_customer, total_amount=Decimal("1.00")
    )

    invoice = Invoice(
        organization=organization,
        customer=customer,
        order=foreign_order,
        invoice_number="INV-1",
        issue_date=ISSUE_DATE,
        total_amount=Decimal("1.00"),
    )
    with pytest.raises(ValidationError) as exc:
        invoice.full_clean()
    assert "order" in exc.value.message_dict


# --- invoice number uniqueness ---------------------------


def test_invoice_number_is_unique_within_an_organization(organization, customer):
    make_invoice(organization, customer, invoice_number="INV-100")
    with pytest.raises(IntegrityError), transaction.atomic():
        make_invoice(organization, customer, invoice_number="INV-100")


def test_invoice_number_can_repeat_across_organizations(organization, customer):
    make_invoice(organization, customer, invoice_number="INV-100")

    other_org = Organization.objects.create(name="Other")
    other_customer = Customer.objects.create(organization=other_org, name="Bob")
    other_invoice = make_invoice(other_org, other_customer, invoice_number="INV-100")

    assert other_invoice.pk is not None


# --- timestamps / ordering / str -----------------------


def test_timestamps_are_configured_and_populated(organization, customer):
    assert Invoice._meta.get_field("created_at").auto_now_add is True
    assert Invoice._meta.get_field("updated_at").auto_now is True

    invoice = make_invoice(organization, customer)
    created_at, updated_at = invoice.created_at, invoice.updated_at
    assert created_at is not None and updated_at is not None

    invoice.notes = "changed"
    invoice.save()
    invoice.refresh_from_db()

    assert invoice.created_at == created_at
    assert invoice.updated_at >= updated_at


def test_default_ordering_is_newest_first(organization, customer):
    assert Invoice._meta.ordering == ["-created_at"]

    now = timezone.now()
    oldest = make_invoice(organization, customer, invoice_number="A")
    middle = make_invoice(organization, customer, invoice_number="B")
    newest = make_invoice(organization, customer, invoice_number="C")
    Invoice.objects.filter(pk=oldest.pk).update(created_at=now - timedelta(hours=2))
    Invoice.objects.filter(pk=middle.pk).update(created_at=now - timedelta(hours=1))
    Invoice.objects.filter(pk=newest.pk).update(created_at=now)

    assert list(Invoice.objects.all()) == [newest, middle, oldest]


def test_str_is_useful(organization, customer):
    invoice = make_invoice(
        organization, customer, invoice_number="INV-777", status=InvoiceStatus.PAID
    )
    text = str(invoice)

    assert "INV-777" in text
    assert "Jane Doe" in text
    assert "paid" in text


# --- indexes / constraints -----------------------------


def test_indexes_and_constraints_are_declared():
    index_fields = {tuple(index.fields) for index in Invoice._meta.indexes}
    assert ("organization", "-created_at") in index_fields
    assert ("organization", "status") in index_fields
    assert ("organization", "customer") in index_fields
    assert ("organization", "due_date") in index_fields

    constraint_names = {c.name for c in Invoice._meta.constraints}
    assert constraint_names == {
        "invoice_number_unique_per_organization",
        "invoice_number_not_empty",
        "invoice_total_amount_non_negative",
        "invoice_status_valid",
        "invoice_due_date_not_before_issue_date",
    }


# --- deletion behaviour --------------------------------


def test_deleting_a_customer_with_invoices_is_protected(organization, customer):
    make_invoice(organization, customer)

    with pytest.raises(ProtectedError):
        customer.delete()

    assert Invoice.objects.count() == 1


def test_deleting_an_order_nulls_the_invoice_and_keeps_it(organization, customer, order):
    invoice = make_invoice(organization, customer, order=order)

    order.delete()

    invoice.refresh_from_db()
    assert invoice.order is None
    assert Invoice.objects.filter(pk=invoice.pk).exists()


def test_deleting_an_organization_with_invoices_is_protected(organization, customer):
    make_invoice(organization, customer)

    with pytest.raises(ProtectedError):
        organization.delete()

    assert Invoice.objects.count() == 1
    assert Organization.objects.filter(pk=organization.pk).exists()


def test_deleting_an_organization_after_its_invoices_are_removed_cascades(organization, customer):
    make_invoice(organization, customer)
    Invoice.objects.filter(organization=organization).delete()

    organization.delete()

    assert Customer.objects.count() == 0
    assert Invoice.objects.count() == 0
