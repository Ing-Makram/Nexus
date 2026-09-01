from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.orders.models import Order
from apps.orders.selectors import order_for_user, orders_for_user
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


def make_order(org, **overrides):
    customer = overrides.pop("customer", None) or Customer.objects.create(
        organization=org, name="C"
    )
    return Order.objects.create(
        organization=org,
        customer=customer,
        total_amount=overrides.pop("total_amount", Decimal("10.00")),
        **overrides,
    )


def test_orders_for_user_returns_only_member_organization_orders(alice, org_a, org_b):
    mine = make_order(org_a)
    make_order(org_b)

    result = orders_for_user(alice)

    assert list(result) == [mine]


def test_orders_for_user_is_empty_for_a_non_member(django_user_model, org_a):
    carol = make_user(django_user_model, "carol@example.com")
    make_order(org_a)

    assert list(orders_for_user(carol)) == []


def test_order_for_user_returns_the_order_when_it_belongs_to_the_user(alice, org_a):
    order = make_order(org_a)
    assert order_for_user(alice, order.id) == order


def test_order_for_user_returns_none_for_another_organizations_order(alice, org_a, org_b):
    foreign = make_order(org_b)
    assert order_for_user(alice, foreign.id) is None


def test_order_for_user_returns_none_for_a_missing_id(alice, org_a):
    make_order(org_a)
    assert order_for_user(alice, 999_999) is None


def test_orders_for_user_selects_related_organization_and_customer(
    alice, org_a, django_assert_num_queries
):
    make_order(org_a)

    with django_assert_num_queries(1):
        order = orders_for_user(alice).get()
        _ = order.organization.name
        _ = order.customer.name
