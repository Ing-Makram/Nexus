# ADR 005 — Defer microservices

- **Status:** Accepted
- **Date:** 2026-08-31
- **Related:** [ADR 001](001-modular-monolith.md)

## Context

Microservices are often adopted early as a default "scalable" architecture. For
a small team on a young product they usually cost more than they return.

## Decision

**NEXUS is not, and will not soon be, a microservice system.** It stays a
modular monolith (ADR 001) until a concrete, measured pressure justifies
extracting a specific service.

### Why premature microservices would hurt now

- **Distributed complexity with no payoff:** network failures, retries,
  partial failure, versioned contracts, and distributed tracing — for a system
  that comfortably fits one process.
- **Lost transactions:** today `create_organization` (org + owner membership) is
  one atomic DB transaction. Split across services it needs sagas / eventual
  consistency and compensating actions.
- **Operational load:** many pipelines, deployables, dashboards, and on-call
  surfaces instead of one — a real tax on a small team.
- **Premature boundaries:** the domain is still moving; cutting service seams
  now would freeze guesses that turn out wrong, and cross-service refactors are
  far more expensive than moving code between apps.

### What we do instead

- Keep **well-defined module boundaries** (ADR 001) and the layered structure
  (ADR 002) so each app already has a clean public surface
  (`models` / `selectors` / `services`).
- Prefer **explicit domain events / service functions** over apps reaching into
  each other, so an inter-module call is easy to later replace with a queue or
  RPC.
- Route heavy or slow work to **Celery tasks** as it arises — that async seam
  (a worker is already scaffolded) is the natural place a future service would
  detach.

### Later, selective extraction

When (and only when) scale demands it, extract one module at a time behind its
existing interface. Likely first candidates, *if their load justifies it*:

- **Analytics / reporting** — the dashboard's read aggregation, plus any future
  scheduled jobs, would otherwise compete with transactional traffic; can run
  off a read replica or its own store.
- **A third-party integration boundary** — any bursty, quota- or
  latency-bound external work with a naturally async profile very different
  from CRUD traffic.

Extraction is a future ADR with evidence, not a plan.

## Consequences

- **Positive:** engineering effort stays on product; the system is simple to run
  and change.
- **Positive:** disciplined modules mean extraction later is an option, not a
  rewrite.
- **Negative:** the whole backend scales as a unit until the first extraction;
  a pathological module could force that work sooner.
- **Negative:** requires ongoing boundary discipline in review to keep the
  "extractable later" property real.
