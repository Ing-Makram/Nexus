from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.customers.models import Customer
from apps.invoices.models import Invoice, InvoiceStatus
from apps.invoices.services import create_invoice, delete_invoice, update_invoice
from apps.organizations.models import Membership, Organization, Role

pytestmark = pytest.mark.django_db

ISSUE_DATE = date(2026, 1, 1)


def list_url():
    return reverse("invoices:invoice-list")


def detail_url(pk):
    return reverse("invoices:invoice-detail", args=[pk])


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
def customer_a(org_a):
    return Customer.objects.create(organization=org_a, name="Acme")


@pytest.fixture
def customer_b(org_b):
    return Customer.objects.create(organization=org_b, name="Beta")


def new_invoice(org, customer, actor, **overrides):
    return create_invoice(
        organization=org,
        actor=actor,
        customer=customer,
        issue_date=ISSUE_DATE,
        total_amount=Decimal("10.00"),
        **overrides,
    )


@pytest.fixture
def invoice_a(org_a, customer_a, owner_a):
    return new_invoice(org_a, customer_a, owner_a)


@pytest.fixture
def invoice_b(org_b, customer_b):
    return create_invoice(
        organization=org_b,
        actor=member_of(org_b, Role.OWNER),
        customer=customer_b,
        issue_date=ISSUE_DATE,
        total_amount=Decimal("10.00"),
    )


def create_payload(org, customer, **overrides):
    payload = {
        "organization": org.id,
        "customer": customer.id,
        "invoice_number": "INV-900",
        "issue_date": "2026-01-01",
        "total_amount": "50.00",
    }
    payload.update(overrides)
    return payload


# --- authentication ---------------------------------------------


def test_endpoints_require_authentication(invoice_a):
    anon = APIClient()
    assert anon.get(list_url()).status_code == 401
    assert anon.post(list_url(), {}, format="json").status_code == 401
    assert anon.get(detail_url(invoice_a.id)).status_code == 401
    assert anon.patch(detail_url(invoice_a.id), {}, format="json").status_code == 401
    assert anon.delete(detail_url(invoice_a.id)).status_code == 401


# --- list / retrieve / tenant isolation ---------------------


def test_list_returns_only_invoices_from_the_users_organizations(owner_a, invoice_a, invoice_b):
    resp = client_for(owner_a).get(list_url())
    assert resp.status_code == 200
    assert [row["id"] for row in resp.json()] == [invoice_a.id]


def test_list_is_empty_for_a_non_member(django_user_model, invoice_a):
    carol = make_user(django_user_model, "carol@x.com")
    resp = client_for(carol).get(list_url())
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_can_be_filtered_by_organization_and_status(owner_a, org_a, customer_a, invoice_a):
    new_invoice(org_a, customer_a, owner_a, status=InvoiceStatus.PAID)

    all_resp = client_for(owner_a).get(list_url())
    assert len(all_resp.json()) == 2

    org_resp = client_for(owner_a).get(list_url(), {"organization": org_a.id})
    assert len(org_resp.json()) == 2

    status_resp = client_for(owner_a).get(list_url(), {"status": "paid"})
    assert [row["status"] for row in status_resp.json()] == ["paid"]


def test_list_can_be_filtered_by_issue_date_range(owner_a, org_a, customer_a):
    def at(day):
        return create_invoice(
            organization=org_a,
            actor=owner_a,
            customer=customer_a,
            issue_date=day,
            total_amount=Decimal("10.00"),
        )

    jan = at("2026-01-10")
    jun = at("2026-06-20")

    resp = client_for(owner_a).get(list_url(), {"date_from": "2026-06-01"})
    assert [row["id"] for row in resp.json()] == [jun.id]

    resp = client_for(owner_a).get(list_url(), {"date_to": "2026-03-01"})
    assert [row["id"] for row in resp.json()] == [jan.id]

    resp = client_for(owner_a).get(list_url(), {"date_from": "bad", "date_to": ""})
    assert resp.status_code == 200
    assert {row["id"] for row in resp.json()} == {jan.id, jun.id}


def test_retrieve_own_invoice(plain_member_a, invoice_a):
    resp = client_for(plain_member_a).get(detail_url(invoice_a.id))
    assert resp.status_code == 200
    assert resp.json()["id"] == invoice_a.id


def test_retrieve_cross_tenant_invoice_is_404(owner_a, invoice_b):
    assert client_for(owner_a).get(detail_url(invoice_b.id)).status_code == 404


# --- create -------------------------------------------------


def test_owner_can_create_an_invoice(owner_a, org_a, customer_a):
    resp = client_for(owner_a).post(
        list_url(),
        create_payload(org_a, customer_a, status=InvoiceStatus.SENT, notes="net 30"),
        format="json",
    )
    assert resp.status_code == 201
    invoice = Invoice.objects.get(id=resp.json()["id"])
    assert invoice.organization == org_a
    assert invoice.customer == customer_a
    assert invoice.status == InvoiceStatus.SENT
    assert invoice.created_by == owner_a


def test_admin_can_create_an_invoice(admin_a, org_a, customer_a):
    resp = client_for(admin_a).post(list_url(), create_payload(org_a, customer_a), format="json")
    assert resp.status_code == 201


def test_create_auto_numbers_when_number_omitted(owner_a, org_a, customer_a):
    body = create_payload(org_a, customer_a)
    del body["invoice_number"]
    resp = client_for(owner_a).post(list_url(), body, format="json")
    assert resp.status_code == 201
    assert resp.json()["invoice_number"] == "INV-0001"


def test_plain_member_cannot_create_an_invoice(plain_member_a, org_a, customer_a):
    resp = client_for(plain_member_a).post(
        list_url(), create_payload(org_a, customer_a), format="json"
    )
    assert resp.status_code == 403
    assert Invoice.objects.count() == 0


def test_non_member_cannot_create_in_an_organization(django_user_model, org_a, customer_a):
    carol = make_user(django_user_model, "carol@x.com")
    resp = client_for(carol).post(list_url(), create_payload(org_a, customer_a), format="json")
    assert resp.status_code == 400
    assert "organization" in resp.json()


def test_create_rejects_customer_from_another_organization(owner_a, org_a, customer_b):
    resp = client_for(owner_a).post(list_url(), create_payload(org_a, customer_b), format="json")
    assert resp.status_code == 400
    assert "customer" in resp.json()


def test_create_rejects_duplicate_number(owner_a, org_a, customer_a, invoice_a):
    resp = client_for(owner_a).post(
        list_url(),
        create_payload(org_a, customer_a, invoice_number=invoice_a.invoice_number),
        format="json",
    )
    assert resp.status_code == 400
    assert "invoice_number" in resp.json()


def test_create_rejects_invalid_status(owner_a, org_a, customer_a):
    resp = client_for(owner_a).post(
        list_url(), create_payload(org_a, customer_a, status="refunded"), format="json"
    )
    assert resp.status_code == 400
    assert "status" in resp.json()


def test_create_rejects_negative_amount(owner_a, org_a, customer_a):
    resp = client_for(owner_a).post(
        list_url(), create_payload(org_a, customer_a, total_amount="-5.00"), format="json"
    )
    assert resp.status_code == 400
    assert "total_amount" in resp.json()


def test_create_rejects_due_date_before_issue_date(owner_a, org_a, customer_a):
    resp = client_for(owner_a).post(
        list_url(),
        create_payload(org_a, customer_a, issue_date="2026-02-01", due_date="2026-01-01"),
        format="json",
    )
    assert resp.status_code == 400
    assert "due_date" in resp.json()


# --- update -----------------------------------------------


def test_owner_can_update_an_invoice(owner_a, invoice_a):
    resp = client_for(owner_a).patch(
        detail_url(invoice_a.id),
        {"status": InvoiceStatus.PAID, "total_amount": "12.00"},
        format="json",
    )
    assert resp.status_code == 200
    invoice_a.refresh_from_db()
    assert invoice_a.status == InvoiceStatus.PAID
    assert invoice_a.total_amount == Decimal("12.00")


def test_plain_member_cannot_update_an_invoice(plain_member_a, invoice_a):
    resp = client_for(plain_member_a).patch(
        detail_url(invoice_a.id), {"status": InvoiceStatus.SENT}, format="json"
    )
    assert resp.status_code == 403


def test_update_cross_tenant_invoice_is_404(owner_a, invoice_b):
    resp = client_for(owner_a).patch(
        detail_url(invoice_b.id), {"status": InvoiceStatus.SENT}, format="json"
    )
    assert resp.status_code == 404


def test_update_cannot_change_the_organization(owner_a, invoice_a, org_b):
    resp = client_for(owner_a).patch(
        detail_url(invoice_a.id),
        {"organization": org_b.id, "status": InvoiceStatus.SENT},
        format="json",
    )
    assert resp.status_code == 200
    invoice_a.refresh_from_db()
    assert invoice_a.organization_id != org_b.id
    assert invoice_a.status == InvoiceStatus.SENT


# --- delete ---------------------------------------------


def test_owner_can_delete_an_invoice(owner_a, invoice_a):
    resp = client_for(owner_a).delete(detail_url(invoice_a.id))
    assert resp.status_code == 204
    assert not Invoice.objects.filter(id=invoice_a.id).exists()


def test_plain_member_cannot_delete_an_invoice(plain_member_a, invoice_a):
    resp = client_for(plain_member_a).delete(detail_url(invoice_a.id))
    assert resp.status_code == 403
    assert Invoice.objects.filter(id=invoice_a.id).exists()


def test_delete_cross_tenant_invoice_is_404(owner_a, invoice_b):
    resp = client_for(owner_a).delete(detail_url(invoice_b.id))
    assert resp.status_code == 404
    assert Invoice.objects.filter(id=invoice_b.id).exists()


# --- writes go through the service layer ------------------


def test_create_uses_the_create_invoice_service(owner_a, org_a, customer_a):
    with patch("apps.invoices.views.create_invoice", wraps=create_invoice) as spy:
        resp = client_for(owner_a).post(
            list_url(), create_payload(org_a, customer_a), format="json"
        )
    assert resp.status_code == 201
    spy.assert_called_once()
    assert spy.call_args.kwargs["organization"] == org_a
    assert spy.call_args.kwargs["actor"] == owner_a


def test_update_uses_the_update_invoice_service(owner_a, invoice_a):
    with patch("apps.invoices.views.update_invoice", wraps=update_invoice) as spy:
        resp = client_for(owner_a).patch(
            detail_url(invoice_a.id), {"status": InvoiceStatus.SENT}, format="json"
        )
    assert resp.status_code == 200
    spy.assert_called_once()
    assert spy.call_args.kwargs["actor"] == owner_a


def test_delete_uses_the_delete_invoice_service(owner_a, invoice_a):
    with patch("apps.invoices.views.delete_invoice", wraps=delete_invoice) as spy:
        resp = client_for(owner_a).delete(detail_url(invoice_a.id))
    assert resp.status_code == 204
    spy.assert_called_once()
    assert spy.call_args.kwargs["actor"] == owner_a
