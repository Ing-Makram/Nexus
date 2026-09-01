import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.customers.models import Customer
from apps.organizations.models import Membership, Role
from apps.organizations.services import create_organization

pytestmark = pytest.mark.django_db


def list_url():
    return reverse("customers:customer-list")


def detail_url(pk):
    return reverse("customers:customer-detail", args=[pk])


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
    return create_organization(name="Org A", user=alice)


@pytest.fixture
def org_b(bob):
    return create_organization(name="Org B", user=bob)


@pytest.fixture
def api(alice):
    client = APIClient()
    client.force_authenticate(alice)
    return client


CUSTOMER_FIELDS = {
    "id",
    "organization",
    "name",
    "email",
    "phone",
    "company",
    "address",
    "created_by",
    "created_at",
    "updated_at",
}


# --- authentication -----------------------------------------------------


def test_authentication_is_required(org_a):
    anon = APIClient()
    assert anon.get(list_url()).status_code == 401
    assert anon.post(list_url(), {"organization": org_a.id, "name": "X"}).status_code == 401


# --- create ----------------------------------------------------------


def test_create_customer(api, alice, org_a):
    resp = api.post(
        list_url(),
        {"organization": org_a.id, "name": "  Jane Doe  ", "email": "jane@example.com"},
        format="json",
    )

    assert resp.status_code == 201
    body = resp.json()
    assert set(body) == CUSTOMER_FIELDS
    assert body["name"] == "Jane Doe"  # trimmed
    assert body["organization"] == org_a.id
    assert body["created_by"] == alice.email

    customer = Customer.objects.get(id=body["id"])
    assert customer.organization == org_a
    assert customer.email == "jane@example.com"
    assert customer.created_by == alice


def test_create_stores_all_optional_fields(api, org_a):
    resp = api.post(
        list_url(),
        {
            "organization": org_a.id,
            "name": "Jane",
            "email": "jane@example.com",
            "phone": "+1 555 0100",
            "company": "Doe LLC",
            "address": "1 Main St",
        },
        format="json",
    )
    assert resp.status_code == 201
    customer = Customer.objects.get(id=resp.json()["id"])
    assert (customer.phone, customer.company, customer.address) == (
        "+1 555 0100",
        "Doe LLC",
        "1 Main St",
    )


def test_create_requires_membership_in_the_target_organization(api, org_b):
    resp = api.post(
        list_url(),
        {"organization": org_b.id, "name": "Jane"},
        format="json",
    )
    assert resp.status_code == 400
    assert "organization" in resp.json()
    assert not Customer.objects.filter(name="Jane").exists()


def test_create_rejects_blank_name(api, org_a):
    resp = api.post(
        list_url(),
        {"organization": org_a.id, "name": "   "},
        format="json",
    )
    assert resp.status_code == 400
    assert "name" in resp.json()


def test_create_requires_name(api, org_a):
    resp = api.post(list_url(), {"organization": org_a.id}, format="json")
    assert resp.status_code == 400
    assert "name" in resp.json()


def test_create_validates_email(api, org_a):
    resp = api.post(
        list_url(),
        {"organization": org_a.id, "name": "Jane", "email": "not-an-email"},
        format="json",
    )
    assert resp.status_code == 400
    assert "email" in resp.json()


# --- list / tenant scope --------------------------------------------


def test_list_returns_only_customers_from_the_users_organizations(
    django_user_model, api, alice, org_a
):
    mine = Customer.objects.create(organization=org_a, name="Mine")

    bob = make_user(django_user_model, "bob2@example.com")
    org_b = create_organization(name="Org B", user=bob)
    Customer.objects.create(organization=org_b, name="Theirs")

    resp = api.get(list_url())
    assert resp.status_code == 200
    ids = [row["id"] for row in resp.json()]
    assert ids == [mine.id]


def test_list_spans_all_of_the_users_organizations(django_user_model, api, alice, org_a):
    second = create_organization(name="Second", user=make_user(django_user_model, "x@example.com"))
    Membership.objects.create(organization=second, user=alice, role=Role.MEMBER)

    a = Customer.objects.create(organization=org_a, name="A")
    b = Customer.objects.create(organization=second, name="B")

    resp = api.get(list_url())
    assert {row["id"] for row in resp.json()} == {a.id, b.id}

    scoped = api.get(list_url(), {"organization": org_a.id})
    assert [row["id"] for row in scoped.json()] == [a.id]


# --- retrieve -----------------------------------------------------


def test_retrieve_own_customer(api, org_a):
    customer = Customer.objects.create(organization=org_a, name="Jane")
    resp = api.get(detail_url(customer.id))
    assert resp.status_code == 200
    assert resp.json()["id"] == customer.id


def test_retrieve_cross_tenant_customer_is_404(api, django_user_model):
    bob = make_user(django_user_model, "bob3@example.com")
    org_b = create_organization(name="Org B", user=bob)
    other = Customer.objects.create(organization=org_b, name="Theirs")

    assert api.get(detail_url(other.id)).status_code == 404


# --- update -----------------------------------------------------


def test_update_own_customer(api, org_a):
    customer = Customer.objects.create(organization=org_a, name="Jane")
    resp = api.patch(detail_url(customer.id), {"name": "  Jane Roe  "}, format="json")
    assert resp.status_code == 200
    customer.refresh_from_db()
    assert customer.name == "Jane Roe"


def test_update_rejects_blank_name(api, org_a):
    customer = Customer.objects.create(organization=org_a, name="Jane")
    resp = api.patch(detail_url(customer.id), {"name": "  "}, format="json")
    assert resp.status_code == 400
    customer.refresh_from_db()
    assert customer.name == "Jane"


def test_organization_cannot_be_changed_through_patch(api, alice, org_a, django_user_model):
    other = create_organization(name="Other", user=make_user(django_user_model, "y@example.com"))
    Membership.objects.create(organization=other, user=alice, role=Role.MEMBER)

    customer = Customer.objects.create(organization=org_a, name="Jane")
    resp = api.patch(
        detail_url(customer.id),
        {"organization": other.id, "name": "Jane"},
        format="json",
    )

    assert resp.status_code == 200
    customer.refresh_from_db()
    assert customer.organization == org_a  # unchanged
    assert resp.json()["organization"] == org_a.id


def test_update_cross_tenant_customer_is_404(api, django_user_model):
    bob = make_user(django_user_model, "bob4@example.com")
    org_b = create_organization(name="Org B", user=bob)
    other = Customer.objects.create(organization=org_b, name="Theirs")

    resp = api.patch(detail_url(other.id), {"name": "Hijacked"}, format="json")
    assert resp.status_code == 404
    other.refresh_from_db()
    assert other.name == "Theirs"


# --- delete -----------------------------------------------------


def test_delete_own_customer(api, org_a):
    customer = Customer.objects.create(organization=org_a, name="Jane")
    resp = api.delete(detail_url(customer.id))
    assert resp.status_code == 204
    assert not Customer.objects.filter(id=customer.id).exists()


def test_delete_cross_tenant_customer_is_404(api, django_user_model):
    bob = make_user(django_user_model, "bob5@example.com")
    org_b = create_organization(name="Org B", user=bob)
    other = Customer.objects.create(organization=org_b, name="Theirs")

    resp = api.delete(detail_url(other.id))
    assert resp.status_code == 404
    assert Customer.objects.filter(id=other.id).exists()
