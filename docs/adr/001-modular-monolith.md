# ADR 001 — Modular monolith

- **Status:** Accepted
- **Date:** 2026-08-31

## Context

NEXUS is early-stage: one small team, an evolving domain model, no production
load, and a roadmap (organizations, then the customer / order / invoice
domain) that is still being discovered. We need fast iteration and cheap
refactoring across feature boundaries.

## Decision

Build NEXUS as a **modular monolith**: a single Django project and a single
deployable backend, internally divided into focused Django apps with explicit
boundaries.

- Each business capability is its own app under `backend/apps/` (`accounts`,
  `organizations`, …). `backend/config/` holds project wiring only.
- Apps own their models, migrations, API, and tests. Cross-app use goes through
  a public surface — models, `selectors`, `services` — never another app's
  `views` or private helpers.
- `accounts` is a foundational dependency (`AUTH_USER_MODEL`); feature apps may
  depend on it. Feature apps should not depend on each other cyclically.
- One database, one process, one deployment. A Celery worker is scaffolded in
  the same codebase for when async work is needed; it runs no tasks today
  (see [ADR 005](005-future-microservices.md)).

## Consequences

- **Positive:** one repo to reason about; atomic cross-cutting changes and
  migrations; local calls instead of network hops; trivial transactions across
  modules; low operational cost.
- **Positive:** clean app boundaries keep the door open to extraction later
  (see [ADR 005](005-future-microservices.md)).
- **Negative:** the whole backend scales and deploys as a unit; a heavy module
  can't be scaled independently yet.
- **Negative:** boundary discipline is a convention, not enforced by the
  network — code review must guard against apps reaching into each other.
