from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.customers.models import Customer
from apps.orders.models import Order, OrderStatus
from apps.orders.services import create_order, delete_order, update_order
from apps.organizations.models import Membership, Organization, Role

pytestmark = pytest.mark.django_db


def list_url():
    return reverse("orders:order-list")


def detail_url(pk):
    return reverse("orders:order-detail", args=[pk])


def make_user(django_user_model, email):
    return django_user_model.objects.create_user(email=email, password="pw12345!")


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def org_a(django_user_model):
    org = Organization.objects.create(name="Org A")
    for email, role in [
        ("owner-a@x.com", Role.OWNER),
        ("admin-a@x.com", Role.ADMIN),
        ("member-a@x.com", Role.MEMBER),
    ]:
        Membership.objects.create(
            organization=org, user=make_user(django_user_model, email), role=role
        )
    return org


@pytest.fixture
def org_b(django_user_model):
    org = Organization.objects.create(name="Org B")
    Membership.objects.create(
        organization=org, user=make_user(django_user_model, "owner-b@x.com"), role=Role.OWNER
    )
    return org


def member_of(org, role):
    return Membership.objects.get(organization=org, role=role).user


@pytest.fixture
def owner_a(org_a):
    return member_of(org_a, Role.OWNER)


@pytest.fixture
def admin_a(org_a):
    return member_of(org_a, Role.ADMIN)


@pytest.fixture
def plain_member_a(org_a):
    return member_of(org_a, Role.MEMBER)


@pytest.fixture
def owner_b(org_b):
    return member_of(org_b, Role.OWNER)


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


@pytest.fixture
def order_b(org_b, customer_b):
    return Order.objects.create(
        organization=org_b, customer=customer_b, total_amount=Decimal("10.00")
    )


def create_payload(org, customer, **overrides):
    payload = {
        "organization": org.id,
        "customer": customer.id,
        "total_amount": "50.00",
    }
    payload.update(overrides)
    return payload


# --- authentication -------------------------------------------------


def test_endpoints_require_authentication(order_a):
    anon = APIClient()
    assert anon.get(list_url()).status_code == 401
    assert anon.post(list_url(), {}, format="json").status_code == 401
    assert anon.get(detail_url(order_a.id)).status_code == 401
    assert anon.patch(detail_url(order_a.id), {}, format="json").status_code == 401
    assert anon.delete(detail_url(order_a.id)).status_code == 401


# --- list / retrieve / tenant isolation ---------------------------


def test_list_returns_only_orders_from_the_users_organizations(owner_a, order_a, order_b):
    resp = client_for(owner_a).get(list_url())

    assert resp.status_code == 200
    assert [row["id"] for row in resp.json()] == [order_a.id]


def test_list_is_empty_for_a_non_member(django_user_model, order_a):
    carol = make_user(django_user_model, "carol@x.com")
    resp = client_for(carol).get(list_url())
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_can_be_filtered_by_organization_and_status(owner_a, org_a, customer_a, order_a):
    create_order(
        organization=org_a,
        actor=owner_a,
        customer=customer_a,
        total_amount=Decimal("1.00"),
        status=OrderStatus.CONFIRMED,
    )
    by_status = client_for(owner_a).get(list_url(), {"status": "confirmed"})
    assert [row["status"] for row in by_status.json()] == ["confirmed"]

    by_org = client_for(owner_a).get(list_url(), {"organization": org_a.id})
    assert len(by_org.json()) == 2


def test_list_can_be_filtered_by_created_date_range(owner_a, org_a, customer_a):
    from datetime import datetime

    from django.utils import timezone

    old = Order.objects.create(organization=org_a, customer=customer_a, total_amount="1.00")
    new = Order.objects.create(organization=org_a, customer=customer_a, total_amount="2.00")
    Order.objects.filter(pk=old.pk).update(created_at=timezone.make_aware(datetime(2026, 1, 10)))
    Order.objects.filter(pk=new.pk).update(created_at=timezone.make_aware(datetime(2026, 6, 20)))

    resp = client_for(owner_a).get(list_url(), {"date_from": "2026-06-01"})
    assert [row["id"] for row in resp.json()] == [new.id]

    resp = client_for(owner_a).get(list_url(), {"date_to": "2026-03-01"})
    assert [row["id"] for row in resp.json()] == [old.id]

    resp = client_for(owner_a).get(list_url(), {"date_from": "2026-01-01", "date_to": "2026-12-31"})
    assert {row["id"] for row in resp.json()} == {old.id, new.id}

    # A malformed date is ignored, not a 500.
    resp = client_for(owner_a).get(list_url(), {"date_from": "not-a-date"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_retrieve_own_order(owner_a, order_a):
    resp = client_for(owner_a).get(detail_url(order_a.id))
    assert resp.status_code == 200
    assert resp.json()["id"] == order_a.id


def test_retrieve_cross_tenant_order_is_404(owner_a, order_b):
    assert client_for(owner_a).get(detail_url(order_b.id)).status_code == 404


def test_any_member_can_retrieve(plain_member_a, order_a):
    assert client_for(plain_member_a).get(detail_url(order_a.id)).status_code == 200


# --- create -------------------------------------------------------


def test_owner_can_create_an_order(owner_a, org_a, customer_a):
    resp = client_for(owner_a).post(
        list_url(),
        create_payload(org_a, customer_a, status=OrderStatus.PENDING, notes="rush"),
        format="json",
    )

    assert resp.status_code == 201
    order = Order.objects.get(id=resp.json()["id"])
    assert order.organization == org_a
    assert order.customer == customer_a
    assert order.status == OrderStatus.PENDING
    assert order.total_amount == Decimal("50.00")


def test_admin_can_create_an_order(admin_a, org_a, customer_a):
    resp = client_for(admin_a).post(list_url(), create_payload(org_a, customer_a), format="json")
    assert resp.status_code == 201


def test_plain_member_cannot_create_an_order(plain_member_a, org_a, customer_a):
    resp = client_for(plain_member_a).post(
        list_url(), create_payload(org_a, customer_a), format="json"
    )
    assert resp.status_code == 403
    assert Order.objects.count() == 0


def test_non_member_cannot_create_in_an_organization(django_user_model, org_a, customer_a):
    carol = make_user(django_user_model, "carol@x.com")
    resp = client_for(carol).post(list_url(), create_payload(org_a, customer_a), format="json")
    assert resp.status_code == 400
    assert "organization" in resp.json()
    assert Order.objects.count() == 0


def test_create_rejects_unknown_organization(owner_a, customer_a):
    resp = client_for(owner_a).post(
        list_url(),
        {"organization": 999_999, "customer": customer_a.id, "total_amount": "1.00"},
        format="json",
    )
    assert resp.status_code == 400
    assert "organization" in resp.json()


def test_create_rejects_customer_from_another_organization(owner_a, org_a, customer_b):
    resp = client_for(owner_a).post(list_url(), create_payload(org_a, customer_b), format="json")
    assert resp.status_code == 400
    assert "customer" in resp.json()


def test_create_rejects_invalid_status(owner_a, org_a, customer_a):
    resp = client_for(owner_a).post(
        list_url(), create_payload(org_a, customer_a, status="shipped"), format="json"
    )
    assert resp.status_code == 400
    assert "status" in resp.json()


def test_create_rejects_negative_amount(owner_a, org_a, customer_a):
    resp = client_for(owner_a).post(
        list_url(), create_payload(org_a, customer_a, total_amount="-5.00"), format="json"
    )
    assert resp.status_code == 400
    assert "total_amount" in resp.json()


# --- update -----------------------------------------------------


def test_owner_can_update_an_order(owner_a, order_a):
    resp = client_for(owner_a).patch(
        detail_url(order_a.id),
        {"status": OrderStatus.CONFIRMED, "total_amount": "99.00"},
        format="json",
    )
    assert resp.status_code == 200
    order_a.refresh_from_db()
    assert order_a.status == OrderStatus.CONFIRMED
    assert order_a.total_amount == Decimal("99.00")


def test_admin_can_update_an_order(admin_a, order_a):
    resp = client_for(admin_a).patch(
        detail_url(order_a.id), {"status": OrderStatus.PENDING}, format="json"
    )
    assert resp.status_code == 200


def test_plain_member_cannot_update_an_order(plain_member_a, order_a):
    resp = client_for(plain_member_a).patch(
        detail_url(order_a.id), {"status": OrderStatus.PENDING}, format="json"
    )
    assert resp.status_code == 403
    order_a.refresh_from_db()
    assert order_a.status == OrderStatus.DRAFT


def test_update_cross_tenant_order_is_404(owner_a, order_b):
    resp = client_for(owner_a).patch(
        detail_url(order_b.id), {"status": OrderStatus.PENDING}, format="json"
    )
    assert resp.status_code == 404
    order_b.refresh_from_db()
    assert order_b.status == OrderStatus.DRAFT


def test_update_cannot_change_the_organization(owner_a, order_a, org_b):
    resp = client_for(owner_a).patch(
        detail_url(order_a.id),
        {"organization": org_b.id, "status": OrderStatus.PENDING},
        format="json",
    )
    assert resp.status_code == 200
    order_a.refresh_from_db()
    assert order_a.organization_id != org_b.id
    assert order_a.status == OrderStatus.PENDING


def test_update_rejects_negative_amount(owner_a, order_a):
    resp = client_for(owner_a).patch(
        detail_url(order_a.id), {"total_amount": "-1.00"}, format="json"
    )
    assert resp.status_code == 400
    order_a.refresh_from_db()
    assert order_a.total_amount == Decimal("10.00")


# --- delete ---------------------------------------------------


def test_owner_can_delete_an_order(owner_a, order_a):
    resp = client_for(owner_a).delete(detail_url(order_a.id))
    assert resp.status_code == 204
    assert not Order.objects.filter(id=order_a.id).exists()


def test_admin_can_delete_an_order(admin_a, order_a):
    assert client_for(admin_a).delete(detail_url(order_a.id)).status_code == 204


def test_plain_member_cannot_delete_an_order(plain_member_a, order_a):
    resp = client_for(plain_member_a).delete(detail_url(order_a.id))
    assert resp.status_code == 403
    assert Order.objects.filter(id=order_a.id).exists()


def test_delete_cross_tenant_order_is_404(owner_a, order_b):
    resp = client_for(owner_a).delete(detail_url(order_b.id))
    assert resp.status_code == 404
    assert Order.objects.filter(id=order_b.id).exists()


# --- writes go through the service layer ---------------------


def test_create_uses_the_create_order_service(owner_a, org_a, customer_a):
    with patch("apps.orders.views.create_order", wraps=create_order) as spy:
        resp = client_for(owner_a).post(
            list_url(), create_payload(org_a, customer_a), format="json"
        )
    assert resp.status_code == 201
    spy.assert_called_once()
    assert spy.call_args.kwargs["organization"] == org_a
    assert spy.call_args.kwargs["actor"] == owner_a
    assert spy.call_args.kwargs["customer"] == customer_a


def test_update_uses_the_update_order_service(owner_a, order_a):
    with patch("apps.orders.views.update_order", wraps=update_order) as spy:
        resp = client_for(owner_a).patch(
            detail_url(order_a.id), {"status": OrderStatus.PENDING}, format="json"
        )
    assert resp.status_code == 200
    spy.assert_called_once()
    assert spy.call_args.kwargs["order"].id == order_a.id
    assert spy.call_args.kwargs["actor"] == owner_a


def test_delete_uses_the_delete_order_service(owner_a, order_a):
    with patch("apps.orders.views.delete_order", wraps=delete_order) as spy:
        resp = client_for(owner_a).delete(detail_url(order_a.id))
    assert resp.status_code == 204
    spy.assert_called_once()
    assert spy.call_args.kwargs["actor"] == owner_a
    assert not Order.objects.filter(id=order_a.id).exists()
