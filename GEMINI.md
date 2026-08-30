# ==============================================================================
# NEXUS - Engineering Guidelines (GEMINI.md)
# ==============================================================================
# This document defines the architectural guidelines, engineering standards,
# and developer workflows for the NEXUS platform. All engineers and AI
# agents MUST strictly adhere to these rules.

## Core Mandates

### 1. Follow the Documented Architecture
- Always adhere to the established monorepo structure and service boundaries.
- The frontend (React/TypeScript/Vite) and backend (Django REST Framework) must interact strictly via well-documented REST APIs.
- Core business logic must be isolated in the backend services. The frontend is primarily a presentation and user-interaction layer.

### 2. Do Not Introduce Technologies Without Justification
- Our core tech stack is:
  - **Frontend:** React + TypeScript + Vite + Vanilla CSS
  - **Backend:** Python + Django + Django REST Framework
  - **Database:** PostgreSQL
  - **Caching/Queuing:** Redis + Celery
  - **Infrastructure:** Docker & Docker Compose
  - **AI Integration:** Google Gemini API
- Do not add packages, libraries, databases, or frameworks (e.g., Tailwind, NestJS, MongoDB) without explicit justification and design review.

### 3. Do Not Modify Unrelated Code
- Keep pull requests and changesets scoped, surgical, and modular.
- Do not make stylistic or architectural modifications to code outside the scope of your assigned task.
- Refactorings should be handled in isolated, separate commits or pull requests specifically dedicated to that refactoring.

### 4. Prefer Clean, Maintainable Code
- Adhere to language-specific best practices:
  - **Python:** Follow PEP 8 guidelines, use type hints, and ensure modular app structures in Django.
  - **TypeScript/React:** Prefer functional components, custom hooks for stateful/effectful logic, strict TypeScript typing (avoid `any`), and descriptive naming conventions.
- Keep functions and methods focused on single responsibilities (Single Responsibility Principle).

### 5. Never Hardcode Secrets
- Under no circumstances should passwords, API keys, credentials, or cryptographic keys be hardcoded in any file.
- All configuration and secrets must be loaded dynamically via environment variables using `.env` files.
- Ensure any new secret is registered in `.env.example`.

### 6. Write Tests for Important Functionality
- Code modifications are considered incomplete without corresponding unit, integration, or end-to-end tests.
- **Backend:** Write Django unit/integration tests for models, serialisers, views, and Celery tasks. Aim for high test coverage of critical workflows.
- **Frontend:** Write component and utility unit tests using standard testing frameworks (e.g., Vitest + React Testing Library).

### 7. Update Documentation When Architecture Changes
- Always keep the files in `/docs`, as well as `README.md` and this `GEMINI.md`, fully updated when interfaces, contracts, schemas, or architectures change.
- Stale documentation is an engineering debt; update it immediately as part of your branch lifecycle.

---

## Workspace Workflows

### Branching and Committing
- **Branch Naming:** Use structural prefixes (e.g., `feat/`, `fix/`, `docs/`, `chore/`) followed by descriptive kebab-case descriptions (e.g., `feat/monorepo-scaffolding`).
- **Commit Messages:** Follow the conventional commits standard:
  - `feat: add database schema support for orders`
  - `fix: resolve race condition in celery queue initialization`
  - `docs: update gemini rules for local testing`
- **Surgical Changes:** Avoid staging unnecessary or transient files. Use `git add` for targeted files rather than bulk additions.

### AI and Agent Assistance
- When operating in the NEXUS workspace, AI agents must run validation workflows (e.g., linter checks, test suite executions) to prove correctness before concluding their work.
- If an agent makes structural or foundational shifts, it must first write its plan in `docs/` and seek confirmation from the lead developer.

---

## Tooling Reference

| Area | Tool | Validation commands |
| :--- | :--- | :--- |
| Backend lint / format | **Ruff** (replaces Black + Flake8 + isort) | `cd backend && ruff check . && ruff format --check .` |
| Backend tests | **pytest** + **pytest-django** | `cd backend && pytest` |
| Backend framework check | Django | `cd backend && python manage.py check` |
| Frontend lint | **ESLint** (flat config) | `cd frontend && npm run lint` |
| Frontend format | **Prettier** | `cd frontend && npm run format:check` |
| Frontend types | **TypeScript** (strict mode) | `cd frontend && npm run typecheck` |
| Frontend tests | **Vitest** + **React Testing Library** | `cd frontend && npm run test:run` |
| Frontend build | Vite | `cd frontend && npm run build` |
| Full local stack | Docker Compose | `docker compose config && docker compose up` |

Configuration lives in `backend/pyproject.toml` (Ruff + pytest),
`frontend/eslint.config.js`, `frontend/.prettierrc.json`, and
`frontend/tsconfig.*.json`.
