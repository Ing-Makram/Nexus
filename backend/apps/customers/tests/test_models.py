import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.customers.models import Customer
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization():
    return Organization.objects.create(name="Acme")


def test_create_customer_with_only_required_fields(organization):
    customer = Customer.objects.create(organization=organization, name="Jane Doe")

    assert customer.pk is not None
    assert customer.organization == organization
    assert customer.name == "Jane Doe"
    # Optional fields default to an empty string, never NULL.
    assert customer.email == ""
    assert customer.phone == ""
    assert customer.company == ""
    assert customer.address == ""


def test_create_customer_with_all_fields(organization):
    customer = Customer.objects.create(
        organization=organization,
        name="Jane Doe",
        email="jane@example.com",
        phone="+1 555 0100",
        company="Doe LLC",
        address="1 Main St\nSpringfield",
    )
    customer.full_clean()  # no validation errors

    assert customer.email == "jane@example.com"
    assert customer.company == "Doe LLC"


def test_organization_is_required(organization):
    with pytest.raises(IntegrityError), transaction.atomic():
        Customer.objects.create(name="No Org")


def test_name_is_required():
    org = Organization.objects.create(name="Acme")
    with pytest.raises(ValidationError):
        Customer(organization=org).full_clean()


def test_blank_name_is_rejected_by_the_database(organization):
    with pytest.raises(IntegrityError), transaction.atomic():
        Customer.objects.create(organization=organization, name="")


def test_invalid_email_is_rejected_by_validation(organization):
    customer = Customer(organization=organization, name="Jane", email="not-an-email")
    with pytest.raises(ValidationError):
        customer.full_clean()


def test_customer_is_reachable_through_the_organization(organization):
    customer = Customer.objects.create(organization=organization, name="Jane Doe")

    assert list(organization.customers.all()) == [customer]


def test_customer_belongs_to_exactly_one_organization():
    org_a = Organization.objects.create(name="Org A")
    org_b = Organization.objects.create(name="Org B")
    customer = Customer.objects.create(organization=org_a, name="Jane")

    assert org_a.customers.count() == 1
    assert org_b.customers.count() == 0

    customer.organization = org_b
    customer.save(update_fields=["organization"])
    assert org_a.customers.count() == 0
    assert org_b.customers.count() == 1


def test_deleting_the_organization_cascades_to_customers(organization):
    Customer.objects.create(organization=organization, name="Jane")
    Customer.objects.create(organization=organization, name="John")

    organization.delete()

    assert Customer.objects.count() == 0


def test_timestamps_are_configured_and_populated(organization):
    assert Customer._meta.get_field("created_at").auto_now_add is True
    assert Customer._meta.get_field("updated_at").auto_now is True

    customer = Customer.objects.create(organization=organization, name="Jane")
    created_at, updated_at = customer.created_at, customer.updated_at
    assert created_at is not None
    assert updated_at is not None

    customer.name = "Jane Roe"
    customer.save()
    customer.refresh_from_db()

    # created_at is frozen; updated_at is bumped by auto_now on every save
    # (the two saves can land in the same clock tick, hence >=).
    assert customer.created_at == created_at
    assert customer.updated_at >= updated_at


def test_default_ordering_is_by_name(organization):
    Customer.objects.create(organization=organization, name="Zoe")
    Customer.objects.create(organization=organization, name="Amy")
    Customer.objects.create(organization=organization, name="Mike")

    assert [c.name for c in Customer.objects.all()] == ["Amy", "Mike", "Zoe"]


def test_str_is_the_name(organization):
    assert str(Customer(organization=organization, name="Jane Doe")) == "Jane Doe"
