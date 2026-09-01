# Auth API (`/api/v1/auth/`)

JWT authentication backed by `djangorestframework-simplejwt`. The user model
(`accounts.User`) authenticates by **email**; there is no username.

Send the access token as `Authorization: Bearer <access>` on protected requests.
Access tokens live 15 minutes, refresh tokens 1 day.

---

## POST `/api/v1/auth/register/`

Public self-service sign up. Returns a session so the client can sign the new
user in immediately.

**Request**

```json
{
  "email": "new.user@example.com",
  "password": "a-strong-passphrase",
  "first_name": "New",
  "last_name": "User"
}
```

`first_name` / `last_name` are optional. `password` is validated with Django's
`AUTH_PASSWORD_VALIDATORS` (length, common-password, numeric, similarity).

**201 Response** — same shape as `login` (`access`, `refresh`, `user`).

**400** — email already registered (case-insensitive), password too weak, or a
required field missing. The response body is a field → messages map, e.g.
`{"password": ["This password is too short. …"]}`. The password is never echoed
back.

---

## POST `/api/v1/auth/login/`

Public. Exchange credentials for a token pair.

**Request**

```json
{ "email": "user@example.com", "password": "s3cret" }
```

**200 Response**

```json
{
  "access": "<jwt>",
  "refresh": "<jwt>",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "",
    "last_name": "",
    "is_active": true,
    "date_joined": "2026-08-30T00:00:00Z"
  }
}
```

**401** — invalid credentials or inactive account. The password hash is never
returned by any endpoint.

---

## POST `/api/v1/auth/refresh/`

Public. Exchange a valid refresh token for a new access token.

**Request**

```json
{ "refresh": "<jwt>" }
```

**200 Response**

```json
{ "access": "<jwt>" }
```

**401** — refresh token invalid or expired.

---

## GET `/api/v1/auth/me/`

Requires `Authorization: Bearer <access>`. Returns the authenticated user
(same shape as `login.user`).

**401** — missing, malformed, or expired access token.
