# Runbook — Production deployment

NEXUS production runtime + observability. Covers the Docker-based stack:
PostgreSQL + Gunicorn/Django + an nginx reverse proxy that also serves the
built React SPA, plus request-ID propagation, structured logging, optional
Sentry, and the CI/local production verification.

```
          client
            │  HTTP/HTTPS   (TLS terminated by an upstream LB / ingress)
            ▼
   ┌──────────────────┐   docker-compose.prod.yml : proxy
   │  nginx (proxy)   │   • serves /            → React SPA  (try_files → index.html)
   │                  │   • proxies /api /admin /static /health → backend:8000
   └────────┬─────────┘
            │  HTTP (compose network only)
            ▼
   ┌──────────────────┐   docker-compose.prod.yml : backend
   │ Gunicorn (sync)  │   backend/Dockerfile + gunicorn.conf.py
   │   → Django       │   entrypoint: wait-for-db → migrate → collectstatic → gunicorn
   │   + WhiteNoise   │   /health/  /health/ready/
   └────────┬─────────┘
            │  TCP 5432 (compose network only)
            ▼
   ┌──────────────────┐   docker-compose.prod.yml : db
   │  PostgreSQL 16   │   named volume: postgres_data_prod
   └──────────────────┘
```

Redis / Celery are **not** part of the production stack — there are no
background tasks yet. Add them in a later milestone if and when a task exists.

---

## 1. Prerequisites

- Docker Engine + Compose v2 on the host.
- A `.env` file at the repo root (copy `.env.example`, fill real values). It is
  gitignored — never commit it.
- TLS terminated in front of the `proxy` container by your load balancer /
  ingress, which must forward `X-Forwarded-Proto`.

## 2. Required environment variables

Startup **fails fast** if a required variable is missing.

| Variable | Required | Notes |
| :--- | :--- | :--- |
| `ENVIRONMENT` | yes | must be `production` (compose sets it) |
| `SECRET_KEY` | yes | long random value; no fallback in production |
| `ALLOWED_HOSTS` | yes | comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | recommended | full origins, e.g. `https://app.example.com` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | yes | `DB_ENGINE`/`DB_HOST`/`DB_PORT` are set by compose |
| `CONN_MAX_AGE` | no | default `60` |
| `SECURE_SSL_REDIRECT` | no | default `true`; keep it on behind TLS |
| `SECURE_HSTS_SECONDS` | no | default `31536000` |
| `LOG_LEVEL` | no | default `INFO` |
| `PROXY_PORT` | no | host port for nginx (default `8080`) |
| `GUNICORN_WORKERS` | no | default `(2 × CPU) + 1` |
| `GUNICORN_TIMEOUT` | no | default `30` |
| `RUN_MIGRATIONS` | no | default `true` — run `migrate` on container start |
| `RUN_COLLECTSTATIC` | no | default `true` — run `collectstatic` on container start |
| `VITE_API_URL` | no | baked into the SPA at build time; default `/api/v1` (same origin) |
| `LOG_LEVEL` | no | default `INFO` |
| `LOG_FORMAT` | no | `json` (production default) or `plain` |
| `SENTRY_DSN` | no | **absent → Sentry is off**; set to enable error monitoring |
| `SENTRY_ENVIRONMENT` | no | default `production` |
| `SENTRY_RELEASE` | no | git SHA / version tag, for release health |
| `SENTRY_TRACES_SAMPLE_RATE` | no | default `0` (tracing disabled) |

## 3. Start / update the stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Startup order (handled automatically):

1. `db` starts, becomes healthy (`pg_isready`).
2. `backend` starts → entrypoint waits for the DB, runs `migrate --noinput`,
   runs `collectstatic --noinput`, then `exec`s Gunicorn. Becomes healthy once
   `GET /health/` returns 200.
3. `proxy` starts once `backend` is healthy.

To roll out new code: re-run the command above. `backend` re-runs migrations and
collectstatic on recreate.

## 4. Verify

```bash
curl -fsS http://localhost:${PROXY_PORT:-8080}/health/          # {"status": "alive"}
curl -fsS http://localhost:${PROXY_PORT:-8080}/health/ready/    # {"status": "ready"}
curl -fsS http://localhost:${PROXY_PORT:-8080}/api/health/      # existing app health
curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:${PROXY_PORT:-8080}/   # 200 (SPA)
docker compose -f docker-compose.prod.yml ps                    # all "healthy"
```

## 5. Migrations

- Applied automatically on `backend` start (`RUN_MIGRATIONS=true`).
- Manual: `docker compose -f docker-compose.prod.yml exec backend python manage.py migrate`
- Set `RUN_MIGRATIONS=false` to take control (e.g. run migrations as a separate
  step in a blue/green rollout).

## 6. Static files

- Collected on `backend` start into `/app/staticfiles` and served by WhiteNoise.
- Manual: `docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput`

## 7. Observability

### Logs

```bash
docker compose -f docker-compose.prod.yml logs -f backend   # Django + Gunicorn (access + error)
docker compose -f docker-compose.prod.yml logs -f proxy     # nginx access log (JSON)
```

All logs go to stdout/stderr — collect them with your container runtime /
platform log driver. No log files are written inside the containers.

In production (`LOG_FORMAT=json`, the default) each Django log line is a single
JSON object: `timestamp`, `level`, `logger`, `message`, `request_id` (when in a
request), plus `method` / `path` / `status` for `django.request` errors. It
**never** contains cookies, `Authorization`, JWTs, or request bodies. Set
`LOG_FORMAT=plain` for human-readable local debugging.

### Request / correlation ID (`X-Request-ID`)

Every request is tagged with an ID that flows the whole chain:

```
client ──X-Request-ID?──▶ nginx ──▶ Gunicorn ──▶ Django ──▶ logs
             (reuse if present, else nginx `$request_id`)      (request_id field)
```

- Django (`apps.common.observability.RequestIDMiddleware`) preserves a valid
  inbound `X-Request-ID` (`[A-Za-z0-9._-]`, ≤128 chars) or generates a UUID hex.
- The ID is on `request.request_id`, in every log record, in the Gunicorn access
  log (`request_id=…`), and on the **response** `X-Request-ID` header.
- To trace one request end-to-end: grab `X-Request-ID` from the response (or the
  client) and `grep` it across the `proxy` and `backend` logs.

### Error monitoring (Sentry) — optional

Sentry is **off unless `SENTRY_DSN` is set**; production boots identically
without it. When enabled:

- DSN and all tuning come from the environment (`SENTRY_*`) — nothing hardcoded.
- `send_default_pii=False` — no cookies, auth headers, client IP, or bodies.
- `/health/` and `/health/ready/` events/transactions are dropped (`before_send`).
- Readiness DB-outage is logged at `WARNING` (no traceback), so it is **not**
  captured as an application error. Expected `401/403/404` API responses are
  handled by DRF and are not reported.

## 8. Stop / restart / rollback

```bash
docker compose -f docker-compose.prod.yml stop           # stop, keep data
docker compose -f docker-compose.prod.yml start
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml down            # remove containers, KEEP the DB volume
docker compose -f docker-compose.prod.yml down -v         # also DROP the DB volume (destroys data)
```

Rollback = redeploy the previous image tag / commit. Reverse any migration
manually first if it is not backward-compatible.

## 9. Security notes

- No secrets in `Dockerfile`s or compose files — everything sensitive is in
  `.env` (gitignored) or your platform secret store.
- Containers run as a non-root user; `db` and `backend` publish **no** host
  ports — only `proxy` is reachable.
- `DEBUG=False` is forced by `config.settings.production`.
- Keep `SECURE_SSL_REDIRECT=true` and a non-zero `SECURE_HSTS_SECONDS` in real
  deployments; only lower them for local plain-HTTP testing.
- The reverse proxy must sit behind real TLS. This stack does **not** manage
  certificates.
- Rotate `SECRET_KEY` and DB credentials out of band; a `SECRET_KEY` rotation
  invalidates existing sessions and JWTs.

## 10. Production verification (CI + local)

CI (`.github/workflows/ci.yml`, job **`production-stack`**) proves the stack is
buildable and internally valid on every push/PR — no real services, no secrets,
no registry push, no deploy:

1. build `backend/Dockerfile` and `infrastructure/docker/frontend.prod.Dockerfile`;
2. `docker compose -f docker-compose.prod.yml config` (with dummy env);
3. `scripts/prod-smoke-test.sh` — starts the full stack with dummy values, waits
   for `db` + `backend` + `proxy` to become **healthy**, checks the endpoints
   below, verifies DB-down behaviour, then tears everything down (containers,
   volume, and locally-built images).

The `backend` job also runs `python manage.py check --deploy --fail-level WARNING`
under `config.settings.production` with a safe CI env — this must be **zero
warnings**, not just zero errors.

Run the same smoke test locally (needs Docker + Compose v2):

```bash
./scripts/prod-smoke-test.sh          # ~3 min; prints "SMOKE PASS" on success
```

Endpoints it asserts (through the nginx proxy):

| Path | Expected |
| :--- | :--- |
| `/health/` | `200` `{"status":"alive"}` |
| `/health/ready/` | `200` `{"status":"ready"}` (→ `503` while `db` is stopped) |
| `/api/health/` | `200` |
| `/` and `/x/deep-link` | `200` (SPA + client-route fallback) |
| `/static/admin/css/base.css` | `200` (WhiteNoise) |
| `/api/v1/orders/` | `401` (protected API stays unauthenticated) |
| any response | carries an `X-Request-ID` header |

## 11. When a deployment fails — what to inspect

1. **`docker compose -f docker-compose.prod.yml ps`** — which service is not
   `healthy`?
2. **`... logs backend`** — the entrypoint prints each step. Common stops:
   - `ImproperlyConfigured: The SECRET_KEY / ALLOWED_HOSTS environment variable
     must be set` → the required var is missing/empty in `.env`.
   - `database did not become available within 60s` → `db` unhealthy, wrong
     `DB_*`, or a stale `postgres_data_prod` volume with a different password
     (`down -v` to reset in non-prod).
   - migration or `collectstatic` traceback → fix forward; set
     `RUN_MIGRATIONS=false` to boot without migrating and investigate.
3. **`... logs proxy`** — `502` from nginx means Gunicorn isn't up yet / crashed;
   check the `backend` logs. `X-Forwarded-Proto` must be set by your TLS
   terminator or `SECURE_SSL_REDIRECT` will loop.
4. **`check --deploy`** locally with the real env
   (`docker compose ... run --rm backend python manage.py check --deploy`).
5. Grab the failing response's `X-Request-ID` and `grep` it across both logs.
6. If Sentry is enabled, the unhandled exception is there with the same
   `request_id` tag (health-check noise excluded).
