# Contributing to NEXUS

NEXUS is a portfolio project, but it is developed to production standards. These
are the conventions the codebase follows; anything merged is expected to match
them.

## Core principles

### 1. Follow the documented architecture

- The frontend (React / TypeScript / Vite) and backend (Django REST Framework)
  interact **only** through the versioned REST API (`/api/v1/…`).
- Business logic, validation, authorization and tenant scoping live in the
  backend. The frontend is a presentation + interaction layer with no business
  logic.
- Backend layering is strict: `models → selectors → services → permissions →
  serializers → views`. `selectors.py` is the only place tenant scoping is
  expressed; `services.py` is the only write path; views stay thin.

### 2. Do not introduce technologies without justification

The stack is intentionally small:

| Layer | Technology |
| :--- | :--- |
| Frontend | React + TypeScript + Vite + plain CSS |
| Backend | Python + Django + Django REST Framework |
| Database | PostgreSQL |
| Auth | `djangorestframework-simplejwt` |
| CORS | `django-cors-headers` (dev cross-origin: Vite → API) |
| Static files | WhiteNoise |
| App server / proxy | Gunicorn + nginx |
| Containers | Docker + Docker Compose |

New dependencies, databases or frameworks require explicit justification in the
PR description (and, for anything structural, an ADR under `docs/adr/`). Redis
and Celery are present in the **development** Compose file as scaffolding for
future background work — they run no application tasks today and are absent from
the production stack.

### 3. Keep changes scoped

- One concern per branch / PR. No drive-by refactors or unrelated style changes.
- Dedicated refactoring goes in its own PR.

### 4. Prefer clean, maintainable code

- **Python:** PEP 8 (enforced by Ruff), type hints on service/selector/helper
  signatures, single-responsibility functions.
- **TypeScript/React:** functional components, custom hooks for stateful logic,
  strict typing (no `any`), descriptive names.

### 5. Never hardcode secrets

- No passwords, API keys, tokens or cryptographic keys in any tracked file.
- All configuration comes from environment variables; every variable is listed
  in `.env.example` with a placeholder value.
- `config.settings.production` refuses to start if a required secret is missing.

### 6. Test every change

- **Backend:** pytest + pytest-django for models, selectors, services,
  serializers, permissions and views. Test permissions and tenant isolation as
  explicit properties.
- **Frontend:** Vitest + React Testing Library for user-visible behaviour
  (states, role-aware UI, exact request parameters) — not implementation detail.

### 7. Keep documentation in sync

Update `README.md`, the workspace READMEs, `docs/api/*` and `docs/adr/*` in the
same PR that changes the behaviour they describe. Stale documentation is a bug.

## Workflow

### Branch names

`feat/…`, `fix/…`, `docs/…`, `chore/…`, `refactor/…`, kebab-case description.

### Commit messages — Conventional Commits

```
feat: add customer search to the customers provider
fix: reset the invoice status filter on organization switch
docs: correct the backend README app inventory
```

### Before opening a PR

Run the full local suite (identical to CI):

```bash
# backend
cd backend
ruff check . && ruff format --check .
python manage.py check
python manage.py check --deploy --fail-level WARNING   # production settings, safe env
python manage.py makemigrations --check
pytest

# frontend
cd frontend
npm run lint && npm run format:check && npm run typecheck
npm run test:run
npm run build

# production stack (if infra files changed)
docker compose -f docker-compose.prod.yml config
./scripts/prod-smoke-test.sh
```

### Migrations

Never edit a migration file by hand. Use `makemigrations` / `migrate`, review
the generated file, and run `makemigrations --check` before pushing. Do not
delete historical migrations.

## Tooling reference

| Area | Tool | Command (from the workspace dir) |
| :--- | :--- | :--- |
| Backend lint / format | Ruff | `ruff check . && ruff format --check .` |
| Backend tests | pytest + pytest-django | `pytest` |
| Backend framework checks | Django | `python manage.py check` |
| Frontend lint | ESLint (flat config) | `npm run lint` |
| Frontend format | Prettier | `npm run format:check` |
| Frontend types | TypeScript (strict) | `npm run typecheck` |
| Frontend tests | Vitest + RTL | `npm run test:run` |
| Frontend build | Vite | `npm run build` |

Configuration: `backend/pyproject.toml` (Ruff + pytest), `frontend/eslint.config.js`,
`frontend/.prettierrc.json`, `frontend/tsconfig.*.json`.
