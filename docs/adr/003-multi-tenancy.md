# ADR 003 — Multi-tenancy via Organization / Membership

- **Status:** Accepted
- **Date:** 2026-08-31
- **Related:** [ADR 002](002-layered-architecture.md)

## Context

NEXUS is a B2B SaaS: users work inside organizations, and one user may belong to
several. Tenant data must never leak across organizations, and that guarantee
cannot depend on the frontend.

## Decision

**Shared schema, row-level tenancy.** One database; every tenant-owned row
carries an `organization` foreign key.

### Model

- `Organization` — the tenant. `name`, `created_by`, timestamps.
- `Membership` — through-model linking `User` ↔ `Organization` with a single
  `role` (`owner` / `admin` / `member`). `UniqueConstraint(organization, user)`
  so a user has exactly one membership (one role) per organization; a
  `CheckConstraint` pins `role` to the valid set.
- Future business models (customers, orders, …) will each carry an
  `organization` FK and be scoped the same way.

### Tenant isolation — scoped querysets

- `selectors.organizations_for_user(user)` is the single scoping primitive:
  `Organization.objects.filter(memberships__user=user)`. API code never queries
  `Organization.objects` directly.
- `OrganizationViewSet.get_queryset()` and `MembershipViewSet.get_organization()`
  build on it, so a request touching a non-member organization resolves to
  **404 — existence is never revealed** (not 403).
- Nested collections (`/organizations/{id}/members/`) resolve the parent through
  the same scoped path before doing anything else.

### Server-side authorization

- DRF defaults to `IsAuthenticated` globally ([ADR 004](004-authentication.md));
  public endpoints opt out explicitly.
- Role checks are reusable permission classes (`IsOrganizationMember`,
  `IsOrganizationAdmin`, `IsOrganizationOwner`, `CanManageOrganizationMembers`).
- Fine-grained invariants live in services: the owner's membership cannot be
  changed or removed; only an owner may modify/remove an admin; roles assignable
  through the API are limited to `admin` / `member`.
- The frontend's organization switcher and route guards are **convenience
  only** — every rule is enforced again by the API.

## Consequences

- **Positive:** simplest possible operations (one DB, one migration path);
  scoping logic is centralised and auditable; cross-tenant access fails closed
  with 404.
- **Positive:** the `organization`-FK + selector pattern extends to every future
  module unchanged.
- **Negative:** isolation depends on every query going through a selector — a
  raw `Model.objects` call in a view is a latent data-leak; review and tests
  must guard it.
- **Negative:** no hard database-level separation between tenants (acceptable at
  current scale; revisit if a customer contractually requires it).
