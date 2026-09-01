import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.organizations.models import Membership, Role
from apps.organizations.services import create_organization

pytestmark = pytest.mark.django_db


def members_url(org_id):
    return reverse("organizations:member-list", args=[org_id])


def member_url(org_id, user_id):
    return reverse("organizations:member-detail", args=[org_id, user_id])


def make_user(django_user_model, email):
    return django_user_model.objects.create_user(email=email, password="pw12345!")


@pytest.fixture
def owner(django_user_model):
    return make_user(django_user_model, "owner@example.com")


@pytest.fixture
def admin(django_user_model):
    return make_user(django_user_model, "admin@example.com")


@pytest.fixture
def member(django_user_model):
    return make_user(django_user_model, "member@example.com")


@pytest.fixture
def outsider(django_user_model):
    return make_user(django_user_model, "outsider@example.com")


@pytest.fixture
def org(owner, admin, member):
    organization = create_organization(name="Acme", user=owner)
    Membership.objects.create(organization=organization, user=admin, role=Role.ADMIN)
    Membership.objects.create(organization=organization, user=member, role=Role.MEMBER)
    return organization


def client_for(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


# --- authentication -------------------------------------------------------


def test_members_endpoint_requires_authentication(org):
    assert APIClient().get(members_url(org.id)).status_code == 401


# --- listing -------------------------------------------------------------


def test_member_can_list_members(org, member):
    resp = client_for(member).get(members_url(org.id))

    assert resp.status_code == 200
    by_email = {row["user"]["email"]: row["role"] for row in resp.json()}
    assert by_email == {
        "owner@example.com": Role.OWNER,
        "admin@example.com": Role.ADMIN,
        "member@example.com": Role.MEMBER,
    }
    assert "password" not in resp.json()[0]["user"]


def test_outsider_cannot_list_members(org, outsider):
    assert client_for(outsider).get(members_url(org.id)).status_code == 404


def test_member_list_is_scoped_to_the_organization(django_user_model, org, owner):
    other_owner = make_user(django_user_model, "other@example.com")
    other = create_organization(name="Other", user=other_owner)

    resp = client_for(owner).get(members_url(org.id))
    emails = {row["user"]["email"] for row in resp.json()}
    assert "other@example.com" not in emails

    # ...and the owner of `org` cannot even see `other`'s members.
    assert client_for(owner).get(members_url(other.id)).status_code == 404


# --- adding members ----------------------------------------------------


def test_admin_can_add_an_existing_user_as_member(django_user_model, org, admin):
    newcomer = make_user(django_user_model, "new@example.com")

    resp = client_for(admin).post(
        members_url(org.id),
        {"email": "new@example.com", "role": "member"},
        format="json",
    )

    assert resp.status_code == 201
    assert resp.json()["user"]["email"] == "new@example.com"
    assert Membership.objects.get(organization=org, user=newcomer).role == Role.MEMBER


def test_owner_can_add_a_user_as_admin(django_user_model, org, owner):
    make_user(django_user_model, "new@example.com")

    resp = client_for(owner).post(
        members_url(org.id),
        {"email": "NEW@example.com", "role": "admin"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == Role.ADMIN


def test_cannot_add_the_same_user_twice(org, admin, member):
    resp = client_for(admin).post(
        members_url(org.id),
        {"email": member.email, "role": "member"},
        format="json",
    )
    assert resp.status_code == 400
    assert "email" in resp.json()
    assert Membership.objects.filter(organization=org, user=member).count() == 1


def test_cannot_add_unknown_email(org, admin):
    resp = client_for(admin).post(
        members_url(org.id),
        {"email": "ghost@example.com", "role": "member"},
        format="json",
    )
    assert resp.status_code == 400
    assert "email" in resp.json()


def test_cannot_add_member_with_owner_role(django_user_model, org, owner):
    make_user(django_user_model, "new@example.com")
    resp = client_for(owner).post(
        members_url(org.id),
        {"email": "new@example.com", "role": "owner"},
        format="json",
    )
    assert resp.status_code == 400
    assert "role" in resp.json()


def test_plain_member_cannot_add_members(django_user_model, org, member):
    make_user(django_user_model, "new@example.com")
    resp = client_for(member).post(
        members_url(org.id),
        {"email": "new@example.com", "role": "member"},
        format="json",
    )
    assert resp.status_code == 403


def test_outsider_cannot_add_members(django_user_model, org, outsider):
    make_user(django_user_model, "new@example.com")
    resp = client_for(outsider).post(
        members_url(org.id),
        {"email": "new@example.com", "role": "member"},
        format="json",
    )
    assert resp.status_code == 404


# --- changing roles --------------------------------------------------


def test_admin_can_promote_a_member_to_admin(org, admin, member):
    resp = client_for(admin).patch(member_url(org.id, member.id), {"role": "admin"}, format="json")
    assert resp.status_code == 200
    assert Membership.objects.get(organization=org, user=member).role == Role.ADMIN


def test_admin_cannot_change_another_admins_role(django_user_model, org, admin):
    admin2 = make_user(django_user_model, "admin2@example.com")
    Membership.objects.create(organization=org, user=admin2, role=Role.ADMIN)

    resp = client_for(admin).patch(member_url(org.id, admin2.id), {"role": "member"}, format="json")
    assert resp.status_code == 403
    assert Membership.objects.get(organization=org, user=admin2).role == Role.ADMIN


def test_owner_can_change_an_admins_role(org, owner, admin):
    resp = client_for(owner).patch(member_url(org.id, admin.id), {"role": "member"}, format="json")
    assert resp.status_code == 200
    assert Membership.objects.get(organization=org, user=admin).role == Role.MEMBER


def test_owner_role_cannot_be_changed(org, owner, admin):
    assert (
        client_for(admin)
        .patch(member_url(org.id, owner.id), {"role": "member"}, format="json")
        .status_code
        == 403
    )
    assert (
        client_for(owner)
        .patch(member_url(org.id, owner.id), {"role": "member"}, format="json")
        .status_code
        == 403
    )
    assert Membership.objects.get(organization=org, user=owner).role == Role.OWNER


def test_plain_member_cannot_change_roles(org, member, admin):
    resp = client_for(member).patch(member_url(org.id, admin.id), {"role": "member"}, format="json")
    assert resp.status_code == 403


def test_change_role_rejects_owner_value(org, owner, member):
    resp = client_for(owner).patch(member_url(org.id, member.id), {"role": "owner"}, format="json")
    assert resp.status_code == 400


def test_change_role_for_non_member_is_404(django_user_model, org, owner):
    stranger = make_user(django_user_model, "stranger@example.com")
    resp = client_for(owner).patch(
        member_url(org.id, stranger.id), {"role": "member"}, format="json"
    )
    assert resp.status_code == 404


def test_cross_tenant_role_change_is_404(django_user_model, org, member):
    other_owner = make_user(django_user_model, "other@example.com")
    other = create_organization(name="Other", user=other_owner)

    resp = client_for(member).patch(
        member_url(other.id, other_owner.id), {"role": "member"}, format="json"
    )
    assert resp.status_code == 404


# --- removing members -----------------------------------------------


def test_admin_can_remove_a_member(org, admin, member):
    resp = client_for(admin).delete(member_url(org.id, member.id))
    assert resp.status_code == 204
    assert not Membership.objects.filter(organization=org, user=member).exists()


def test_admin_cannot_remove_another_admin(django_user_model, org, admin):
    admin2 = make_user(django_user_model, "admin2@example.com")
    Membership.objects.create(organization=org, user=admin2, role=Role.ADMIN)

    resp = client_for(admin).delete(member_url(org.id, admin2.id))
    assert resp.status_code == 403
    assert Membership.objects.filter(organization=org, user=admin2).exists()


def test_owner_can_remove_an_admin(org, owner, admin):
    resp = client_for(owner).delete(member_url(org.id, admin.id))
    assert resp.status_code == 204
    assert not Membership.objects.filter(organization=org, user=admin).exists()


def test_owner_cannot_be_removed(org, owner, admin):
    assert client_for(admin).delete(member_url(org.id, owner.id)).status_code == 403
    assert client_for(owner).delete(member_url(org.id, owner.id)).status_code == 403
    assert Membership.objects.filter(organization=org, user=owner).exists()


def test_plain_member_cannot_remove_members(org, member, admin):
    resp = client_for(member).delete(member_url(org.id, admin.id))
    assert resp.status_code == 403


def test_cross_tenant_removal_is_404(django_user_model, org, member):
    other_owner = make_user(django_user_model, "other@example.com")
    other = create_organization(name="Other", user=other_owner)

    resp = client_for(member).delete(member_url(other.id, other_owner.id))
    assert resp.status_code == 404
    assert Membership.objects.filter(organization=other, user=other_owner).exists()
