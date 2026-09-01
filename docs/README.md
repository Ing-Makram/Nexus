# NEXUS — Documentation (`/docs`)

Technical documentation for NEXUS: architectural decisions, API contracts, the
data model, and operational runbooks.

```
docs/
├── adr/         Architecture Decision Records (context → decision → consequences)
├── api/         REST API contracts, one Markdown file per resource group
├── schemas/     data model overview
└── runbooks/    operational procedures (production deployment, troubleshooting)
```

## Conventions

- **Markdown, GitHub-flavored** — readable directly in the repo.
- **ADRs** capture decisions already made. Files are `NNN-kebab-title.md`
  (`001`, `002`, …); superseded ADRs are kept and marked, not deleted. New
  decisions get the next number and follow **Context → Decision → Consequences**.
- **API docs** describe the actual endpoints (method, auth, request/response,
  status codes). Keep them in sync with the serializers/viewsets in the same PR.
- Update the relevant doc in the **same change** that alters the behaviour it
  describes.
