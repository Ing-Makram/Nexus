import pytest

from apps.organizations.models import Membership, Organization, Role
from apps.organizations.services import create_organization

pytestmark = pytest.mark.django_db


def test_create_organization_makes_the_creator_an_owner(django_user_model):
    user = django_user_model.objects.create_user(email="owner@example.com", password="pw12345!")

    org = create_organization(name="Acme", user=user)

    assert isinstance(org, Organization)
    assert org.created_by == user
    membership = Membership.objects.get(organization=org, user=user)
    assert membership.role == Role.OWNER
    assert org.memberships.count() == 1


def test_create_organization_is_atomic(django_user_model, monkeypatch):
    user = django_user_model.objects.create_user(email="owner@example.com", password="pw12345!")

    def boom(*args, **kwargs):
        raise RuntimeError("membership creation failed")

    monkeypatch.setattr(Membership.objects, "create", boom)

    with pytest.raises(RuntimeError):
        create_organization(name="Acme", user=user)

    assert Organization.objects.count() == 0
