---
paths:
  - "db/**/*.py"
---

# Database Rules

- All database logic lives here, in `db/`. Routes in `app.py` must never contain SQL or direct cursor calls — they call functions from `db/db.py` or `db/queries.py`.
- Always use parameterized queries with `?` placeholders. Never build SQL with f-strings or string concatenation.
- `get_db()` must run `PRAGMA foreign_keys = ON` on every connection — SQLite does not enable this by default.
- No ORM (no SQLAlchemy). Raw `sqlite3` only.
- `db/queries.py` is read-only (profile/summary lookups). Writes/schema/seed logic belongs in `db/db.py`.
