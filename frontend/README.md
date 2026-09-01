# NEXUS — Frontend (`/frontend`)

React + TypeScript + Vite single-page app for the NEXUS platform. It is a thin
presentation layer over the Django REST API (`/api/v1/…`); all business logic
and tenant scoping live in the backend.

## Stack

- **React 19** + **TypeScript** (strict mode)
- **Vite** for dev server / build
- **ESLint** (flat config) + **Prettier**
- **Vitest** + **React Testing Library**
- No router and no state-management library — routing is a small
  auth/organization gate hierarchy, state is React context per feature.

## Architecture

Each feature module follows the same shape (see `src/customers/`, `src/orders/`,
`src/invoices/`):

```
src/
├── api/<feature>.ts          # typed fetch calls via AuthorizedRequest
├── <feature>/context.ts      # React context + value type
├── <feature>/<Feature>Provider.tsx
├── <feature>/use<Feature>.ts # context hook
├── components/<Feature>*.tsx  # List / Form / Manager
└── types/<feature>.ts
```

- **`auth/`** — `AuthProvider` owns the session. The access token lives in
  memory; the refresh token in `localStorage`. `authorizedRequest` injects the
  bearer token and transparently refreshes once on a 401. `logout` blacklists
  the refresh token server-side.
- **`organizations/`** — `OrganizationsProvider` holds the org list and the
  current selection (persisted in `localStorage`). Every feature is scoped to
  `currentOrganization`.
- **`RequireAuth`** gates the app on a session; **`RequireOrganization`** gates
  the feature area on having a current organization.
- **`HomePage`** is an app shell (topbar with brand / org switcher / sign out)
  plus a tab workspace: **Overview · Customers · Orders · Invoices · Settings**.
  Each tab mounts its own provider tree, so opening a tab always shows current
  data and nothing is fetched until its tab is opened.
- **`dashboard/`** — `DashboardProvider` calls `GET /dashboard/?organization=<id>`
  (a single backend aggregation) for the Overview tab. Figures are never derived
  from the list providers, which apply their own filters.

Feature providers request their list scoped to the current organization
(`?organization=<id>` and, for orders/invoices, `&status=`) and refetch when the
selection changes. **Search** (customers, invoices) and the **status filter**
(orders, invoices) live on the provider; search filters the already-loaded list
client-side (no request), the status filter refetches server-side.

Shared UI: `components/StatusBadge`, `components/SearchInput`,
`components/StatusFilter`, and `lib/format.ts` (`formatAmount` / `formatDate`,
locale pinned to `en-US` so every teammate sees identical figures).

## Commands

```bash
npm install
npm run dev            # Vite dev server on :5173
npm run build          # tsc -b && vite build
npm run lint
npm run format:check   # prettier --check .
npm run typecheck      # tsc -b --noEmit
npm run test:run       # vitest run
```

`VITE_API_URL` (default `http://localhost:8000/api/v1`) points the client at the
backend.

## Production build & serving

`npm run build` emits static assets to `frontend/dist/` (`index.html` +
hashed `assets/`). There is no server-side rendering.

In production these assets are built and served by the nginx **`proxy`**
container (`infrastructure/docker/frontend.prod.Dockerfile`, multi-stage:
Node build → nginx). That same nginx reverse-proxies `/api`, `/admin`,
`/static` and `/health` to Gunicorn, so:

- `VITE_API_URL` is baked at **build time** to `/api/v1` (same origin — no CORS,
  no per-environment rebuild for the host name). Override via the
  `VITE_API_URL` build arg if the API lives elsewhere.
- SPA deep links survive a refresh: nginx `try_files … /index.html`.

See [docs/runbooks/production-deployment.md](../docs/runbooks/production-deployment.md).
