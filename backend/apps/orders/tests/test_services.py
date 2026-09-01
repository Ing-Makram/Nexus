from decimal import Decimal

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.customers.models import Customer
from apps.orders.models import Order, OrderStatus
from apps.orders.services import create_order, delete_order, update_order
from apps.organizations.models import Membership, Organization, Role

pytestmark = pytest.mark.django_db


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
def order_a(org_a, customer_a, alice):
    return create_order(
        organization=org_a, actor=alice, customer=customer_a, total_amount=Decimal("10.00")
    )


# --- create --------------------------------------------------------


def test_create_order(org_a, customer_a, alice):
    order = create_order(
        organization=org_a,
        actor=alice,
        customer=customer_a,
        total_amount=Decimal("125.50"),
    )

    assert order.pk is not None
    assert order.organization == org_a
    assert order.customer == customer_a
    assert order.status == OrderStatus.DRAFT
    assert order.total_amount == Decimal("125.50")
    assert order.created_by == alice


def test_create_order_with_status_and_notes(org_a, customer_a, alice):
    order = create_order(
        organization=org_a,
        actor=alice,
        customer=customer_a,
        total_amount=Decimal("1.00"),
        status=OrderStatus.CONFIRMED,
        notes="priority",
    )
    assert order.status == OrderStatus.CONFIRMED
    assert order.notes == "priority"


def test_create_order_requires_membership_in_the_target_organization(org_a, customer_a, bob):
    with pytest.raises(PermissionDenied):
        create_order(
            organization=org_a, actor=bob, customer=customer_a, total_amount=Decimal("1.00")
        )
    assert Order.objects.count() == 0


def test_create_order_customer_must_belong_to_the_same_organization(org_a, customer_b, alice):
    with pytest.raises(ValidationError) as exc:
        create_order(
            organization=org_a, actor=alice, customer=customer_b, total_amount=Decimal("1.00")
        )
    assert "customer" in exc.value.detail
    assert Order.objects.count() == 0


def test_create_order_rejects_negative_total(org_a, customer_a, alice):
    with pytest.raises(ValidationError):
        create_order(
            organization=org_a, actor=alice, customer=customer_a, total_amount=Decimal("-1.00")
        )
    assert Order.objects.count() == 0


def test_create_order_rejects_invalid_status(org_a, customer_a, alice):
    with pytest.raises(ValidationError):
        create_order(
            organization=org_a,
            actor=alice,
            customer=customer_a,
            total_amount=Decimal("1.00"),
            status="shipped",
        )
    assert Order.objects.count() == 0


def test_create_order_rejects_missing_total(org_a, customer_a, alice):
    with pytest.raises(ValidationError):
        create_order(organization=org_a, actor=alice, customer=customer_a, total_amount=None)


# --- update --------------------------------------------------------


def test_update_order(order_a, alice):
    updated = update_order(
        order=order_a,
        actor=alice,
        status=OrderStatus.CONFIRMED,
        total_amount=Decimal("99.99"),
        notes="ok",
    )
    updated.refresh_from_db()
    assert updated.status == OrderStatus.CONFIRMED
    assert updated.total_amount == Decimal("99.99")
    assert updated.notes == "ok"


def test_update_order_requires_membership(order_a, bob):
    with pytest.raises(PermissionDenied):
        update_order(order=order_a, actor=bob, status=OrderStatus.PENDING)
    order_a.refresh_from_db()
    assert order_a.status == OrderStatus.DRAFT


def test_update_order_cannot_change_organization(order_a, alice, org_b):
    with pytest.raises(ValidationError) as exc:
        update_order(order=order_a, actor=alice, organization=org_b)
    assert "organization" in exc.value.detail
    order_a.refresh_from_db()
    assert order_a.organization_id != org_b.id


def test_update_order_customer_must_stay_in_the_same_organization(order_a, alice, customer_b):
    with pytest.raises(ValidationError):
        update_order(order=order_a, actor=alice, customer=customer_b)


def test_update_order_can_reassign_customer_within_the_organization(order_a, alice, org_a):
    other_customer = Customer.objects.create(organization=org_a, name="Second")
    update_order(order=order_a, actor=alice, customer=other_customer)
    order_a.refresh_from_db()
    assert order_a.customer == other_customer


def test_update_order_rejects_invalid_data(order_a, alice):
    with pytest.raises(ValidationError):
        update_order(order=order_a, actor=alice, total_amount=Decimal("-5.00"))
    order_a.refresh_from_db()
    assert order_a.total_amount == Decimal("10.00")


# --- delete --------------------------------------------------------


def test_delete_order(order_a, alice):
    delete_order(order=order_a, actor=alice)
    assert Order.objects.count() == 0


def test_delete_order_requires_membership(order_a, bob):
    with pytest.raises(PermissionDenied):
        delete_order(order=order_a, actor=bob)
    assert Order.objects.count() == 1
