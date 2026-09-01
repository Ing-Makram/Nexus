import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.organizations.models import Membership, Organization, Role
from apps.organizations.services import create_organization

pytestmark = pytest.mark.django_db


def list_url():
    return reverse("organizations:organization-list")


def detail_url(pk):
    return reverse("organizations:organization-detail", args=[pk])


@pytest.fixture
def alice(django_user_model):
    return django_user_model.objects.create_user(email="alice@example.com", password="pw12345!")


@pytest.fixture
def bob(django_user_model):
    return django_user_model.objects.create_user(email="bob@example.com", password="pw12345!")


@pytest.fixture
def api(alice):
    client = APIClient()
    client.force_authenticate(alice)
    return client


def add_member(org, user, role):
    return Membership.objects.create(organization=org, user=user, role=role)


# --- authentication ---------------------------------------------------------


def test_endpoints_require_authentication():
    anon = APIClient()
    assert anon.get(list_url()).status_code == 401
    assert anon.post(list_url(), {"name": "Acme"}, format="json").status_code == 401


# --- creation --------------------------------------------------------------


def test_create_organization_makes_requester_the_owner(api, alice):
    resp = api.post(list_url(), {"name": "  Acme Inc  "}, format="json")

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Acme Inc"  # trimmed
    assert body["role"] == Role.OWNER

    org = Organization.objects.get(id=body["id"])
    assert org.created_by == alice
    assert Membership.objects.get(organization=org, user=alice).role == Role.OWNER


@pytest.mark.parametrize("name", ["", "   ", "A"])
def test_create_organization_rejects_invalid_names(api, name):
    resp = api.post(list_url(), {"name": name}, format="json")
    assert resp.status_code == 400
    assert "name" in resp.json()


def test_create_organization_ignores_client_supplied_role(api, alice):
    resp = api.post(list_url(), {"name": "Acme", "role": Role.MEMBER}, format="json")
    assert resp.status_code == 201
    assert resp.json()["role"] == Role.OWNER


# --- listing / tenant scope ----------------------------------------------


def test_list_returns_only_organizations_the_user_belongs_to(api, alice, bob):
    mine = create_organization(name="Mine", user=alice)
    create_organization(name="Theirs", user=bob)

    resp = api.get(list_url())

    assert resp.status_code == 200
    names = [row["name"] for row in resp.json()]
    assert names == ["Mine"]
    assert resp.json()[0]["id"] == mine.id


def test_member_of_multiple_orgs_sees_all_of_them(api, alice, bob):
    owned = create_organization(name="Owned", user=alice)
    joined = create_organization(name="Joined", user=bob)
    add_member(joined, alice, Role.MEMBER)

    resp = api.get(list_url())

    assert {row["name"]: row["role"] for row in resp.json()} == {
        "Joined": Role.MEMBER,
        "Owned": Role.OWNER,
    }
    assert owned.id in {row["id"] for row in resp.json()}


# --- retrieve ------------------------------------------------------------


def test_retrieve_own_organization(api, alice):
    org = create_organization(name="Acme", user=alice)
    resp = api.get(detail_url(org.id))
    assert resp.status_code == 200
    assert resp.json()["id"] == org.id


def test_retrieve_other_tenants_organization_is_404(api, bob):
    other = create_organization(name="Theirs", user=bob)
    resp = api.get(detail_url(other.id))
    assert resp.status_code == 404


# --- update ------------------------------------------------------------


def test_owner_can_update_organization(api, alice):
    org = create_organization(name="Acme", user=alice)
    resp = api.patch(detail_url(org.id), {"name": "Acme Renamed"}, format="json")
    assert resp.status_code == 200
    org.refresh_from_db()
    assert org.name == "Acme Renamed"


def test_admin_can_update_organization(api, alice, bob):
    org = create_organization(name="Acme", user=bob)
    add_member(org, alice, Role.ADMIN)
    resp = api.patch(detail_url(org.id), {"name": "Renamed"}, format="json")
    assert resp.status_code == 200
    org.refresh_from_db()
    assert org.name == "Renamed"


def test_member_cannot_update_organization(api, alice, bob):
    org = create_organization(name="Acme", user=bob)
    add_member(org, alice, Role.MEMBER)
    resp = api.patch(detail_url(org.id), {"name": "Hijacked"}, format="json")
    assert resp.status_code == 403
    org.refresh_from_db()
    assert org.name == "Acme"


def test_cannot_update_other_tenants_organization(api, bob):
    other = create_organization(name="Theirs", user=bob)
    resp = api.patch(detail_url(other.id), {"name": "Hijacked"}, format="json")
    assert resp.status_code == 404
    other.refresh_from_db()
    assert other.name == "Theirs"


def test_role_cannot_be_changed_through_update(api, alice):
    org = create_organization(name="Acme", user=alice)
    resp = api.patch(detail_url(org.id), {"role": Role.MEMBER}, format="json")
    assert resp.status_code == 200
    assert Membership.objects.get(organization=org, user=alice).role == Role.OWNER


# --- delete ------------------------------------------------------------


def test_owner_can_delete_organization(api, alice):
    org = create_organization(name="Acme", user=alice)
    resp = api.delete(detail_url(org.id))
    assert resp.status_code == 204
    assert not Organization.objects.filter(id=org.id).exists()


def test_admin_cannot_delete_organization(api, alice, bob):
    org = create_organization(name="Acme", user=bob)
    add_member(org, alice, Role.ADMIN)
    resp = api.delete(detail_url(org.id))
    assert resp.status_code == 403
    assert Organization.objects.filter(id=org.id).exists()


def test_member_cannot_delete_organization(api, alice, bob):
    org = create_organization(name="Acme", user=bob)
    add_member(org, alice, Role.MEMBER)
    resp = api.delete(detail_url(org.id))
    assert resp.status_code == 403
    assert Organization.objects.filter(id=org.id).exists()


def test_cannot_delete_other_tenants_organization(api, bob):
    other = create_organization(name="Theirs", user=bob)
    resp = api.delete(detail_url(other.id))
    assert resp.status_code == 404
    assert Organization.objects.filter(id=other.id).exists()
