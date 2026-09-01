# NEXUS — Backend (`/backend`)

The API-only Django application powering NEXUS: authentication, multi-tenant
organizations, and the customers / orders / invoices domain. Built on **Python
3.12**, **Django 5**, and **Django REST Framework**.

## Core architecture

The backend renders no HTML — it consumes and produces JSON only.

- **APIs:** DRF viewsets + routers under `/api/v1/`.
- **Database:** PostgreSQL via the Django ORM (SQLite for the test suite).
- **Layering:** every app follows `models → selectors → services → permissions →
  serializers → views` (see *App layering* below).
- **Background jobs:** none yet. `config/celery.py` and the dev `celery_worker`
  container are scaffolding — no application tasks are defined
  (`docs/adr/005-future-microservices.md`). The production stack does not run
  Celery or Redis.

---

## Directory Structure

To maintain a clean and modular Django project, we avoid putting all logic into a single folder. We group models, serializers, and operations into dedicated Django apps under the root backend.

```
backend/
├── Dockerfile              # production image (Gunicorn, non-root)
├── docker-entrypoint.sh    # wait-for-db → migrate → collectstatic → gunicorn
├── gunicorn.conf.py        # production Gunicorn config (env-driven)
├── manage.py
├── pyproject.toml          # Ruff + pytest configuration
├── requirements.txt
├── config/
│   ├── __init__.py         # loads the Celery app on Django startup
│   ├── settings/
│   │   ├── __init__.py     # resolve_settings_module() — entrypoint settings strategy
│   │   ├── base.py         # shared settings (env-driven)
│   │   ├── development.py   # local development overrides
│   │   ├── test.py         # pytest-only overrides (fast password hasher)
│   │   └── production.py    # fail-fast, HTTPS/HSTS/secure cookies, WhiteNoise, JSON logs
│   ├── urls.py             # /health/, /health/ready/, /api/health/, /api/v1/*, /admin/
│   ├── health.py           # liveness / readiness probe views
│   ├── celery.py           # Celery app (scaffold — no tasks)
│   ├── wsgi.py  /  asgi.py  # server entrypoints
├── apps/
│   ├── common/             # abstract TimestampedModel / AuthoredModel; RequestID middleware,
│   │                       #   JSON log formatter (observability.py)
│   ├── accounts/           # email-based User model + JWT auth (register/login/refresh/logout/me)
│   ├── organizations/      # Organization + Membership + roles + nested members API
│   ├── customers/          # Customer CRUD
│   ├── orders/             # Order CRUD (+ status filter)
│   ├── invoices/           # Invoice CRUD (+ auto-numbering, `mark_overdue_invoices` command)
│   └── dashboard/          # read-only aggregation endpoint (no model)
└── tests/                  # cross-cutting: health, settings, request-id, logging, docker
```

### App layering

Every business app follows the same shape:

| Module | Responsibility |
| :--- | :--- |
| `models.py` | schema + DB constraints/indexes only |
| `selectors.py` | read queries — **the only place tenant scoping is expressed** |
| `services.py` | write operations / multi-step business transactions |
| `permissions.py` | reusable DRF object-permission classes (role checks) |
| `serializers.py` | I/O shape + field-level validation |
| `views.py` | thin viewsets wiring the above together |

## Configuration & environments

Settings are a split package. The active module is chosen like this (identical
logic in `manage.py` and in `config/settings/__init__.py:resolve_settings_module`,
which `wsgi.py`, `asgi.py` and `celery.py` all use):

1. an explicit `DJANGO_SETTINGS_MODULE` always wins (pytest sets it to
   `config.settings.test` in `pyproject.toml`);
2. otherwise `ENVIRONMENT=production` → `config.settings.production`;
3. anything else, including an unset `ENVIRONMENT` → `config.settings.development`.

With no env vars set, `manage.py` and the dev containers use development
settings; production requires `ENVIRONMENT=production` (the prod Compose file
sets it).

**Production** (`ENVIRONMENT=production`) is fully environment-driven and fails
fast — a missing required variable raises `ImproperlyConfigured` at startup
instead of booting with insecure defaults:

| Variable | Required | Purpose |
| :--- | :--- | :--- |
| `SECRET_KEY` | **yes** | no dev fallback in production |
| `ALLOWED_HOSTS` | **yes** | comma-separated; the dev default is rejected |
| `CSRF_TRUSTED_ORIGINS` | no | comma-separated full origins (`https://app.example.com`) |
| `CONN_MAX_AGE` | no | persistent DB connections, seconds (default `60`) |
| `SECURE_SSL_REDIRECT` | no | default `true`; set `false` only if TLS is enforced upstream |
| `SECURE_HSTS_SECONDS` | no | default `31536000` (1 year) |
| `LOG_LEVEL` | no | root/`django` log level (default `INFO`) |
| `LOG_FORMAT` | no | `json` (production default) or `plain` |
| `SENTRY_DSN` | no | absent → Sentry off; set to enable error monitoring (`SENTRY_ENVIRONMENT` / `SENTRY_RELEASE` / `SENTRY_TRACES_SAMPLE_RATE` tune it) |

Production also enables, unconditionally: `SECURE_PROXY_SSL_HEADER`
(`X-Forwarded-Proto`), HSTS incl. subdomains + preload, secure/HttpOnly session
cookies, secure CSRF cookies, `SECURE_CONTENT_TYPE_NOSNIFF`,
`X_FRAME_OPTIONS = "DENY"`, and WhiteNoise static serving. The `/health/` probes
are exempt from the HTTPS redirect so load-balancer checks can use plain HTTP.
`python manage.py check --deploy --fail-level WARNING` is clean with a valid
production env (CI runs it on every push).

## Observability

- **`X-Request-ID`** — `apps.common.observability.RequestIDMiddleware` (first in
  `MIDDLEWARE`) preserves a valid inbound `X-Request-ID` or generates a UUID hex,
  exposes it on `request.request_id` + every log record + the response header.
  nginx generates one upstream when the client sends none.
- **Structured logs** — production emits one JSON object per line
  (`timestamp`, `level`, `logger`, `message`, `request_id`, plus
  `method`/`path`/`status` for `django.request`). Never logs cookies, auth
  headers, tokens, or bodies. `LOG_FORMAT=plain` for local debugging.
- **Sentry** — optional; only initialises when `SENTRY_DSN` is set. Drops
  `/health/` noise, `send_default_pii=False`, readiness DB-outage logged at
  WARNING (not captured).

See [`docs/runbooks/production-deployment.md`](../docs/runbooks/production-deployment.md)
§7 and §10–11, and `scripts/prod-smoke-test.sh` for full-stack verification.

## Production runtime

The backend ships as a container (`backend/Dockerfile`): **Gunicorn only, never
`runserver`**. Logging goes to stdout/stderr (no log files).

| Piece | File | Notes |
| :--- | :--- | :--- |
| Gunicorn config | `gunicorn.conf.py` | binds `0.0.0.0:8000`; env-driven `GUNICORN_WORKERS` (default `2·CPU+1`), `GUNICORN_TIMEOUT` (30s), graceful shutdown, worker recycling |
| Startup | `docker-entrypoint.sh` | wait for DB → `migrate --noinput` → `collectstatic --noinput` → `exec gunicorn`. `set -e` — any step failing aborts the boot. Toggle with `RUN_MIGRATIONS` / `RUN_COLLECTSTATIC` |
| Static files | WhiteNoise | `STATIC_ROOT=backend/staticfiles`; `CompressedManifestStaticFilesStorage`. Verify: `ENVIRONMENT=production … python manage.py collectstatic --noinput` |
| Probes | `config/health.py` | `GET /health/` (liveness, no DB), `GET /health/ready/` (readiness — DB `SELECT 1`, `503` when the DB is down; logged at WARNING, no traceback). Both public, no secrets in the body |
| Verification | `scripts/prod-smoke-test.sh` | builds + starts the full prod stack, waits for health, checks endpoints + DB-down behaviour, tears down. Runs in CI (`production-stack` job). |

Full stack (`db` + Gunicorn `backend` + nginx `proxy` serving the built SPA):

```bash
cp .env.example .env          # set real production values
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml down          # stop  (add -v to drop the DB volume)
```

See [`docs/runbooks/production-deployment.md`](../docs/runbooks/production-deployment.md).

## Authentication

- Custom user model `accounts.User` (`AUTH_USER_MODEL`); **email is the login
  identifier**, there is no username.
- JWT via `djangorestframework-simplejwt`. DRF defaults to
  `JWTAuthentication` + `IsAuthenticated` (`config/settings/base.py`); public
  endpoints opt out with `permission_classes = [AllowAny]`.
- Access token 15 min, refresh token 1 day (`SIMPLE_JWT`).

| Method | Path | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| POST | `/api/v1/auth/register/` | none | email + password (+ optional names) → `{access, refresh, user}`; password run through Django validators |
| POST | `/api/v1/auth/login/` | none | email + password → `{access, refresh, user}` |
| POST | `/api/v1/auth/refresh/` | none | `{refresh}` → `{access}` |
| POST | `/api/v1/auth/logout/` | Bearer | `{refresh}` → `205`; blacklists the refresh token |
| GET | `/api/v1/auth/me/` | Bearer | current user |

See [`docs/api/auth.md`](../docs/api/auth.md) for request/response detail.

## Organizations & multi-tenancy

- `Organization` + `Membership` (M2M through-model) with roles `owner` / `admin`
  / `member`. A user may belong to many organizations; `(organization, user)` is
  unique so a membership has exactly one role.
- **Tenant isolation** is enforced in the API, not the client:
  `OrganizationViewSet.get_queryset()` only ever returns
  `organizations_for_user(request.user)`, so any request touching another
  tenant's organization returns **404** (existence is never disclosed).
  Object-level permissions add role checks on top.
- Creating an organization makes the creator its `owner` (atomic, in
  `services.create_organization`).

| Method | Path | Who |
| :--- | :--- | :--- |
| POST | `/api/v1/organizations/` | any authenticated user (becomes owner) |
| GET | `/api/v1/organizations/` | lists only the caller's organizations |
| GET | `/api/v1/organizations/{id}/` | members |
| PATCH | `/api/v1/organizations/{id}/` | owner or admin |
| DELETE | `/api/v1/organizations/{id}/` | owner only |

See [`docs/api/organizations.md`](../docs/api/organizations.md) for detail.

## Customers · Orders · Invoices

All three are `ModelViewSet`s at `/api/v1/{customers,orders,invoices}/`, scoped
to the caller's organizations through the app's `*_for_user` selector
(cross-tenant → **404**). Any member reads; owners and admins write. Writes go
through the service layer.

| Resource | List filters | Notable rules |
| :--- | :--- | :--- |
| Customers | `?organization=` | name required; email validated |
| Orders | `?organization=`, `?status=` | `customer` must be in the same organization; status ∈ draft/pending/confirmed/cancelled/completed |
| Invoices | `?organization=`, `?status=` | `invoice_number` auto-assigned + unique per organization; `customer`/`order` must be same-org; `due_date ≥ issue_date`; status ∈ draft/sent/paid/overdue/void |

Full request/response detail:
[`customers.md`](../docs/api/customers.md) ·
[`orders.md`](../docs/api/orders.md) ·
[`invoices.md`](../docs/api/invoices.md).

`apps/invoices` also provides `python manage.py mark_overdue_invoices`, which
moves past-due `sent` invoices to `overdue`.

## Dashboard

`apps/dashboard` is a **read-only** aggregation app — no model, no migration, no
service layer. `selectors.dashboard_stats` builds every queryset from the
existing per-app `*_for_user` selectors, so tenant isolation is inherited.

| Method | Path | Notes |
| :--- | :--- | :--- |
| GET | `/api/v1/dashboard/?organization=<id>` | any member of the org; `400` if the param is missing, `404` if the caller isn't a member |

Returns counts (customers, orders, invoices), invoice totals
(`total_amount` excl. void / `paid_amount` / `outstanding_amount` = sent+overdue
/ `overdue_count`), `by_status` breakdowns, and the 5 most recent orders /
invoices (customer **name** only — no emails, ids of related rows, or other PII).

## Tooling

| Purpose | Tool | Command (run from `backend/`) |
| :--- | :--- | :--- |
| Lint | Ruff | `ruff check .` |
| Format | Ruff | `ruff format .` |
| Tests | pytest + pytest-django | `pytest` |
| Django checks | Django | `python manage.py check` |

Ruff replaces the previous Black + Flake8 + isort combination; all three rule
sets (formatting, pycodestyle/pyflakes, import sorting) are configured in
`pyproject.toml`.

Tests run against SQLite with a fast password hasher
(`config/settings/test.py`, selected by `DJANGO_SETTINGS_MODULE` in
`pyproject.toml`) — the full suite is a couple of seconds.

### Running management commands against the Docker Postgres

`makemigrations` / `migrate` / `shell` connect to the database. Run them
**inside the container** so they use the Linux/UTF-8 environment:

```bash
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

Running them on the host against the Docker Postgres can raise a
`UnicodeDecodeError` (psycopg2 fails to decode a libpq error message under a
non-UTF-8 Windows locale). If host access shows *"password authentication
failed"*, the `nexus_postgres_data` volume was initialised with a different
password than the current `.env`; recreate it with `docker compose down -v`
(this **wipes local data**) then `docker compose up -d`.

## Development & Code Quality Guidelines

1. **Surgical Migrations:** Never alter migration files manually. Always use Django's command tools (`makemigrations`, `migrate`) and verify generated Python code before executing.
2. **Model Fatness:** Keep views lean and serializers focused. Place core domain actions and business mutations directly on the Django Models or in dedicated service layer modules.
3. **Strict Python Typing:** Utilize type-hinting for all custom helper functions, service classes, and utility layers.
4. **Testing:** Each app keeps its own tests in `apps/<app>/tests/`
   (`test_models.py`, `test_selectors.py`, `test_services.py`, `test_api.py` as
   applicable). Cross-cutting infrastructure tests live in `backend/tests/`.
   Permissions and tenant isolation are tested as explicit properties.
