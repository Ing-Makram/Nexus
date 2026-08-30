# NEXUS - Backend Workspace (`/backend`)

This directory houses the backend server logic, API endpoints, database operations, and asynchronous queues powering the NEXUS SaaS platform. Built on **Python**, **Django**, and **Django REST Framework (DRF)**.

## Core Architecture Design

The backend acts as a highly structured API-only application. It does not render HTML templates; it strictly consumes and produces standardized JSON formats.

- **Routing and APIs:** Managed via Django REST Framework (DRF) serializers, viewsets, and custom routers.
- **Database Engine:** PostgreSQL mapped via Django's secure Object-Relational Mapper (ORM).
- **Background Jobs:** Long-running analytics, document indexing, and Google Gemini API requests are deferred to **Celery workers** backed by a **Redis** message broker.

---

## Directory Structure

To maintain a clean and modular Django project, we avoid putting all logic into a single folder. We group models, serializers, and operations into dedicated Django apps under the root backend.

```
backend/
├── README.md               # Backend overview (this file)
├── requirements.txt        # Python pip dependencies
├── pyproject.toml          # Ruff (lint + format) and pytest configuration
├── manage.py               # Django CLI management script
├── config/                 # Central project configuration and main URL entry
│   ├── __init__.py         # Loads the Celery app on Django startup
│   ├── settings/           # Split settings package
│   │   ├── base.py         # Shared settings (loads from env variables)
│   │   ├── development.py   # Local development overrides
│   │   └── production.py    # Production overrides
│   ├── urls.py             # Root URL router (currently: /api/health/)
│   ├── celery.py           # Celery application definition
│   └── wsgi.py             # WSGI entrypoint for web server
├── apps/                   # Custom business domains (added as they are implemented)
└── tests/                  # Cross-cutting infrastructure / smoke tests
```

> Planned business apps (not yet implemented): `authentication/`, `customers/`,
> `orders/`, `inventory/`, `ai_engine/`. They will be added under `apps/` and
> registered in `config/settings/base.py` as work reaches each roadmap phase.

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

## Development & Code Quality Guidelines

1. **Surgical Migrations:** Never alter migration files manually. Always use Django's command tools (`makemigrations`, `migrate`) and verify generated Python code before executing.
2. **Model Fatness:** Keep views lean and serializers focused. Place core domain actions and business mutations directly on the Django Models or in dedicated service layer modules.
3. **Strict Python Typing:** Utilize type-hinting for all custom helper functions, service classes, and utility layers.
4. **Unit Testing:** Maintain independent unit test classes inside each custom app (`apps/[app_name]/tests/`). Mock out-of-process services (e.g. Redis, Mail servers, and especially the Google Gemini API).
