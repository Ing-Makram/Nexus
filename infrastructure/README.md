# NEXUS - Infrastructure Workspace (`/infrastructure`)

This workspace contains all configuration, orchestration, and provisioning tools necessary to run, scale, and monitor the NEXUS platform in local, staging, and production environments.

## Local Development Design

NEXUS uses **Docker Compose** for a fully-orchestrated local development experience. This guarantees absolute environment parity across developer machines (Mac, Linux, Windows).

### Orchestrated Containers & Roles:

| Service Name | Technology | Internal Port | Exposed Port | Role |
| :--- | :--- | :--- | :--- | :--- |
| `frontend` | Node/Vite (React) | `5173` | `5173` | UI Presentation layer |
| `backend` | Python/Django (DRF) | `8000` | `8000` | Core API layer |
| `db` | PostgreSQL | `5432` | `5432` | Relational DBMS |
| `redis` | Redis | `6379` | `6379` | Cache, Session Store, & Celery Message Broker |
| `celery_worker` | Celery Worker | N/A | N/A | Asynchronous task execution worker (uses Django environment) |

---

## Planned Directory Structure

Once fully implemented, the `/infrastructure` layout will be structured as follows:

```
infrastructure/
├── README.md                 # Infrastructure overview (this file)
├── docker/                   # Isolated Dockerfiles for services
│   ├── frontend.dev.Dockerfile   # implemented
│   ├── backend.dev.Dockerfile    # implemented
│   ├── frontend.prod.Dockerfile  # future
│   └── backend.prod.Dockerfile   # future
└── k8s/                      # Production Kubernetes manifests (future)
```

> The development orchestrator (`docker-compose.yml`) lives at the repository
> root, not under `infrastructure/`, so that build contexts resolve against the
> monorepo root.

## Security & Operational Policy

- **Environment Isolation:** Containers in the development orchestrator will strictly consume values injected via the root-level `.env` file. No production keys may be stored in any config or Dockerfiles.
- **Volume Persistences:** Local databases must be backed by a persistent Docker volume (`postgres_data`) to prevent data loss on container rebuilds. This volume is gitignored.
