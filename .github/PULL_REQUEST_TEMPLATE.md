# Describe Your Changes

Please provide a clear, concise description of what this PR does, why it is necessary, and any structural/behavioral changes introduced.

## Checklist Before Requesting Review

- [ ] My code follows the core architectural guidelines defined in `GEMINI.md`.
- [ ] I have not modified any files or directories unrelated to my assigned task.
- [ ] I have not introduced new technologies/packages without explicit team approval.
- [ ] I have fully typed all new structures (avoiding Python untyped or TypeScript `any` types).
- [ ] I have written automated tests to verify the correctness of my changes.
- [ ] I have verified that all existing and new tests pass locally.
- [ ] I have updated any relevant documentation (under `/docs` or in the root files) if my changes alter configuration or database schemas.
- [ ] I have verified that no sensitive credentials or keys are hardcoded.

## How to Verify These Changes?

Please describe the manual or automated steps required to verify your implementation. Include commands to run or specific endpoints/UI forms to test.

```bash
# Example: Run the backend test suite
cd backend && pytest

# Example: Run the frontend test suite
cd frontend && npm run test
```

## Related Architectural Decisions or Issues

If this relates to a specific issue or Architectural Decision Record (ADR), link it here:
- Fixes #
- Relates to ADR-
