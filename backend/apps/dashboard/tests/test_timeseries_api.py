from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.customers.models import Customer
from apps.invoices.models import Invoice, InvoiceStatus
from apps.orders.models import Order, OrderStatus
from apps.organizations.models import Membership, Organization, Role

pytestmark = pytest.mark.django_db

URL = reverse("dashboard:dashboard-timeseries")


def make_user(django_user_model, email):
    return django_user_model.objects.create_user(email=email, password="pw12345!")


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def set_created_at(instance, when):
    """`created_at` is auto_now_add, so bypass it with a direct UPDATE."""
    type(instance).objects.filter(pk=instance.pk).update(created_at=when)


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


def test_days_defaults_to_30_and_rejects_unsupported_windows(member, org):
    body = client_for(member).get(URL, {"organization": org.id}).json()
    assert body["days"] == 30
    assert len(body["points"]) == 30

    assert client_for(member).get(URL, {"organization": org.id, "days": "90"}).json()["days"] == 90
    assert client_for(member).get(URL, {"organization": org.id, "days": "7"}).status_code == 400
    assert client_for(member).get(URL, {"organization": org.id, "days": "x"}).status_code == 400


def test_buckets_are_continuous_and_zero_filled(member, org):
    body = client_for(member).get(URL, {"organization": org.id, "days": "90"}).json()
    today = timezone.localdate()

    assert body["end"] == today.isoformat()
    assert body["start"] == (today - timedelta(days=89)).isoformat()
    dates = [p["date"] for p in body["points"]]
    assert dates == sorted(dates)
    assert dates[0] == body["start"]
    assert dates[-1] == body["end"]
    assert all(
        p
        == {
            "date": p["date"],
            "orders": 0,
            "invoices": 0,
            "customers": 0,
            "invoiced_amount": "0.00",
            "paid_amount": "0.00",
        }
        for p in body["points"]
    )


def test_counts_and_amounts_land_on_the_right_day(member, org):
    today = timezone.localdate()
    customer = Customer.objects.create(organization=org, name="C")
    set_created_at(customer, timezone.now() - timedelta(days=5))

    recent = Order.objects.create(
        organization=org, customer=customer, status=OrderStatus.DRAFT, total_amount="10"
    )
    old = Order.objects.create(
        organization=org, customer=customer, status=OrderStatus.DRAFT, total_amount="10"
    )
    set_created_at(recent, timezone.now() - timedelta(days=2))
    set_created_at(old, timezone.now() - timedelta(days=200))

    Invoice.objects.create(
        organization=org,
        customer=customer,
        invoice_number="INV-1",
        status=InvoiceStatus.PAID,
        issue_date=today - timedelta(days=3),
        total_amount=Decimal("100.00"),
    )
    Invoice.objects.create(
        organization=org,
        customer=customer,
        invoice_number="INV-2",
        status=InvoiceStatus.SENT,
        issue_date=today - timedelta(days=3),
        total_amount=Decimal("40.00"),
    )
    Invoice.objects.create(
        organization=org,
        customer=customer,
        invoice_number="INV-3",
        status=InvoiceStatus.VOID,
        issue_date=today - timedelta(days=3),
        total_amount=Decimal("999.00"),
    )

    points = {
        p["date"]: p for p in client_for(member).get(URL, {"organization": org.id}).json()["points"]
    }

    assert points[(today - timedelta(days=2)).isoformat()]["orders"] == 1
    assert points[(today - timedelta(days=5)).isoformat()]["customers"] == 1

    day3 = points[(today - timedelta(days=3)).isoformat()]
    assert day3["invoices"] == 3
    assert day3["invoiced_amount"] == "140.00"  # 100 + 40, void excluded
    assert day3["paid_amount"] == "100.00"

    # The 200-day-old order falls outside the 30-day window entirely.
    assert sum(p["orders"] for p in points.values()) == 1


def test_does_not_leak_other_organizations_activity(member, org, django_user_model):
    today = timezone.localdate()
    other = Organization.objects.create(name="Other")
    other_user = make_user(django_user_model, "o@other.test")
    Membership.objects.create(organization=other, user=other_user, role=Role.OWNER)
    oc = Customer.objects.create(organization=other, name="Other C")
    Invoice.objects.create(
        organization=other,
        customer=oc,
        invoice_number="O-1",
        status=InvoiceStatus.PAID,
        issue_date=today,
        total_amount=Decimal("5000.00"),
    )

    body = client_for(member).get(URL, {"organization": org.id}).json()
    assert all(p["paid_amount"] == "0.00" for p in body["points"])
