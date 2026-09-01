from datetime import date
from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.invoices.models import Invoice
from apps.invoices.selectors import invoice_for_user, invoices_for_user
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


def make_invoice(org, number="INV-001", **overrides):
    customer = overrides.pop("customer", None) or Customer.objects.create(
        organization=org, name="C"
    )
    return Invoice.objects.create(
        organization=org,
        customer=customer,
        invoice_number=number,
        issue_date=ISSUE_DATE,
        total_amount=Decimal("10.00"),
        **overrides,
    )


def test_invoices_for_user_returns_only_member_organization_invoices(alice, org_a, org_b):
    mine = make_invoice(org_a)
    make_invoice(org_b)

    assert list(invoices_for_user(alice)) == [mine]


def test_invoices_for_user_is_empty_for_a_non_member(django_user_model, org_a):
    carol = make_user(django_user_model, "carol@example.com")
    make_invoice(org_a)

    assert list(invoices_for_user(carol)) == []


def test_invoice_for_user_returns_the_invoice_when_it_belongs_to_the_user(alice, org_a):
    invoice = make_invoice(org_a)
    assert invoice_for_user(alice, invoice.id) == invoice


def test_invoice_for_user_returns_none_for_another_organizations_invoice(alice, org_a, org_b):
    foreign = make_invoice(org_b)
    assert invoice_for_user(alice, foreign.id) is None


def test_invoice_for_user_returns_none_for_a_missing_id(alice, org_a):
    make_invoice(org_a)
    assert invoice_for_user(alice, 999_999) is None


def test_invoices_for_user_selects_related_organization_customer_and_order(
    alice, org_a, django_assert_num_queries
):
    customer = Customer.objects.create(organization=org_a, name="Jane")
    order = Order.objects.create(
        organization=org_a, customer=customer, total_amount=Decimal("1.00")
    )
    make_invoice(org_a, customer=customer, order=order)

    with django_assert_num_queries(1):
        invoice = invoices_for_user(alice).get()
        _ = invoice.organization.name
        _ = invoice.customer.name
        _ = invoice.order.status
