from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.customers.models import Customer
from apps.orders.models import Order, OrderStatus
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization():
    return Organization.objects.create(name="Acme")


@pytest.fixture
def customer(organization):
    return Customer.objects.create(organization=organization, name="Jane Doe")


def make_order(organization, customer, **overrides):
    data = {
        "organization": organization,
        "customer": customer,
        "total_amount": Decimal("10.00"),
    }
    data.update(overrides)
    return Order.objects.create(**data)


# --- creation / defaults ------------------------------------------------


def test_create_order_with_required_fields(organization, customer):
    order = make_order(organization, customer)

    assert order.pk is not None
    assert order.organization == organization
    assert order.customer == customer
    assert order.total_amount == Decimal("10.00")
    assert order.status == OrderStatus.DRAFT  # default
    assert order.notes == ""


def test_create_order_with_all_fields(organization, customer):
    order = make_order(
        organization,
        customer,
        status=OrderStatus.CONFIRMED,
        total_amount=Decimal("199.99"),
        notes="Rush delivery",
    )
    order.full_clean()

    assert order.status == OrderStatus.CONFIRMED
    assert order.notes == "Rush delivery"


# --- required fields --------------------------------------------------


def test_organization_is_required(customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.create(customer=customer, total_amount=Decimal("1.00"))


def test_customer_is_required(organization):
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.create(organization=organization, total_amount=Decimal("1.00"))


def test_total_amount_is_required(organization, customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.create(organization=organization, customer=customer)


# --- status ---------------------------------------------------------


def test_status_choices_are_the_expected_five():
    assert set(OrderStatus.values) == {
        "draft",
        "pending",
        "confirmed",
        "cancelled",
        "completed",
    }


@pytest.mark.parametrize("status", OrderStatus.values)
def test_every_status_choice_is_accepted(organization, customer, status):
    order = make_order(organization, customer, status=status)
    order.full_clean()
    assert order.status == status


def test_invalid_status_fails_validation(organization, customer):
    order = Order(
        organization=organization,
        customer=customer,
        total_amount=Decimal("1.00"),
        status="shipped",
    )
    with pytest.raises(ValidationError):
        order.full_clean()


def test_invalid_status_rejected_by_the_database(organization, customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.create(
            organization=organization,
            customer=customer,
            total_amount=Decimal("1.00"),
            status="shipped",
        )


# --- total_amount --------------------------------------------------


def test_total_amount_keeps_two_decimal_places(organization, customer):
    order = make_order(organization, customer, total_amount=Decimal("1234567890.12"))
    order.refresh_from_db()

    assert order.total_amount == Decimal("1234567890.12")
    assert order.total_amount.as_tuple().exponent == -2


def test_negative_total_amount_is_rejected(organization, customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.create(
            organization=organization,
            customer=customer,
            total_amount=Decimal("-1.00"),
        )


def test_zero_total_amount_is_allowed(organization, customer):
    order = make_order(organization, customer, total_amount=Decimal("0.00"))
    assert order.total_amount == Decimal("0.00")


# --- relationships -------------------------------------------------


def test_organization_relationship(organization, customer):
    order = make_order(organization, customer)
    assert list(organization.orders.all()) == [order]


def test_customer_relationship(organization, customer):
    order = make_order(organization, customer)
    assert list(customer.orders.all()) == [order]


def test_customer_must_belong_to_the_same_organization(organization):
    other_org = Organization.objects.create(name="Other")
    foreign_customer = Customer.objects.create(organization=other_org, name="Bob")

    order = Order(
        organization=organization,
        customer=foreign_customer,
        total_amount=Decimal("1.00"),
    )
    with pytest.raises(ValidationError):
        order.full_clean()


# --- timestamps --------------------------------------------------


def test_timestamps_are_configured_and_populated(organization, customer):
    assert Order._meta.get_field("created_at").auto_now_add is True
    assert Order._meta.get_field("updated_at").auto_now is True

    order = make_order(organization, customer)
    created_at, updated_at = order.created_at, order.updated_at
    assert created_at is not None and updated_at is not None

    order.notes = "changed"
    order.save()
    order.refresh_from_db()

    assert order.created_at == created_at
    assert order.updated_at >= updated_at


# --- ordering --------------------------------------------------


def test_default_ordering_is_newest_first(organization, customer):
    assert Order._meta.ordering == ["-created_at"]

    now = timezone.now()
    oldest = make_order(organization, customer)
    middle = make_order(organization, customer)
    newest = make_order(organization, customer)
    Order.objects.filter(pk=oldest.pk).update(created_at=now - timedelta(hours=2))
    Order.objects.filter(pk=middle.pk).update(created_at=now - timedelta(hours=1))
    Order.objects.filter(pk=newest.pk).update(created_at=now)

    assert list(Order.objects.all()) == [newest, middle, oldest]


# --- deletion behaviour ---------------------------------------


def test_deleting_an_organization_with_no_orders_cascades_its_customers(organization, customer):
    organization.delete()

    assert Customer.objects.count() == 0
    assert Order.objects.count() == 0


def test_deleting_an_organization_after_its_orders_are_removed_cascades(organization, customer):
    make_order(organization, customer)
    Order.objects.filter(organization=organization).delete()

    organization.delete()

    assert Order.objects.count() == 0
    assert Customer.objects.count() == 0


def test_deleting_an_organization_with_orders_is_protected(organization, customer):
    # `Order.customer` is PROTECT, and deleting the organization would cascade
    # the customer, so the organization cannot be deleted while orders exist.
    make_order(organization, customer)

    with pytest.raises(ProtectedError):
        organization.delete()

    assert Order.objects.count() == 1
    assert Organization.objects.filter(pk=organization.pk).exists()


def test_deleting_a_customer_with_orders_is_protected(organization, customer):
    make_order(organization, customer)

    with pytest.raises(ProtectedError):
        customer.delete()

    assert Order.objects.count() == 1


def test_deleting_a_customer_without_orders_is_allowed(organization, customer):
    customer.delete()
    assert Customer.objects.count() == 0


# --- str / indexes / constraints ---------------------------


def test_str_is_useful(organization, customer):
    order = make_order(organization, customer, status=OrderStatus.PENDING)
    text = str(order)

    assert f"#{order.pk}" in text
    assert "Jane Doe" in text
    assert "pending" in text


def test_indexes_and_constraints_are_declared():
    index_fields = {tuple(index.fields) for index in Order._meta.indexes}
    assert ("organization", "-created_at") in index_fields
    assert ("organization", "status") in index_fields
    assert ("organization", "customer") in index_fields

    constraint_names = {c.name for c in Order._meta.constraints}
    assert constraint_names == {
        "order_total_amount_non_negative",
        "order_status_valid",
    }
