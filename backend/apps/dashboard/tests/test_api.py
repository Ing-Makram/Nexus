from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.customers.models import Customer
from apps.invoices.models import Invoice, InvoiceStatus
from apps.orders.models import Order, OrderStatus
from apps.organizations.models import Membership, Organization, Role

pytestmark = pytest.mark.django_db

URL = reverse("dashboard:dashboard")


def make_user(django_user_model, email):
    return django_user_model.objects.create_user(email=email, password="pw12345!")


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def org(django_user_model):
    organization = Organization.objects.create(name="Acme")
    Membership.objects.create(
        organization=organization,
        user=make_user(django_user_model, "member@acme.test"),
        role=Role.MEMBER,
    )
    return organization


@pytest.fixture
def member(org):
    return Membership.objects.get(organization=org, role=Role.MEMBER).user


@pytest.fixture
def populated(org):
    a = Customer.objects.create(organization=org, name="Customer A")
    Customer.objects.create(organization=org, name="Customer B")

    Order.objects.create(organization=org, customer=a, status=OrderStatus.DRAFT, total_amount="10")
    Order.objects.create(
        organization=org, customer=a, status=OrderStatus.COMPLETED, total_amount="20"
    )

    Invoice.objects.create(
        organization=org,
        customer=a,
        invoice_number="INV-1",
        status=InvoiceStatus.PAID,
        issue_date=date(2026, 1, 1),
        total_amount=Decimal("100.00"),
    )
    Invoice.objects.create(
        organization=org,
        customer=a,
        invoice_number="INV-2",
        status=InvoiceStatus.SENT,
        issue_date=date(2026, 1, 2),
        total_amount=Decimal("50.00"),
    )
    Invoice.objects.create(
        organization=org,
        customer=a,
        invoice_number="INV-3",
        status=InvoiceStatus.OVERDUE,
        issue_date=date(2026, 1, 3),
        total_amount=Decimal("25.00"),
    )
    Invoice.objects.create(
        organization=org,
        customer=a,
        invoice_number="INV-4",
        status=InvoiceStatus.VOID,
        issue_date=date(2026, 1, 4),
        total_amount=Decimal("999.00"),
    )
    return org


def test_requires_authentication():
    assert APIClient().get(URL, {"organization": 1}).status_code == 401


def test_organization_query_param_is_required(member):
    assert client_for(member).get(URL).status_code == 400


def test_returns_404_for_an_organization_the_user_does_not_belong_to(django_user_model, member):
    other = Organization.objects.create(name="Other")
    Membership.objects.create(
        organization=other, user=make_user(django_user_model, "x@other.test"), role=Role.OWNER
    )
    assert client_for(member).get(URL, {"organization": other.id}).status_code == 404


def test_aggregates_are_scoped_and_correct(populated, member):
    response = client_for(member).get(URL, {"organization": populated.id})
    assert response.status_code == 200
    body = response.json()

    assert body["organization"] == populated.id
    assert body["customers"]["total"] == 2

    assert body["orders"]["total"] == 2
    assert body["orders"]["by_status"] == {"draft": 1, "completed": 1}

    inv = body["invoices"]
    assert inv["total"] == 4
    assert inv["by_status"] == {"paid": 1, "sent": 1, "overdue": 1, "void": 1}
    assert inv["total_amount"] == "175.00"  # 100 + 50 + 25, void excluded
    assert inv["paid_amount"] == "100.00"
    assert inv["outstanding_amount"] == "75.00"  # sent + overdue
    assert inv["overdue_count"] == 1


def test_recent_lists_are_limited_and_only_expose_safe_fields(populated, member):
    body = client_for(member).get(URL, {"organization": populated.id}).json()

    assert len(body["recent_orders"]) == 2
    assert len(body["recent_invoices"]) == 4
    order = body["recent_orders"][0]
    assert set(order) == {"id", "customer", "status", "total_amount", "created_at"}
    invoice = body["recent_invoices"][0]
    assert set(invoice) == {
        "id",
        "invoice_number",
        "customer",
        "status",
        "total_amount",
        "issue_date",
        "due_date",
    }


def test_empty_organization_returns_zeroes(org, member):
    body = client_for(member).get(URL, {"organization": org.id}).json()
    assert body["customers"]["total"] == 0
    assert body["orders"] == {"total": 0, "by_status": {}}
    assert body["invoices"]["total_amount"] == "0.00"
    assert body["invoices"]["outstanding_amount"] == "0.00"
    assert body["recent_orders"] == []


def test_does_not_leak_other_organizations_data(populated, django_user_model):
    """A second org's numbers never bleed into the first org's dashboard."""
    other = Organization.objects.create(name="Other")
    other_member = make_user(django_user_model, "om@other.test")
    Membership.objects.create(organization=other, user=other_member, role=Role.OWNER)
    oc = Customer.objects.create(organization=other, name="Other Cust")
    Invoice.objects.create(
        organization=other,
        customer=oc,
        invoice_number="O-1",
        status=InvoiceStatus.PAID,
        issue_date=date(2026, 1, 1),
        total_amount=Decimal("5000.00"),
    )

    member = Membership.objects.get(organization=populated, role=Role.MEMBER).user
    body = client_for(member).get(URL, {"organization": populated.id}).json()
    assert body["invoices"]["paid_amount"] == "100.00"
