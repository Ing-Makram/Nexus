import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.organizations.models import Membership, Organization, Role

pytestmark = pytest.mark.django_db


def make_user(django_user_model, email):
    return django_user_model.objects.create_user(email=email, password="pw12345!")


def test_membership_is_unique_per_user_and_organization(django_user_model):
    user = make_user(django_user_model, "a@example.com")
    org = Organization.objects.create(name="Acme")
    Membership.objects.create(organization=org, user=user, role=Role.OWNER)

    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.create(organization=org, user=user, role=Role.MEMBER)


def test_membership_default_role_is_member(django_user_model):
    user = make_user(django_user_model, "a@example.com")
    org = Organization.objects.create(name="Acme")

    membership = Membership.objects.create(organization=org, user=user)

    assert membership.role == Role.MEMBER


def test_role_check_constraint_rejects_unknown_role(django_user_model):
    user = make_user(django_user_model, "a@example.com")
    org = Organization.objects.create(name="Acme")

    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.create(organization=org, user=user, role="superuser")


def test_user_can_belong_to_multiple_organizations(django_user_model):
    user = make_user(django_user_model, "a@example.com")
    one = Organization.objects.create(name="One")
    two = Organization.objects.create(name="Two")
    Membership.objects.create(organization=one, user=user, role=Role.OWNER)
    Membership.objects.create(organization=two, user=user, role=Role.MEMBER)

    assert set(user.organizations.values_list("name", flat=True)) == {"One", "Two"}


def test_organization_can_have_multiple_members(django_user_model):
    a = make_user(django_user_model, "a@example.com")
    b = make_user(django_user_model, "b@example.com")
    org = Organization.objects.create(name="Acme")
    Membership.objects.create(organization=org, user=a, role=Role.OWNER)
    Membership.objects.create(organization=org, user=b, role=Role.MEMBER)

    assert org.memberships.count() == 2


def test_organization_name_min_length_is_validated():
    with pytest.raises(ValidationError):
        Organization(name="A").full_clean()


def test_roles_are_the_expected_three():
    assert set(Role.values) == {"owner", "admin", "member"}
