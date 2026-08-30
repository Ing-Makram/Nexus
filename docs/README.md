# NEXUS - Documentation Root (`/docs`)

This directory houses all technical specifications, system design schemas, Architectural Decision Records (ADRs), and runbooks for the NEXUS platform. Keeping this documentation up-to-date is a core engineering mandate.

## Directory Layout

```
docs/
├── README.md               # Overview of documentation (this file)
├── adr/                    # Architectural Decision Records (ADRs)
├── api/                    # OpenAPI specifications and REST API contracts
├── schemas/                # Relational database schemas and state flow charts
└── runbooks/               # Infrastructure provisioning and operational guides
```

## Documentation Standards

All engineering plans, updates, and reviews must align with these standards:

1. **Keep it Markdown-native:** Use standard GitHub-flavored Markdown for readability and accessibility directly within the codebase.
2. **Co-locate with Code:** When adding massive features, write the technical specification first in `/docs` and link it in the pull request.
3. **Use ADRs for Decisions:** When changing database engine patterns, state-machines, or routing strategies, create an ADR file under `docs/adr/XXXX-title.md` (where `XXXX` is a sequential ID like `0001`).
4. **API First Development:** Define expected API schemas (endpoints, payload structures, response statuses) before writing any frontend or backend code. Use the `docs/api` folder for mock JSON schemas.
