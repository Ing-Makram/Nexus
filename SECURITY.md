# Security Policy

## Supported versions

NEXUS is a single, continuously developed project on `main` — there are no
maintained release branches. Security fixes land on `main`.

## Reporting a vulnerability

If you find a security issue (an authentication bypass, a tenant-isolation
leak, a way to escalate role/permissions, exposed secrets, or similar):

- **Do not open a public issue.**
- Use GitHub's private **[Report a vulnerability](../../security/advisories/new)**
  flow (Security → Advisories) on this repository, or contact the maintainer
  directly with enough detail to reproduce the issue.
- Please include: the affected endpoint/component, steps to reproduce,
  and the impact you'd expect (e.g. cross-tenant data access).

You'll get an acknowledgement and, once the fix is confirmed, credit in the
advisory unless you'd prefer otherwise. Please allow time to ship and deploy a
fix before any public disclosure.

## In scope

- Authentication and JWT handling (`apps/accounts`)
- Tenant isolation across organizations (every `*_for_user` selector)
- Role-based authorization (owner / admin / member)
- Production configuration (`config/settings/production.py`)
- Secret/credential handling and logging (`apps/common/observability.py`)

## Out of scope

- Findings that require a compromised database, server, or CI credentials.
- The absence of features that were never claimed (e.g. rate limiting is a
  documented future improvement, not a vulnerability report).
- Third-party dependencies — report those upstream; we track and update them
  here once a fix is published.

## Responsible handling of credentials

This repository never contains real secrets. If you believe a credential was
accidentally committed, report it privately (as above) rather than commenting
on the commit — the value must be rotated regardless of whether it was ever
truly reachable.
