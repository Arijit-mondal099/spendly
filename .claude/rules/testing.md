---
paths:
  - "tests/**/*.py"
  - "conftest.py"
---

# Testing Rules

- Never `import app` at module level. `conftest.py` repoints the DB at a temp file before `app` is imported — a module-level import bypasses that and touches the dev database.
- Never assert global row counts. The shared seeded DB plus per-run fixtures mean only relational/ordering assertions are stable (e.g. "this user has N transactions", not "the table has N rows").
- Use the fixtures from `conftest.py` (isolated temp DB + test client) rather than constructing your own DB connection.
- Every new or modified route in `app.py` must have a corresponding test in `tests/` before the task is considered done.
