from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.customers.models import Customer
from apps.organizations.selectors import membership_for

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.organizations.models import Organization

# Fields a caller may set on a customer through the API.
WRITABLE_FIELDS = ("name", "email", "phone", "company", "address")


def _require_membership(organization: Organization, actor: User) -> None:
    if membership_for(actor, organization) is None:
        raise PermissionDenied("You are not a member of this organization.")


@transaction.atomic
def create_customer(*, organization: Organization, actor: User, **fields: str) -> Customer:
    _require_membership(organization, actor)
    data = {key: fields.get(key, "") for key in WRITABLE_FIELDS}
    data["name"] = fields["name"]
    return Customer.objects.create(organization=organization, created_by=actor, **data)


@transaction.atomic
def update_customer(*, customer: Customer, **fields: str) -> Customer:
    for key, value in fields.items():
        if key in WRITABLE_FIELDS:
            setattr(customer, key, value)
    customer.save()
    return customer


@transaction.atomic
def delete_customer(*, customer: Customer) -> None:
    # Deleting a customer also deletes their orders and invoices. The customer
    # FKs are PROTECT at the database level (a backstop against accidental
    # deletes from elsewhere), so the dependent rows are cleared here first,
    # invoices before orders.
    customer.invoices.all().delete()
    customer.orders.all().delete()
    customer.delete()
