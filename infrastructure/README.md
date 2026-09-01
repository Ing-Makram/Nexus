# NEXUS - Infrastructure Workspace (`/infrastructure`)

This workspace contains all configuration, orchestration, and provisioning tools necessary to run, scale, and monitor the NEXUS platform in local, staging, and production environments.

## Local Development Design

NEXUS uses **Docker Compose** for a fully-orchestrated local development experience. This guarantees absolute environment parity across developer machines (Mac, Linux, Windows).

### Orchestrated Containers & Roles:

| Service Name | Technology | Internal Port | Exposed Port | Role |
| :--- | :--- | :--- | :--- | :--- |
| `frontend` | Node/Vite (React) | `5173` | `5173` | UI Presentation layer |
| `backend` | Python/Django (DRF) | `8000` | `8000` | Core API layer |
| `db` | PostgreSQL 16 | `5432` | `5432` | Relational database |
| `redis` | Redis 7 | `6379` | `6379` | Celery broker (scaffold — no tasks run) |
| `celery_worker` | Celery worker | — | — | Scaffold — defines no application tasks |

---

## Directory layout

```
infrastructure/
└── docker/
    ├── backend.dev.Dockerfile     # dev: Django runserver (hot reload)
    ├── frontend.dev.Dockerfile    # dev: Vite dev server
    ├── frontend.prod.Dockerfile   # prod: multi-stage Node build → nginx (SPA + reverse proxy)
    └── nginx.prod.conf            # prod: nginx reverse-proxy + SPA config
```

> The **production backend image** lives at `backend/Dockerfile` (build context =
> `backend/`), not under `infrastructure/`, alongside `backend/gunicorn.conf.py`
> and `backend/docker-entrypoint.sh`.

## Production orchestrator

`docker-compose.prod.yml` (repo root) runs the production stack:

| Service | Image / build | Role |
| :--- | :--- | :--- |
| `db` | `postgres:16-alpine` | database, named volume `postgres_data_prod`, no host port |
| `backend` | `backend/Dockerfile` | Gunicorn → Django (+ WhiteNoise static), no host port |
| `proxy` | `infrastructure/docker/frontend.prod.Dockerfile` | nginx: serves built SPA, reverse-proxies the API; the only service with a published port (`PROXY_PORT`, default 8080) |

No `redis` / `celery_worker` — there are no background tasks yet. TLS is expected
to be terminated by an upstream load balancer. See
[`docs/runbooks/production-deployment.md`](../docs/runbooks/production-deployment.md).

> The development orchestrator (`docker-compose.yml`) lives at the repository
> root, not under `infrastructure/`, so that build contexts resolve against the
> monorepo root.

## Security & operational policy

- **No secrets in tracked files.** Containers read configuration from the
  root-level `.env` (gitignored) in development, and from the deployment
  environment in production. The `:-` defaults in the Compose files are
  throwaway local values.
- **Persistent data.** Postgres data lives in a named Docker volume
  (`postgres_data` in dev, `postgres_data_prod` in prod) so container rebuilds
  don't lose it. `down -v` removes it.
- **Production containers run as a non-root user**; only the `proxy` publishes a
  host port.
