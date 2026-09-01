import json
from datetime import date
from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.invoices.models import Invoice, InvoiceStatus
from apps.invoices.serializers import InvoiceSerializer
from apps.orders.models import Order
from apps.organizations.models import Membership, Organization, Role

pytestmark = pytest.mark.django_db

ISSUE_DATE = date(2026, 1, 1)

FIELDS = {
    "id",
    "organization",
    "customer",
    "order",
    "invoice_number",
    "status",
    "issue_date",
    "due_date",
    "total_amount",
    "notes",
    "created_by",
    "created_at",
    "updated_at",
}


class Ctx:
    def __init__(self, user):
        self.user = user


def make_user(django_user_model, email):
    return django_user_model.objects.create_user(email=email, password="pw12345!")


@pytest.fixture
def alice(django_user_model):
    return make_user(django_user_model, "alice@example.com")


@pytest.fixture
def org_a(alice):
    org = Organization.objects.create(name="Org A")
    Membership.objects.create(organization=org, user=alice, role=Role.OWNER)
    return org


@pytest.fixture
def org_b(django_user_model):
    org = Organization.objects.create(name="Org B")
    Membership.objects.create(
        organization=org, user=make_user(django_user_model, "bob@example.com"), role=Role.OWNER
    )
    return org


@pytest.fixture
def customer_a(org_a):
    return Customer.objects.create(organization=org_a, name="Acme")


@pytest.fixture
def customer_b(org_b):
    return Customer.objects.create(organization=org_b, name="Beta")


@pytest.fixture
def invoice_a(org_a, customer_a):
    return Invoice.objects.create(
        organization=org_a,
        customer=customer_a,
        invoice_number="INV-001",
        issue_date=ISSUE_DATE,
        total_amount=Decimal("10.00"),
    )


def ser(user, **kwargs):
    return InvoiceSerializer(context={"request": Ctx(user)}, **kwargs)


def payload(org, customer, **overrides):
    data = {
        "organization": org.id,
        "customer": customer.id,
        "invoice_number": "INV-100",
        "issue_date": "2026-01-01",
        "total_amount": "50.00",
    }
    data.update(overrides)
    return data


def test_serialized_invoice_has_exactly_the_allowed_fields(alice, invoice_a):
    data = ser(alice, instance=invoice_a).data
    assert set(data) == FIELDS
    assert data["organization"] == invoice_a.organization_id
    assert data["customer"] == invoice_a.customer_id
    assert data["order"] is None
    assert data["total_amount"] == "10.00"


def test_serialization_never_exposes_secrets(alice, invoice_a):
    blob = json.dumps(ser(alice, instance=invoice_a).data)
    for needle in ("password", "token", "secret", "access", "refresh"):
        assert needle not in blob


def test_id_and_timestamps_are_read_only():
    fields = InvoiceSerializer().fields
    assert fields["id"].read_only is True
    assert fields["created_at"].read_only is True
    assert fields["updated_at"].read_only is True
    assert fields["created_by"].read_only is True


def test_valid_create_payload(alice, org_a, customer_a):
    serializer = ser(alice, data=payload(org_a, customer_a, status=InvoiceStatus.SENT))
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["organization"] == org_a


def test_organization_must_be_one_the_user_belongs_to(alice, org_b, customer_b):
    serializer = ser(alice, data=payload(org_b, customer_b))
    assert not serializer.is_valid()
    assert "organization" in serializer.errors


def test_customer_must_belong_to_the_selected_organization(
    django_user_model, alice, org_a, customer_a
):
    other = Organization.objects.create(name="Other")
    Membership.objects.create(organization=other, user=alice, role=Role.OWNER)
    foreign_customer = Customer.objects.create(organization=other, name="Foreign")

    serializer = ser(alice, data=payload(org_a, foreign_customer))
    assert not serializer.is_valid()
    assert "customer" in serializer.errors


def test_order_must_belong_to_the_selected_customer(alice, org_a, customer_a):
    other_customer = Customer.objects.create(organization=org_a, name="Other")
    other_order = Order.objects.create(
        organization=org_a, customer=other_customer, total_amount=Decimal("1.00")
    )
    serializer = ser(alice, data=payload(org_a, customer_a, order=other_order.id))
    assert not serializer.is_valid()
    assert "order" in serializer.errors


def test_blank_invoice_number_is_allowed_for_auto_numbering(alice, org_a, customer_a):
    serializer = ser(alice, data=payload(org_a, customer_a, invoice_number="   "))
    assert serializer.is_valid(), serializer.errors
    # The serializer leaves it blank; the service assigns the next number.
    assert serializer.validated_data["invoice_number"] == ""


def test_invoice_number_can_be_omitted(alice, org_a, customer_a):
    body = payload(org_a, customer_a)
    del body["invoice_number"]
    serializer = ser(alice, data=body)
    assert serializer.is_valid(), serializer.errors


def test_duplicate_invoice_number_is_rejected(alice, org_a, customer_a, invoice_a):
    serializer = ser(alice, data=payload(org_a, customer_a, invoice_number="INV-001"))
    assert not serializer.is_valid()
    assert "invoice_number" in serializer.errors


def test_negative_total_amount_is_rejected(alice, org_a, customer_a):
    serializer = ser(alice, data=payload(org_a, customer_a, total_amount="-1.00"))
    assert not serializer.is_valid()
    assert "total_amount" in serializer.errors


def test_invalid_status_is_rejected(alice, org_a, customer_a):
    serializer = ser(alice, data=payload(org_a, customer_a, status="refunded"))
    assert not serializer.is_valid()
    assert "status" in serializer.errors


def test_due_date_before_issue_date_is_rejected(alice, org_a, customer_a):
    serializer = ser(
        alice,
        data=payload(org_a, customer_a, issue_date="2026-01-10", due_date="2026-01-01"),
    )
    assert not serializer.is_valid()
    assert "due_date" in serializer.errors


def test_organization_is_immutable_on_update(alice, invoice_a, org_b):
    serializer = ser(
        alice,
        instance=invoice_a,
        data={"organization": org_b.id, "status": InvoiceStatus.SENT},
        partial=True,
    )
    assert serializer.is_valid(), serializer.errors
    assert "organization" not in serializer.validated_data
    assert serializer.validated_data["status"] == InvoiceStatus.SENT


def test_update_keeping_its_own_number_is_allowed(alice, invoice_a):
    serializer = ser(alice, instance=invoice_a, data={"invoice_number": "INV-001"}, partial=True)
    assert serializer.is_valid(), serializer.errors
