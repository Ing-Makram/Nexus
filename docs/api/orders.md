# Orders API (`/api/v1/orders/`)

All endpoints require `Authorization: Bearer <access>` (JWT).

## Model

| Field | Type | Notes |
| :--- | :--- | :--- |
| `id` | int | read-only |
| `organization` | int (Organization id) | **required on create**, **immutable** afterwards; must be one the caller belongs to |
| `customer` | int (Customer id) | must belong to the order's organization |
| `status` | string | `draft` \| `pending` \| `confirmed` \| `cancelled` \| `completed` (default `draft`) |
| `total_amount` | string (decimal, 2 dp) | `>= 0` |
| `notes` | string | optional |
| `created_by` | string (email) or null | read-only — the user who created the order |
| `created_at` / `updated_at` | ISO-8601 | read-only |

## Tenant isolation & roles

Every query is scoped via `selectors.orders_for_user`. A request for an order in
an organization the caller does not belong to returns **404**. Any member may
**read**; only **owner / admin** may create, update or delete (→ **403** for a
plain member). Writes go through `services.create_order` / `update_order` /
`delete_order`.

---

## GET `/api/v1/orders/`

List orders across all the caller's organizations, newest first.

**Query params** — `?organization=<id>`, `?status=<status>` (both optional).

## POST `/api/v1/orders/`

```json
{ "organization": 1, "customer": 7, "total_amount": "99.00", "status": "pending" }
```

- `organization` must be one the caller manages (owner/admin) → **403**/**400** otherwise.
- `customer` must belong to that organization → **400** `customer`.
- Invalid `status` / negative `total_amount` → **400**.

**201** — the created order.

## GET / PATCH / DELETE `/api/v1/orders/{id}/`

- **GET** — members, **404** for other tenants.
- **PATCH** — owner/admin; updates `customer`, `status`, `total_amount`, `notes`;
  `organization` is read-only and ignored; **403** for members, **404** for
  other tenants.
- **DELETE** — owner/admin → **204**; **403** for members, **404** for other
  tenants.
