# Spendly

Spendly is a lightweight personal expense tracker built with Flask and SQLite, designed to help users easily record, manage, and track their expenses.

## Architecture

(See `ls` for the current tree; the repo has `app.py`, `db/`, `templates/`, `static/`, `tests/`, `design/`, `conftest.py`, `requirements.txt`.)

## Where Things Belong

- **New routes:** Add them to `app.py` only. Do not use blueprints.
- **Database logic:** Keep all database operations in `db/db.py`. Never write database logic directly inside routes.
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
| `GET /profile` | Implemented — renders `profile.html` with live DB data |
| `GET /expenses/add` | Stub — Step 7 |
| `GET /expenses/<id>/edit` | Stub — Step 8 |
| `GET /expenses/<id>/delete` | Stub — Step 9 |

**Do not implement a stub route unless the active task explicitly targets that step.**

## Warnings and Things to Avoid

- **Never use raw string returns for stub routes** once a step is implemented — always render a template.
- **Never hardcode URLs** in templates — always use `url_for()`.
- **Never put database logic in route functions** — it belongs in `db/db.py`.
- **Never install new packages** mid-feature without flagging it — keep `requirements.txt` in sync.
- **Never use JavaScript frameworks** — the frontend is intentionally vanilla.
- **Tests must never `import app` at module level** — `conftest.py` repoints the DB at a temp file before app is imported; module-level imports would touch the dev database.
- **Tests must never assert global row counts** — the shared seeded DB plus per-run fixtures mean only relational/ordering assertions are stable.
- **SQLite foreign keys must be explicitly enabled** — `get_db()` must run `PRAGMA foreign_keys = ON` on every connection.
- **The app runs on port `5001`**, not Flask's default `5000` — do not change this.
