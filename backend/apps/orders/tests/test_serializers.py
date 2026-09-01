import json
from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.orders.models import Order, OrderStatus
from apps.orders.serializers import OrderSerializer
from apps.organizations.models import Membership, Organization, Role

pytestmark = pytest.mark.django_db

FIELDS = {
    "id",
    "organization",
    "customer",
    "status",
    "total_amount",
    "notes",
    "created_by",
    "created_at",
    "updated_at",
}


class Ctx:
    """Minimal request stand-in for serializer context."""

    def __init__(self, user):
        self.user = user


def make_user(django_user_model, email):
    return django_user_model.objects.create_user(email=email, password="pw12345!")


@pytest.fixture
def alice(django_user_model):
    return make_user(django_user_model, "alice@example.com")


@pytest.fixture
def org_a(alice):
    org = Organization.objects.create(name="Org A")
    Membership.objects.create(organization=org, user=alice, role=Role.OWNER)
    return org


@pytest.fixture
def org_b(django_user_model):
    org = Organization.objects.create(name="Org B")
    Membership.objects.create(
        organization=org, user=make_user(django_user_model, "bob@example.com"), role=Role.OWNER
    )
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


def ser(user, **kwargs):
    return OrderSerializer(context={"request": Ctx(user)}, **kwargs)


# --- representation --------------------------------------------------


def test_serialized_order_has_exactly_the_allowed_fields(alice, order_a):
    data = ser(alice, instance=order_a).data

    assert set(data) == FIELDS
    assert data["organization"] == order_a.organization_id
    assert data["customer"] == order_a.customer_id
    assert data["total_amount"] == "10.00"


def test_serialization_never_exposes_secrets_or_nested_objects(alice, order_a):
    blob = json.dumps(ser(alice, instance=order_a).data)

    for needle in ("password", "token", "secret", "access", "refresh"):
        assert needle not in blob
    assert isinstance(ser(alice, instance=order_a).data["organization"], int)
    assert isinstance(ser(alice, instance=order_a).data["customer"], int)


def test_id_and_timestamps_are_read_only():
    fields = OrderSerializer().fields
    assert fields["id"].read_only is True
    assert fields["created_at"].read_only is True
    assert fields["updated_at"].read_only is True


# --- create validation --------------------------------------------


def test_valid_create_payload(alice, org_a, customer_a):
    serializer = ser(
        alice,
        data={
            "organization": org_a.id,
            "customer": customer_a.id,
            "status": OrderStatus.PENDING,
            "total_amount": "42.00",
            "notes": "hi",
        },
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["organization"] == org_a
    assert serializer.validated_data["customer"] == customer_a


def test_organization_must_be_one_the_user_belongs_to(alice, org_b, customer_b):
    serializer = ser(
        alice, data={"organization": org_b.id, "customer": customer_b.id, "total_amount": "1.00"}
    )
    assert not serializer.is_valid()
    assert "organization" in serializer.errors


def test_customer_must_be_one_of_the_users_customers(alice, org_a, customer_b):
    serializer = ser(
        alice, data={"organization": org_a.id, "customer": customer_b.id, "total_amount": "1.00"}
    )
    assert not serializer.is_valid()
    assert "customer" in serializer.errors


def test_customer_must_belong_to_the_selected_organization(
    django_user_model, alice, org_a, customer_a
):
    # alice also belongs to another org that owns `foreign_customer`
    other = Organization.objects.create(name="Other")
    Membership.objects.create(organization=other, user=alice, role=Role.OWNER)
    foreign_customer = Customer.objects.create(organization=other, name="Foreign")

    serializer = ser(
        alice,
        data={"organization": org_a.id, "customer": foreign_customer.id, "total_amount": "1.00"},
    )
    assert not serializer.is_valid()
    assert "customer" in serializer.errors


def test_invalid_status_is_rejected(alice, org_a, customer_a):
    serializer = ser(
        alice,
        data={
            "organization": org_a.id,
            "customer": customer_a.id,
            "status": "shipped",
            "total_amount": "1.00",
        },
    )
    assert not serializer.is_valid()
    assert "status" in serializer.errors


def test_negative_total_amount_is_rejected(alice, org_a, customer_a):
    serializer = ser(
        alice,
        data={"organization": org_a.id, "customer": customer_a.id, "total_amount": "-1.00"},
    )
    assert not serializer.is_valid()
    assert "total_amount" in serializer.errors


def test_nothing_is_selectable_without_an_authenticated_request(org_a, customer_a):
    serializer = OrderSerializer(
        data={"organization": org_a.id, "customer": customer_a.id, "total_amount": "1.00"}
    )
    assert not serializer.is_valid()
    assert "organization" in serializer.errors


# --- update validation --------------------------------------------


def test_organization_is_immutable_on_update(alice, order_a, org_b):
    serializer = ser(
        alice,
        instance=order_a,
        data={"organization": org_b.id, "status": OrderStatus.PENDING},
        partial=True,
    )
    assert serializer.is_valid(), serializer.errors
    assert "organization" not in serializer.validated_data
    assert serializer.validated_data["status"] == OrderStatus.PENDING


def test_update_customer_must_stay_in_the_orders_organization(alice, order_a, customer_b):
    serializer = ser(alice, instance=order_a, data={"customer": customer_b.id}, partial=True)
    assert not serializer.is_valid()
    assert "customer" in serializer.errors


def test_update_can_reassign_customer_within_the_organization(alice, order_a, org_a):
    other = Customer.objects.create(organization=org_a, name="Second")
    serializer = ser(alice, instance=order_a, data={"customer": other.id}, partial=True)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["customer"] == other
