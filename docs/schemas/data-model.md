# Data Model

Every tenant-owned row carries an `organization` FK. Tenant scoping is enforced
in application code (the `*_for_user` selectors), not by the schema alone.

```mermaid
erDiagram
    USER ||--o{ MEMBERSHIP : has
    ORGANIZATION ||--o{ MEMBERSHIP : has
    ORGANIZATION ||--o{ CUSTOMER : owns
    ORGANIZATION ||--o{ ORDER : owns
    ORGANIZATION ||--o{ INVOICE : owns
    CUSTOMER ||--o{ ORDER : places
    CUSTOMER ||--o{ INVOICE : billed_on
    ORDER ||--o{ INVOICE : "invoiced by (optional)"

    USER {
      int id PK
      string email UK
      string first_name
      string last_name
      bool is_active
    }
    ORGANIZATION {
      int id PK
      string name
    }
    MEMBERSHIP {
      int id PK
      int organization_id FK
      int user_id FK
      string role "owner | admin | member"
    }
    CUSTOMER {
      int id PK
      int organization_id FK
      string name
      string email
      string phone
      string company
      text address
    }
    ORDER {
      int id PK
      int organization_id FK
      int customer_id FK
      string status "draft|pending|confirmed|cancelled|completed"
      decimal total_amount
      text notes
    }
    INVOICE {
      int id PK
      int organization_id FK
      int customer_id FK
      int order_id FK "nullable"
      string invoice_number "unique per organization"
      string status "draft|sent|paid|overdue|void"
      date issue_date
      date due_date "nullable, >= issue_date"
      decimal total_amount
      text notes
    }
```

## Notes

| Relationship | On delete | Reason |
| :--- | :--- | :--- |
| `Membership.organization` / `Membership.user` | CASCADE | membership is meaningless without either side |
| `Customer.organization` / `Order.organization` / `Invoice.organization` | CASCADE | tenant ownership |
| `Order.customer` / `Invoice.customer` | PROTECT | keep transactional history; delete the customer's orders/invoices first |
| `Invoice.order` | SET NULL | an invoice outlives the order it was raised from |

- `(organization, invoice_number)` is unique; `invoice_number` is auto-assigned
  when blank.
- Check constraints: `total_amount >= 0`, status ∈ the model's choices,
  `due_date IS NULL OR due_date >= issue_date`, `name`/`invoice_number` non-empty.
- Org-first composite indexes on the list/filter paths
  (`(organization, -created_at)`, `(organization, status)`, `(organization, customer)`).
- Every model has `created_at` / `updated_at` (`TimestampedModel`); the
  business models also have `created_by` (`AuthoredModel`, `SET_NULL`).

See [ADR 003 — Multi-tenancy](../adr/003-multi-tenancy.md).
