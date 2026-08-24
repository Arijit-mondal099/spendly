# Spec: Registration

## Overview

Implement account registration end-to-end. Today `/register` only renders a static signup form; submitting it goes nowhere. This feature adds the `POST /register` handler: validate the submitted name, email, and password server-side, reject duplicate emails gracefully, hash the password with werkzeug, and insert the new user through a dedicated helper in `db/db.py`. On success the user lands on the login page. Every later step in the roadmap (login, logout, profile, expense tracking) depends on real accounts existing, which makes this the natural next layer on top of the Step 1 data foundation.

---

## Depends on

- **Step 1 — Database Setup**: the `users` table (with `UNIQUE email` constraint), `get_db()`, and `init_db()` must exist. Werkzeug's `generate_password_hash` is already used by `seed_db()`.

---

## Routes

- `GET /register` — already implemented (renders the signup form) — public
- `POST /register` — process the signup form: validate input, create the user via `db/db.py`, redirect to the login page on success; re-render the form with an error message on failure — public

No other routes are added or modified in this step.

---

## Database changes

**No database changes.** The `users` table created in Step 1 (`id`, `name`, `email UNIQUE`, `password_hash`, `created_at`) already supports everything this feature needs. This step adds a new **function** (`create_user`) in `db/db.py`, not a schema change.

---

## Templates

- **Create:** none

- **Modify:**
  - `templates/register.html`
    - Replace the hardcoded `action="/register"` with `action="{{ url_for('register') }}"` (CLAUDE.md forbids hardcoded internal URLs)
    - Render server-side validation errors through the existing `{% if error %}` block
    - After a failed submission, pre-fill the `name` and `email` inputs with the submitted values (never echo the password back)

---

## Files to change

- `app.py` — extend the `register` view to accept `GET` and `POST`; validate input; delegate insertion to `db/db.py`; redirect to login on success
- `db/db.py` — add `create_user(name, email, password_hash)` performing the parameterized `INSERT INTO users` and returning the new row id
- `templates/register.html` — changes listed under Templates

---

## Files to create

None.

---

## New dependencies

No new dependencies.

---

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` through the existing `get_db()` pattern only
- Parameterised queries only (`?` placeholders) — never build SQL with f-strings or concatenation
- Passwords hashed with werkzeug (`generate_password_hash`) — plaintext passwords must never reach the database
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Database logic lives in `db/db.py` only — the route validates input and calls the helper, nothing more
- Use `url_for()` for every internal link, including the form `action`
- Validation failures re-render `register.html` with an `error` message (the template's existing pattern); reserve `abort()` for genuine HTTP errors — never return plain error strings
- Enforce server-side rules regardless of HTML attributes: non-empty name, syntactically valid email, password of at least 8 characters (matching the form's "Min. 8 characters" hint)
- Treat the `users.email` UNIQUE constraint as the backstop: catch/re-check duplicates so a race cannot produce a raw sqlite traceback
- Follow PEP 8 / `snake_case`
- Do not touch any stub routes (`/logout`, `/profile`, `/expenses/*`) — they belong to later steps
- No new pip packages; no JavaScript frameworks
- The dev server keeps running on port `5001`

---

## Definition of done

Each item verifiable by running the app (`python app.py`, port 5001):

- [ ] `GET /register` still renders the signup form unchanged
- [ ] Submitting valid details (new name/email/password ≥ 8 chars) inserts a row into `users` and redirects to the login page
- [ ] Inspecting the database confirms the stored `password_hash` is a werkzeug hash, not the plaintext password
- [ ] Submitting an email that already exists re-renders `/register` with a friendly "email already registered" style error and does **not** insert a second row
- [ ] Submitting an empty name, a malformed email, or a too-short password each shows a specific error message and inserts nothing
- [ ] After a failed submission, the name and email fields retain what was typed (password empty again)
- [ ] The rendered page contains no hardcoded internal URLs — the form action resolves via `url_for()`
- [ ] The app starts and serves without errors on port `5001`
