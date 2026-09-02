# Dashboard API (`/api/v1/dashboard/`)

Requires `Authorization: Bearer <access>` (JWT). Read-only aggregation for one
organization — there is no model, no write path, and no role gate beyond
membership (it only exposes figures a member can already compute from the list
endpoints).

## GET `/api/v1/dashboard/?organization=<id>`

| Case | Response |
| :--- | :--- |
| `organization` missing / non-numeric | `400 {"organization": "This query parameter is required."}` |
| caller is not a member of that organization | `404 {"detail": "Not found."}` |
| otherwise | `200` with the body below |

```json
{
  "organization": 1,
  "customers": { "total": 12 },
  "orders": {
    "total": 40,
    "by_status": { "draft": 3, "completed": 37 }
  },
  "invoices": {
    "total": 30,
    "by_status": { "draft": 5, "sent": 10, "paid": 12, "overdue": 2, "void": 1 },
    "total_amount": "45000.00",        // sum of all invoices except "void"
    "paid_amount": "20000.00",         // sum where status = "paid"
    "outstanding_amount": "23000.00",  // sum where status in ("sent", "overdue")
    "overdue_count": 2
  },
  "recent_orders": [
    { "id": 9, "customer": "Globex", "status": "completed",
      "total_amount": "250.00", "created_at": "2026-03-01T00:00:00Z" }
  ],
  "recent_invoices": [
    { "id": 3, "invoice_number": "INV-0003", "customer": "Globex",
      "status": "overdue", "total_amount": "90.00",
      "issue_date": "2026-02-01", "due_date": "2026-02-15" }
  ]
}
```

- `recent_*` are capped at 5 rows, newest first, and expose only the fields
  shown — customer **name**, never emails or unrelated ids.
- Money values are 2dp decimal strings regardless of DB backend.

## GET `/api/v1/dashboard/timeseries/?organization=<id>&days=<30|90>`

Daily activity for the last `days` calendar days, for date-based charts.

| Case | Response |
| :--- | :--- |
| `organization` missing / non-numeric | `400 {"organization": "This query parameter is required."}` |
| caller is not a member of that organization | `404 {"detail": "Not found."}` |
| `days` present but not `30` or `90` | `400 {"days": "Must be one of [30, 90]."}` |
| otherwise | `200` with the body below (`days` defaults to `30`) |

```json
{
  "organization": 1,
  "start": "2026-08-04",
  "end": "2026-09-02",
  "days": 30,
  "points": [
    { "date": "2026-08-04", "orders": 2, "invoices": 1, "customers": 0,
      "invoiced_amount": "340.00", "paid_amount": "0.00" }
  ]
}
```

- `points` always has exactly `days` entries, one per calendar day from `start`
  to `end` inclusive, ascending and zero-filled — no gaps.
- Orders and customers are bucketed by `created_at`; invoices, `invoiced_amount`
  and `paid_amount` by invoice `issue_date`. `invoiced_amount` excludes `void`;
  `paid_amount` counts only `paid`.

## Tenant isolation

`selectors.dashboard_stats` and `selectors.dashboard_timeseries` build every
queryset from the existing `customers_for_user` / `orders_for_user` /
`invoices_for_user` selectors, then `.filter(organization=...)`. A non-member's
request 404s before any aggregation runs; another organization's rows can never
appear in the totals.
