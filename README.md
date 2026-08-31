# Spendly

> **Track every rupee. Know where it goes.**

Spendly is a lightweight, personal expense tracker built with Flask and SQLite. It helps you log expenses, spot spending patterns, and stay on top of your budget — without the spreadsheet headache.

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![Flask](https://img.shields.io/badge/flask-3.1.3-green) ![SQLite](https://img.shields.io/badge/sqlite-3-lightgrey) ![License](https://img.shields.io/badge/license-MIT-purple)

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [Routes](#routes)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Configuration](#configuration)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- 🔐 **Secure authentication** — Email + password with hashed credentials (Werkzeug)
- 💸 **Expense tracking** — Log amount, category, date, and description
- 📊 **Profile dashboard** — Total spent, transaction count, and top category at a glance
- 🎯 **Category breakdown** — Visual progress bars for 7 fixed categories (Food, Transport, Bills, Health, Entertainment, Shopping, Other)
- 📅 **Date-range filter** — Slice your transaction history by any custom period
- ✏️ **Edit expenses** — Update any of your own expenses; 404 (not 403) when touching other users' data
- 🔒 **Session-based auth** — Flask-managed sessions, no custom cookie logic
- 🧪 **Comprehensive test suite** — pytest + pytest-flask with isolated temp databases

---

## Tech Stack

| Layer       | Choice                                              |
| ----------- | --------------------------------------------------- |
| Language    | Python 3.8+                                         |
| Framework   | [Flask 3.1.3](https://flask.palletsprojects.com/)   |
| Database    | [SQLite 3](https://www.sqlite.org/) (raw, no ORM)   |
| Passwords   | [Werkzeug 3.1.6](https://werkzeug.palletsprojects.com/) (`generate_password_hash` / `check_password_hash`) |
| Tests       | [pytest 8.3.5](https://docs.pytest.org/) + [pytest-flask 1.3.0](https://pytest-flask.readthedocs.io/) |
| Frontend    | Jinja2 templates + vanilla CSS/JS (no React, no jQuery) |

> **Constraint:** No new pip packages are added mid-feature. The frontend is intentionally vanilla — no build step, no npm.

---

## Quick Start

### Prerequisites

- Python 3.8 or higher
- `pip` (Python package manager)
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Arijit-mondal099/spendly.git
cd spendly

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

### Running the App

```bash
# Start the dev server (port 5001)
python app.py
```

Visit **http://localhost:5001** in your browser.

> ⚠️ The app uses **port 5001**, not Flask's default `5000`. This is intentional to avoid collisions with other local services.

### Demo Credentials

The first time you start the app, `seed_db()` inserts a demo user and 8 sample expenses:

| Field    | Value               |
| -------- | ------------------- |
| Email    | `demo@spendly.com`  |
| Password | `demo123`           |

The SQLite database (`expense_tracker.db`) is auto-created at the repo root on first run.

---

## Project Structure

```
spendly/
├── app.py                      # All routes (no blueprints), runs on port 5001
├── conftest.py                 # Pytest fixtures: temp DB + test client
├── requirements.txt            # Pinned deps: Flask, Werkzeug, pytest, pytest-flask
│
├── db/
│   ├── __init__.py
│   ├── db.py                   # Writes: get_db/close_db/init_db/seed_db + insert_expense/update_expense/create_user
│   └── queries.py              # Reads: get_user_by_id/get_summary_stats/get_recent_transactions/get_category_breakdown
│
├── templates/                  # Jinja2, all extend base.html
│   ├── base.html               # Shared layout: nav, footer, fonts
│   ├── landing.html            # Public landing page
│   ├── login.html              # Sign-in form
│   ├── register.html           # Sign-up form
│   ├── profile.html            # Authenticated dashboard
│   ├── add_expense.html        # Add-expense form
│   ├── edit_expense.html       # Edit-expense form
│   ├── terms.html              # Terms and Conditions
│   └── privacy.html            # Privacy Policy
│
├── static/
│   ├── css/
│   │   ├── style.css           # Global styles + design tokens
│   │   ├── profile.css         # Profile-page styles
│   │   ├── add_expense.css     # Add-expense form styles
│   │   └── edit_expense.css    # Edit-expense form styles
│   └── js/
│       └── main.js             # Vanilla JS (modal handling, etc.)
│
├── tests/
│   ├── test_backend_connection.py   # /profile + db.queries helpers
│   ├── test_date_filter.py          # Date-range filter on /profile
│   ├── test_add_expense.py          # /expenses/add + insert_expense
│   └── test_edit_expense.py         # /expenses/<id>/edit + update_expense
│
├── design/                     # Reference images only
├── .claude/                    # Specs, agents, skills, hooks (project tooling)
└── expense_tracker.db          # Generated at runtime, gitignored
```

---

## Architecture

Spendly follows a **layered architecture** with strict separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                       app.py                            │
│   (Routes: validate input → call DB helper → render)    │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────┐         ┌──────────────────┐
│   db/db.py   │         │  db/queries.py   │
│  (WRITES)    │         │    (READS)       │
│              │         │                  │
│ • get_db     │         │ • get_user_by_id │
│ • close_db   │         │ • get_summary    │
│ • init_db    │         │ • get_recent     │
│ • seed_db    │         │ • get_breakdown  │
│ • create_user│         │                  │
│ • insert_exp │         │                  │
│ • update_exp │         │                  │
└──────┬───────┘         └────────┬─────────┘
       │                          │
       └──────────┬───────────────┘
                  ▼
        ┌──────────────────┐
        │  SQLite (file)   │
        │ expense_tracker  │
        │      .db         │
        └──────────────────┘
```

### Key Principles

1. **No SQL in routes.** All database logic lives in `db/db.py` (writes) or `db/queries.py` (reads).
2. **No blueprints.** The app uses a flat route structure in `app.py` for simplicity.
3. **No ORM.** Raw `sqlite3` only, with parameterized queries (`?` placeholders) to prevent SQL injection.
4. **No new dependencies.** The `requirements.txt` is intentionally minimal and pinned.
5. **Tests are spec-driven.** Each test corresponds to a feature spec in `.claude/specs/`, not the implementation.

---

## Database Schema

Two tables, defined in `db/db.py`:

```sql
-- Users
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now'))
);

-- Expenses
CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL NOT NULL,
    category    TEXT NOT NULL,    -- one of 7 fixed categories
    date        TEXT NOT NULL,    -- ISO YYYY-MM-DD
    description TEXT,             -- nullable
    created_at  TEXT DEFAULT (datetime('now'))
);
```

### Notes

- **Foreign keys are enforced** — `get_db()` runs `PRAGMA foreign_keys = ON` on every connection (SQLite does not enable this by default).
- **`description` is nullable** — an empty/whitespace description is stored as `NULL`, not `''`.
- **Categories are a fixed enum** of 7 values: `Food`, `Transport`, `Bills`, `Health`, `Entertainment`, `Shopping`, `Other`.
- **Amount validation** — must be a finite float in `(0, 1_000_000_000]`.

---

## Routes

| Method   | Path                          | Auth   | Description                                        |
| -------- | ----------------------------- | ------ | -------------------------------------------------- |
| `GET`    | `/`                           | —      | Public landing page                                |
| `GET` `POST` | `/register`               | —      | Create a new account                               |
| `GET` `POST` | `/login`                  | —      | Sign in (sets `session['user_id']`)                |
| `GET`    | `/logout`                     | ✅     | Clear session, redirect to login                   |
| `GET`    | `/terms`                      | —      | Terms and Conditions                               |
| `GET`    | `/privacy`                    | —      | Privacy Policy                                     |
| `GET`    | `/profile`                    | ✅     | Dashboard with stats, transactions, and filter     |
| `GET` `POST` | `/expenses/add`           | ✅     | Add a new expense                                  |
| `GET` `POST` | `/expenses/<id>/edit`     | ✅     | Edit one of your own expenses (404 for others)     |
| `GET`    | `/expenses/<id>/delete`       | ✅     | **Stub** — coming in Step 9                        |

> **Profile filter:** `/profile?start=YYYY-MM-DD&end=YYYY-MM-DD` filters the transaction list and summary stats by an inclusive date range. Invalid dates are silently ignored.

---

## Development Workflow

### Adding a New Route

1. Define the route in `app.py` only. Do not use blueprints.
2. If the route reads or writes the DB, call a helper from `db/db.py` or `db/queries.py` — never inline SQL in the route.
3. Create a Jinja2 template that extends `base.html`.
4. Add page-specific styles to a new `static/css/<page>.css` file (no inline `<style>` tags).
5. Write a test in `tests/test_<feature>.py` before considering the feature done.

### Adding a Database Helper

- **Writes** (`INSERT`/`UPDATE`/`CREATE`/seed logic) → `db/db.py`
- **Reads** (`SELECT` only) → `db/queries.py`
- Always use parameterized queries: `db.execute("... WHERE id = ?", (id,))`.

### Slash Commands

Spendly ships with project-specific Claude Code slash commands in `.claude/commands/`:

- `/create-spec` — Create a spec file and feature branch for the next step
- `/test-feature <spec-name>` — Write and run tests for a feature
- `/code-review-feature <spec-name>` — Run security + quality code review
- `/ship-feature` — Commit, push, create PR, merge, and clean up
- `/seed-user`, `/seed-expense` — Add demo data

---

## Testing

### Run All Tests

```bash
pytest
```

### Run a Specific Test File

```bash
pytest tests/test_add_expense.py
```

### Run a Specific Test by Name

```bash
pytest -k "test_post_add_expense_valid"
```

### Show Output (e.g. for `print` debugging)

```bash
pytest -s
```

### How the Test Suite Works

- **`conftest.py` repoints the DB** at a temp file inside the `app` fixture — *before* `app.py` is imported. This means tests never touch your dev database.
- **Critical rule:** No test file may `import app` at module level. Collection imports run before fixtures and would hit the real DB. Always import `app` inside a fixture or test body.
- **Critical rule:** Never assert global row counts. The shared seeded DB plus per-run fixtures mean only relational/ordering assertions are stable. Scope every DB lookup to a specific `user_id`.

### Test Coverage by Feature

| Test file                         | What it covers                                          |
| --------------------------------- | ------------------------------------------------------- |
| `test_backend_connection.py`      | `/profile` route + `db.queries` helpers                 |
| `test_date_filter.py`             | Date-range filter on `/profile`                         |
| `test_add_expense.py`             | `/expenses/add` route + `insert_expense` helper         |
| `test_edit_expense.py`            | `/expenses/<id>/edit` route + `update_expense` helper   |

---

## Configuration

### Environment Variables

Spendly does not read any environment variables by default. The only configuration knob is the secret key, which is currently set to a random per-process value:

```python
# app.py
app.secret_key = secrets.token_hex()
```

> ⚠️ **This means every server restart signs everyone out.** Fine for development. For production, set `app.secret_key` to a stable, environment-loaded value (e.g. `os.environ["SECRET_KEY"]`).

### Database File

- Default location: `<repo-root>/expense_tracker.db`
- Override: monkey-patch `db.db._DATABASE_PATH` *before* importing `app`. (See `conftest.py` for the pattern.)

---

## Roadmap

The project is being built step-by-step via specs in `.claude/specs/`:

| Step | Spec                          | Status              |
| ---- | ----------------------------- | ------------------- |
| 1    | `01-database-setup.md`        | ✅ Complete         |
| 2    | `02-registration.md`          | ✅ Complete         |
| 3    | `03-login-logout.md`          | ✅ Complete         |
| 4    | `04-profile-page.md`          | ✅ Complete         |
| 5    | `05-backend-routes-for-profile-page.md` | ✅ Complete |
| 6    | `06-date-filter.md`           | ✅ Complete         |
| 7    | `07-add-expense.md`           | ✅ Complete         |
| 8    | `08-edit-expense.md`          | ✅ Complete         |
| 9    | `09-delete-expense.md`        | 🔜 Next             |

**Planned future features:**

- 🗑️ **Delete expense** — Step 9 stub is already in `app.py`
- 📈 **Monthly trend chart** — line chart of spending over time
- 🔍 **Search and sort** — full-text search across descriptions
- 📤 **CSV export** — download your transaction history
- 🌙 **Dark mode** — using the existing CSS variable system

---

## Contributing

1. **Pick or open an issue.** Describe the change you want to make.
2. **Read the spec.** If the feature has a spec in `.claude/specs/`, read it first — tests are derived from the spec, not the implementation.
3. **Create a feature branch.** `git checkout -b feat/<short-description>`
4. **Follow the architecture rules** in [CLAUDE.md](./CLAUDE.md):
   - DB logic in `db/`, never in routes
   - Writes in `db/db.py`, reads in `db/queries.py`
   - No new pip packages without flagging
   - No inline SQL — always parameterized
5. **Write tests** for every new route or helper.
6. **Run the full test suite** before pushing: `pytest`
7. **Open a Pull Request** with a clear description of the change.

---

## License

MIT License. See [LICENSE](./LICENSE) for details.

---

## Acknowledgments

- Built as a learning project to demonstrate clean Flask + SQLite architecture
- Design inspired by minimalist personal-finance tools
- Test patterns follow the [pytest-flask](https://pytest-flask.readthedocs.io/) idiom of session-scoped app + per-test client

---

<p align="center">Made with care. Track every rupee. Own your finances.</p>
