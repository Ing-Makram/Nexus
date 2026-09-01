# Customers API (`/api/v1/customers/`)

All endpoints require `Authorization: Bearer <access>` (JWT).

## Model

| Field | Type | Notes |
| :--- | :--- | :--- |
| `id` | int | read-only |
| `organization` | int (Organization id) | **required on create**, **immutable** afterwards; must be an organization the caller belongs to |
| `name` | string | **required**; leading/trailing whitespace trimmed; may not be blank |
| `email` | string | optional; validated as an email address when present |
| `phone` | string | optional (≤ 32 chars) |
| `company` | string | optional (≤ 255 chars) |
| `address` | string | optional (free text) |
| `created_at` / `updated_at` | ISO-8601 | read-only |

## Tenant isolation

Every query is scoped to the caller's organizations via
`selectors.customers_for_user`. A request for a customer in an organization the
caller does not belong to returns **404** — never 403 — so cross-tenant
existence is not revealed. Enforcement is entirely server-side.

---

## GET `/api/v1/customers/`

List every customer across **all** organizations the caller belongs to, ordered
by name.

**200** — array of customer objects.

## POST `/api/v1/customers/`

Create a customer.

**Request**

```json
{ "organization": 1, "name": "Jane Doe", "email": "jane@example.com" }
```

- `organization` must be one the caller is a member of; otherwise **400**
  (`{"organization": ["…"]}`).
- `name` is trimmed; blank/whitespace-only → **400**.
- `email`, `phone`, `company`, `address` are optional.

**201** — the created customer.

## GET `/api/v1/customers/{id}/`

**200** for a customer in one of the caller's organizations. **404** otherwise.

## PATCH `/api/v1/customers/{id}/`

Partial update of `name`, `email`, `phone`, `company`, `address`.

- `organization` is read-only; if sent it is **ignored** (the customer's
  organization never changes).
- `name` is trimmed; blank → **400**.
- **404** if the customer is not in one of the caller's organizations.

**200** — the updated customer.

## DELETE `/api/v1/customers/{id}/`

**204** on success. **404** if the customer is not in one of the caller's
organizations.
