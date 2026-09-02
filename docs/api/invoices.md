# Invoices API (`/api/v1/invoices/`)

All endpoints require `Authorization: Bearer <access>` (JWT).

## Model

| Field | Type | Notes |
| :--- | :--- | :--- |
| `id` | int | read-only |
| `organization` | int | **required on create**, **immutable** afterwards; must be one the caller belongs to |
| `customer` | int | must belong to the invoice's organization |
| `order` | int or null | optional; must belong to the same organization **and** customer |
| `invoice_number` | string | unique **per organization**; **omit or leave blank to auto-assign** `INV-0001`, `INV-0002`, … |
| `status` | string | `draft` \| `sent` \| `paid` \| `overdue` \| `void` (default `draft`) |
| `issue_date` | date (`YYYY-MM-DD`) | **required** |
| `due_date` | date or null | optional; must be `>= issue_date` |
| `total_amount` | string (decimal, 2 dp) | `>= 0` |
| `notes` | string | optional |
| `created_by` | string (email) or null | read-only |
| `created_at` / `updated_at` | ISO-8601 | read-only |

## Tenant isolation & roles

Scoped via `selectors.invoices_for_user`; other tenants' invoices → **404**. Any
member may **read**; only **owner / admin** may create, update or delete. Writes
go through `services.create_invoice` / `update_invoice` / `delete_invoice`.
Deleting a linked `order` sets the invoice's `order` to `null` (the invoice
survives).

---

## GET `/api/v1/invoices/`

List invoices across all the caller's organizations, newest first.
**Query params** (all optional) — `?organization=<id>`, `?status=<status>`,
`?date_from=<YYYY-MM-DD>` / `?date_to=<YYYY-MM-DD>` (inclusive bounds on
`issue_date`; a malformed value is ignored).

## POST `/api/v1/invoices/`

```json
{ "organization": 1, "customer": 7, "issue_date": "2026-01-01", "total_amount": "1200.00" }
```

**400** for: out-of-scope `organization`/`customer`/`order`, cross-org or
cross-customer `order`, duplicate `invoice_number`, invalid `status`, negative
`total_amount`, `due_date` before `issue_date`.

**201** — the created invoice (with the assigned `invoice_number`).

## GET / PATCH / DELETE `/api/v1/invoices/{id}/`

- **GET** — members; **404** for other tenants.
- **PATCH** — owner/admin; updates `customer`, `order`, `invoice_number`,
  `status`, `issue_date`, `due_date`, `total_amount`, `notes`; `organization` is
  read-only. **403** for members, **404** for other tenants.
- **DELETE** — owner/admin → **204**.
