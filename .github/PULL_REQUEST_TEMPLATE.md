# Summary

What does this PR do, and why?

## Changes

-

## Checklist

- [ ] Follows the conventions in [`CONTRIBUTING.md`](../CONTRIBUTING.md).
- [ ] Scoped to this change — no unrelated files touched.
- [ ] No new dependency without justification in this description.
- [ ] New/changed structures are fully typed (no untyped Python, no TS `any`).
- [ ] Tests added/updated for the behaviour that changed.
- [ ] Ran locally and all checks pass (see below).
- [ ] Docs updated (`README.md`, `docs/`, `.env.example`) if behaviour, config or the schema changed.
- [ ] No secrets, credentials or keys added.

## Verification

```bash
cd backend && ruff check . && ruff format --check . && python manage.py check && pytest
cd frontend && npm run lint && npm run format:check && npm run typecheck && npm run test:run && npm run build
```

## Security considerations

Does this touch auth, tenant scoping, permissions, logging, or production
settings? If so, describe the impact.

## Related

- Fixes #
- Relates to ADR-
