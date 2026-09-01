from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.customers.models import Customer
from apps.invoices.models import Invoice
from apps.invoices.permissions import CanManageInvoices, CanReadInvoices
from apps.organizations.models import Membership, Organization, Role

pytestmark = pytest.mark.django_db

ISSUE_DATE = date(2026, 1, 1)


class FakeRequest:
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
def invoice(org):
    customer = Customer.objects.create(organization=org, name="C")
    return Invoice.objects.create(
        organization=org,
        customer=customer,
        invoice_number="INV-1",
        issue_date=ISSUE_DATE,
        total_amount=Decimal("1.00"),
    )


def test_read_requires_authentication():
    assert CanReadInvoices().has_permission(FakeRequest(AnonymousUser()), FakeView()) is False


@pytest.mark.parametrize("role", [Role.OWNER, Role.ADMIN, Role.MEMBER])
def test_any_member_can_read_an_invoice(org, invoice, role):
    request = FakeRequest(user_with_role(org, role))
    assert CanReadInvoices().has_object_permission(request, FakeView(), invoice) is True


def test_non_member_cannot_read_an_invoice(django_user_model, invoice):
    outsider = make_user(django_user_model, "outsider@x.com")
    assert (
        CanReadInvoices().has_object_permission(FakeRequest(outsider), FakeView(), invoice) is False
    )


@pytest.mark.parametrize("role", [Role.OWNER, Role.ADMIN])
def test_owner_and_admin_can_manage_an_invoice(org, invoice, role):
    request = FakeRequest(user_with_role(org, role), method="PATCH")
    assert CanManageInvoices().has_object_permission(request, FakeView(), invoice) is True


def test_plain_member_cannot_manage_an_invoice(org, invoice):
    request = FakeRequest(user_with_role(org, Role.MEMBER), method="DELETE")
    assert CanManageInvoices().has_object_permission(request, FakeView(), invoice) is False


def test_object_permission_accepts_a_bare_organization(org):
    request = FakeRequest(user_with_role(org, Role.ADMIN))
    assert CanManageInvoices().has_object_permission(request, FakeView(), org) is True


def test_admin_may_create_in_their_organization(org):
    request = FakeRequest(
        user_with_role(org, Role.ADMIN), method="POST", data={"organization": org.id}
    )
    assert CanManageInvoices().has_permission(request, FakeView()) is True


def test_member_may_not_create_invoices(org):
    request = FakeRequest(
        user_with_role(org, Role.MEMBER), method="POST", data={"organization": org.id}
    )
    assert CanManageInvoices().has_permission(request, FakeView()) is False


def test_create_with_out_of_scope_organization_is_deferred_to_the_serializer(org):
    other = Organization.objects.create(name="Other")
    request = FakeRequest(
        user_with_role(org, Role.ADMIN), method="POST", data={"organization": other.id}
    )
    assert CanManageInvoices().has_permission(request, FakeView()) is True
