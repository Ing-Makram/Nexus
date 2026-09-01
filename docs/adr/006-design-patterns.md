# ADR 006 — Design patterns in use and deferred

- **Status:** Accepted
- **Date:** 2026-08-31
- **Related:** [ADR 002](002-layered-architecture.md)

## Context

We want a shared vocabulary for the patterns NEXUS already relies on, and a
clear line on which patterns are welcome *later* — so they arrive when a problem
demands them, not because a checklist wants them.

## Patterns currently in use

- **Layered architecture** — `models → selectors → services → permissions →
  serializers → views`, dependencies pointing one way. See ADR 002.
- **Service layer** — business operations are plain functions in `services.py`
  (`create_organization`, `add_member`, `change_member_role`, `remove_member`).
  They own transactions and invariants and are callable from any entry point
  (API, admin, Celery, shell).
- **Selector pattern** — reads are named, parameterised queryset builders in
  `selectors.py` (`organizations_for_user`, `members_of`,
  `membership_of_user`). Tenant scoping lives here and nowhere else.
- **Dependency / permission separation** — "can this actor do this?" is
  isolated in reusable DRF permission classes (`IsOrganizationMember`,
  `IsOrganizationAdmin`, `IsOrganizationOwner`, `CanManageOrganizationMembers`),
  kept out of views and services. Object-resolution is generic
  (`obj` that *is* or *has* `.organization`) so the classes are reusable.

## Patterns that may be introduced when justified

Adopt only against a concrete, current need — with a short ADR noting the
trigger.

- **Strategy** — when one operation needs interchangeable algorithms selected at
  runtime (e.g. pluggable export/report formats, tax or pricing rules per
  region, alternate payment providers).
- **Factory** — when object construction becomes non-trivial or branchy (e.g.
  building the right provider client from config, assembling test fixtures) and
  a plain constructor or a `create_*` service no longer reads clearly.
- **Observer / event-driven** — when a write must fan out to several
  independent reactions (audit log, notifications, cache invalidation, search
  indexing). Prefer explicit domain events dispatched from services (and handled
  by Celery tasks) over Django signals, so the flow stays traceable. This is
  also the seam a future service would detach along (ADR 005).
- **Repository** — only where an abstraction over persistence genuinely earns
  its keep: swappable backends, a non-ORM store, or contract-testing against a
  fake. The `selectors` + `services` split already gives most of the benefit;
  do not wrap the ORM "just in case".

## Decision

Keep using the four patterns above because they solve problems we have. Treat
the deferred list as a menu, not a plan.

**Do not introduce a pattern for pattern-count.** Abstraction has a cost —
indirection, more files, a steeper first read. A new pattern must be justified
by a present, concrete problem (duplication that hurts, a branch that keeps
growing, a fan-out that keeps expanding), and the justification goes in an ADR.
"We might need it" is not a justification.

## Consequences

- **Positive:** a common language for how the code is organised; new patterns
  land deliberately and documented.
- **Positive:** guards against speculative generality and framework-itis.
- **Negative:** requires reviewers to push back on premature abstraction, which
  can feel like friction.
