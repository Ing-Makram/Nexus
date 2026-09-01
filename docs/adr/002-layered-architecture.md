# ADR 002 — Layered application architecture

- **Status:** Accepted
- **Date:** 2026-08-31
- **Related:** [ADR 001](001-modular-monolith.md), [ADR 006](006-design-patterns.md)

## Context

"Fat models / fat views" both end badly: business rules scatter across
serializers, viewsets, and signal handlers, and become impossible to test in
isolation or reuse (API, admin, management command, a future background job).
We want one obvious home for each kind of logic.

## Decision

Every app follows the same one-directional layering:

```
models → selectors → services → permissions → serializers → views
```

| Layer | Responsibility | Must not |
| :---- | :------------- | :------- |
| **models** | Schema, field validation, DB constraints & indexes, trivial derived properties. | Contain workflow logic or query helpers. |
| **selectors** | Read paths: parameterised, reusable querysets. **The only place tenant scoping is expressed.** | Write data. |
| **services** | Write paths and multi-step business transactions; enforce invariants; own `@transaction.atomic`. | Build response shapes or read `request`. |
| **permissions** | Reusable DRF permission classes: "may this actor perform this action on this object?" | Perform the mutation or contain domain rules. |
| **serializers** | Input parsing + field-level validation; output representation. | Contain business rules or database writes. |
| **views** | Thin HTTP glue: pick permissions, parse via serializer, call one selector/service, return. | Contain business logic or raw ORM queries. |

Dependencies point downward only. Views may call selectors and services;
services may call selectors; nothing calls views.

## Reference implementation

`backend/apps/organizations/` is the canonical example:

- `selectors.organizations_for_user()` / `members_of()` — scoped reads.
- `services.create_organization()` / `add_member()` / `change_member_role()` /
  `remove_member()` — atomic writes that enforce every rule.
- `permissions.IsOrganizationMember` / `IsOrganizationAdmin` /
  `CanManageOrganizationMembers` — role gates, reusable by future modules whose
  objects expose `.organization`.
- `views.OrganizationViewSet` / `MembershipViewSet` — a few lines per action.

New apps copy this structure.

## Consequences

- **Positive:** business logic is unit-testable without HTTP; reusable from
  admin, Celery, and shell; each file has a predictable job.
- **Positive:** security-relevant code (scoping, permissions) is concentrated
  and easy to audit.
- **Negative:** more files and a little ceremony for a small endpoint.
- **Negative:** the layering is a discipline; review must reject ORM writes in
  views or business rules in serializers.
