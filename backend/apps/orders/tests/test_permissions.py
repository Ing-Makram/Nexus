from decimal import Decimal

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.customers.models import Customer
from apps.orders.models import Order
from apps.orders.permissions import CanManageOrders, CanReadOrders
from apps.organizations.models import Membership, Organization, Role

pytestmark = pytest.mark.django_db


class FakeRequest:
    """Minimal stand-in exposing only what the permission classes read."""

    def __init__(self, user, method="GET", data=None):
        self.user = user
        self.method = method
        self.data = data or {}


class FakeView:
    pass


def make_user(django_user_model, email):
    return django_user_model.objects.create_user(email=email, password="pw12345!")


@pytest.fixture
def org(django_user_model):
    organization = Organization.objects.create(name="Acme")
    for email, role in [
        ("owner@x.com", Role.OWNER),
        ("admin@x.com", Role.ADMIN),
        ("member@x.com", Role.MEMBER),
    ]:
        Membership.objects.create(
            organization=organization, user=make_user(django_user_model, email), role=role
        )
    return organization


def user_with_role(org, role):
    return Membership.objects.get(organization=org, role=role).user


@pytest.fixture
def order(org):
    customer = Customer.objects.create(organization=org, name="C")
    return Order.objects.create(organization=org, customer=customer, total_amount=Decimal("1.00"))


# --- read -------------------------------------------------------------


def test_read_requires_authentication():
    assert CanReadOrders().has_permission(FakeRequest(AnonymousUser()), FakeView()) is False


@pytest.mark.parametrize("role", [Role.OWNER, Role.ADMIN, Role.MEMBER])
def test_any_member_can_read_an_order(org, order, role):
    request = FakeRequest(user_with_role(org, role))
    assert CanReadOrders().has_object_permission(request, FakeView(), order) is True


def test_non_member_cannot_read_an_order(django_user_model, order):
    outsider = make_user(django_user_model, "outsider@x.com")
    assert CanReadOrders().has_object_permission(FakeRequest(outsider), FakeView(), order) is False


# --- manage (object level) -----------------------------------------


@pytest.mark.parametrize("role", [Role.OWNER, Role.ADMIN])
def test_owner_and_admin_can_manage_an_order(org, order, role):
    request = FakeRequest(user_with_role(org, role), method="PATCH")
    assert CanManageOrders().has_object_permission(request, FakeView(), order) is True


def test_plain_member_cannot_manage_an_order(org, order):
    request = FakeRequest(user_with_role(org, Role.MEMBER), method="DELETE")
    assert CanManageOrders().has_object_permission(request, FakeView(), order) is False


def test_non_member_cannot_manage_an_order(django_user_model, order):
    outsider = make_user(django_user_model, "outsider@x.com")
    request = FakeRequest(outsider, method="PATCH")
    assert CanManageOrders().has_object_permission(request, FakeView(), order) is False


def test_object_permission_accepts_a_bare_organization(org):
    request = FakeRequest(user_with_role(org, Role.ADMIN))
    assert CanManageOrders().has_object_permission(request, FakeView(), org) is True


# --- manage (create / has_permission) ------------------------------


def test_admin_may_create_in_their_organization(org):
    request = FakeRequest(
        user_with_role(org, Role.ADMIN), method="POST", data={"organization": org.id}
    )
    assert CanManageOrders().has_permission(request, FakeView()) is True


def test_member_may_not_create_orders(org):
    request = FakeRequest(
        user_with_role(org, Role.MEMBER), method="POST", data={"organization": org.id}
    )
    assert CanManageOrders().has_permission(request, FakeView()) is False


def test_create_with_out_of_scope_organization_is_deferred_to_the_serializer(
    django_user_model, org
):
    other = Organization.objects.create(name="Other")
    request = FakeRequest(
        user_with_role(org, Role.ADMIN), method="POST", data={"organization": other.id}
    )
    # Not a member of `other` -> permission defers (True); serializer will 400.
    assert CanManageOrders().has_permission(request, FakeView()) is True


def test_manage_has_permission_only_checks_auth_for_non_post(org):
    request = FakeRequest(user_with_role(org, Role.MEMBER), method="GET")
    assert CanManageOrders().has_permission(request, FakeView()) is True

    assert CanManageOrders().has_permission(FakeRequest(AnonymousUser()), FakeView()) is False
