# ADR 004 — Email-based user + JWT authentication

- **Status:** Accepted
- **Date:** 2026-08-31

## Context

NEXUS has a React SPA talking to a stateless DRF API, and will later add other
API clients. Django's default `username` field is dead weight for a product
where people log in with an email address.

## Decision

### Custom user model

`accounts.User` (subclass of `AbstractUser`) set as `AUTH_USER_MODEL` from the
first migration:

- `username` removed; `email` is unique and is `USERNAME_FIELD`.
- `UserManager` creates users/superusers by email.
- Introduced before any user rows existed, so no swap migration pain.

### JWT authentication

`djangorestframework-simplejwt`. DRF is configured with
`JWTAuthentication` as the default authentication class and `IsAuthenticated` as
the default permission; public endpoints (`register`, `login`, `refresh`,
health) opt out with `AllowAny`.

Stateless bearer tokens fit the SPA + future-clients picture and keep the API
horizontally scalable with no server-side session store.

### Access / refresh token strategy

| Token | Lifetime | Storage (web client) | Purpose |
| :---- | :------- | :------------------- | :------ |
| access | 15 min | in memory only | sent as `Authorization: Bearer …` on every request |
| refresh | 1 day | `localStorage` | exchanged at `/auth/refresh/` for a new access token |

- Endpoints: `POST /api/v1/auth/register/`, `/login/`, `/refresh/`,
  `GET /api/v1/auth/me/`. `register` and `login` return
  `{access, refresh, user}`.
- The SPA keeps the access token in memory (not persisted), silently refreshes
  on a 401 once, and restores a session on reload from the stored refresh token.
- No refresh-token rotation or server-side blocklist yet: logout is
  client-side, and a refresh token stays valid until it expires.

## Consequences

- **Positive:** email-first identity with no legacy `username`; stateless API;
  clean auto-login after sign-up.
- **Negative:** refresh token in `localStorage` is exposed to XSS; acceptable
  for now, revisit with rotation + an HttpOnly-cookie flow or a blocklist if the
  threat model tightens.
- **Negative:** short access-token life means a refresh round-trip roughly every
  15 minutes; mitigated by the client's transparent retry.
- **Negative:** revoking a compromised token before expiry is not possible
  without adding a blocklist.
