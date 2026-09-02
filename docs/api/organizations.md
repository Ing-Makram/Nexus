# Organizations API (`/api/v1/organizations/`)

All endpoints require `Authorization: Bearer <access>`.

## Model

| Entity | Fields |
| :--- | :--- |
| `Organization` | `id`, `name` (2–120 chars, trimmed), `created_at`, `updated_at` |
| `Membership` | `organization`, `user`, `role` (`owner` \| `admin` \| `member`), `created_at`, `updated_at` — unique per `(organization, user)` |

- A user belongs to many organizations; an organization has many users.
- The organization serializer's `role` field is the **requesting user's** role.

## Tenant isolation

The list query is always scoped to the caller's organizations. A request for an
organization the caller does not belong to returns **404**, never 403 — the
existence of other tenants' data is never revealed. Frontend checks are
convenience only; enforcement is server-side.

---

## POST `/api/v1/organizations/`

Create an organization. The caller becomes its `owner`.

**Request** — `{ "name": "Acme Inc" }`

**201** — `{ "id": 1, "name": "Acme Inc", "role": "owner", "created_at": "...", "updated_at": "..." }`

**400** — name missing / blank / < 2 / > 120 chars. Any `role` sent by the
client is ignored.

## GET `/api/v1/organizations/`

**200** — array of the caller's organizations (each with the caller's `role`),
ordered by name.

## GET `/api/v1/organizations/{id}/`

**200** for a member. **404** otherwise.

## PATCH `/api/v1/organizations/{id}/`

Update `name`. Allowed for `owner` or `admin`.

- **200** — updated organization.
- **403** — caller is a `member`.
- **404** — caller is not a member.
- `role` and timestamps are read-only.

## DELETE `/api/v1/organizations/{id}/`

Allowed for `owner` only.

- **204** — deleted. `services.delete_organization` also removes the
  organization's customers, orders and invoices in the same transaction
  (the customer FKs are `PROTECT`, so this is done explicitly rather than by an
  `on_delete` rule); memberships cascade.
- **403** — caller is `admin` or `member`.
- **404** — caller is not a member.
