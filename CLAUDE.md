# Spendly

Spendly is a lightweight personal expense tracker built with Flask and SQLite, designed to help users easily record, manage, and track their expenses.

## Architecture

```
app.py                      # all routes (no blueprints), port 5001
db/
  db.py                     # writes: get_db/close_db/init_db/seed_db + insert_expense/update_expense
  queries.py                # reads: get_user_by_id/get_summary_stats/get_recent_transactions/get_category_breakdown
templates/
  *.html                    # Jinja2, all extend base.html (landing, login, register, profile, add_expense, edit_expense, terms, privacy)
static/
  css/*.css                 # style.css + page-specific files (profile.css, add_expense.css, edit_expense.css)
  js/main.js
tests/
  test_*.py                 # pytest + pytest-flask, fixtures in conftest.py
design/                     # reference images only
conftest.py                 # temp-DB fixture (must import app inside fixtures, not at module level)
requirements.txt            # Flask, Werkzeug, pytest, pytest-flask only
.claude/
  specs/01-08-*.md           # feature specs (Step 8 edit-expense is current)
  commands/                 # slash commands (e.g. ship-feature)
  agents/ skills/ hooks/ rules/ plans/
```

Generated/ignored at runtime: `venv/`, `__pycache__/`, `.pytest_cache/`, `expense_tracker.db`, `.env`.

## Where Things Belong

- **New routes:** Add them to `app.py` only. Do not use blueprints.
- **Database logic:** Writes (`INSERT`/`UPDATE`/`CREATE`) in `db/db.py`; reads (`SELECT`) in `db/queries.py`. Never write database logic directly inside routes. Never put write helpers in `queries.py`.
- **New pages:** Create a new `.html` template that extends `base.html`.
- **Page-specific styles:** Create a dedicated `.css` file. Do not use inline `<style>` tags.

## Code Style

- **Python:** Follow PEP 8. Use `snake_case` for variables and functions.
- **Templates:** Use Jinja2. Use `url_for()` for every internal link; never hardcode URLs.
- **Route functions:** Keep each route focused on one responsibility: validate input, call the required DB logic, and render or redirect.
- **Database queries:** Always use parameterized queries with `?` placeholders. Never build SQL with f-strings or string concatenation.
- **Error handling:** Use Flask's `abort()` for HTTP errors. Do not return plain error strings.

## Tech Constraints

- **Flask only** — no FastAPI, no Django, no other web frameworks
- **SQLite only** — no PostgreSQL, no SQLAlchemy ORM, no external DB
- **Vanilla JS only** — no React, no jQuery, no npm packages
- **No new pip packages** — work within `requirements.txt` as-is unless explicitly told otherwise

## Subagent Policy

- Always use a built-in **Explore** subagent for codebase exploration before implementing any new feature.
- Always use a subagent to verify test results after any implementation.
- When asked to create a plan, delegate codebase research to a subagent before presenting the plan.
- Always use a built-in **Plan** subagent when working in plan mode.

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run dev server (port 5001)
python app.py

# Run all tests
pytest

# Run a specific test file
pytest tests/test_foo.py

# Run a specific test by name
pytest -k "test_name"

# Run tests with output visible
pytest -s
```

## Implemented vs Stub Routes

| Route | Status |
|---|---|
| `GET /` | Implemented — renders `landing.html` |
| `GET/POST /register` | Implemented — validates input, creates user, redirects to login |
| `GET/POST /login` | Implemented — authenticates via session |
| `GET /logout` | Implemented — clears session, redirects to login |
| `GET /terms` | Implemented — renders `terms.html` |
| `GET /privacy` | Implemented — renders `privacy.html` |
| `GET /profile` | Implemented — renders `profile.html` with live DB data + date-range filter (`?start=&end=`, Step 6) |
| `GET/POST /expenses/add` | Implemented — Step 7: validates input, calls `insert_expense` in `db/db.py`, renders `add_expense.html` |
| `GET/POST /expenses/<id>/edit` | Implemented on `feature/edit-expense` (Step 8: pre-filled form, validation, `update_expense` in `db/db.py`, `edit_expense.html`); stub on `main` until PR merged |
| `GET /expenses/<id>/delete` | Stub — Step 9 |

**Do not implement a stub route unless the active task explicitly targets that step.** Status above reflects `feature/edit-expense` working tree; `origin/main` still has `edit` as a `GET`-only placeholder (`return "Edit expense — coming in Step 8"`, `app.py:327`).

## Warnings and Things to Avoid

- **Never use raw string returns for stub routes** once a step is implemented — always render a template.
- **Never hardcode URLs** in templates — always use `url_for()`.
- **Never put database logic in route functions** — it belongs in `db/db.py` (writes) / `db/queries.py` (reads).
- **Never install new packages** mid-feature without flagging it — keep `requirements.txt` in sync.
- **Never use JavaScript frameworks** — the frontend is intentionally vanilla.
- **Tests must never `import app` at module level** — `conftest.py` repoints the DB at a temp file before app is imported; module-level imports would touch the dev database.
- **Tests must never assert global row counts** — the shared seeded DB plus per-run fixtures mean only relational/ordering assertions are stable.
- **SQLite foreign keys must be explicitly enabled** — `get_db()` must run `PRAGMA foreign_keys = ON` on every connection.
- **The app runs on port `5001`**, not Flask's default `5000` — do not change this.
