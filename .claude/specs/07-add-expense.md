# Spec: Add Expense

## Overview

Step 7 lets a logged-in user submit a new expense through a dedicated form page
at `/expenses/add`. The route already exists as a GET placeholder; this step
upgrades it to a full GET + POST handler, inserts validated data into the
`expenses` table, and redirects back to the profile page on success. A reusable
`insert_expense` query helper is added to `db/db.py`. An "Add Expense"
button is added to `profile.html` so users can navigate to the form.

## Depends on

- Step 1: Database setup (`expenses` table exists with all required columns)
- Step 3: Login / Logout (`session["user_id"]` is set and checked)
- Step 4 / 5: Profile page exists and is the natural redirect target after saving

## Routes

- `GET /expenses/add` — render the add-expense form — logged-in only (302 to `/login` if unauthenticated)
- `POST /expenses/add` — validate and insert the new expense — logged-in only (302 to `/login` if unauthenticated)

## Database changes

No database changes. The `expenses` table already has all required columns:
`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

## Templates

- **Create**: `templates/add_expense.html`
  - Extends `base.html`
  - Form with `method="POST"` and `action="{{ url_for('add_expense') }}"` (never hardcode `/expenses/add`)
  - Fields:
    - `amount` — number input, step="0.01", min="0.01", required
    - `category` — `<select>` with the 7 fixed options: Food, Transport, Bills, Health, Entertainment, Shopping, Other
    - `date` — `<input type="date">`, required, defaults to today's date (pass `today=date.today().isoformat()` from route)
    - `description` — text input, optional, `maxlength="200"`
  - Submit button ("Save Expense") and a cancel link back to `{{ url_for('profile') }}`
  - Display error message when validation fails via `{% if error %}<p class="auth-error">{{ error }}</p>{% endif %}` (same pattern as `login.html`/`register.html`), re-populating previous values (re-set `value` attributes and `selected` on category)
  - Dedicated stylesheet `static/css/add_expense.css` linked in `{% block head %}` — no inline `<style>` tags
- **Modify**: `templates/profile.html`
  - Add an "Add Expense" button/link pointing to `{{ url_for('add_expense') }}` placed next to the "Recent transactions" heading (`<h2 class="profile-card-title">`)
- **Modify**: `templates/base.html`
  - Add "Add Expense" link in navbar (`<a href="{{ url_for('add_expense') }}">Add Expense</a>`) visible only when `session.user_id` is set, inside the existing `{% if session.user_id %}` block

## Files to change

- `app.py` — replace the GET-only placeholder at `/expenses/add` with a GET+POST handler:
  - GET: redirect to `url_for("login")` if not authenticated (302); otherwise render `add_expense.html`
  - POST: redirect to `url_for("login")` if not authenticated (302); otherwise read form fields, validate, call `insert_expense`, redirect to `url_for("profile")` on success or re-render form with `error` and submitted values on failure
  - Must declare `methods=["GET", "POST"]` on the route
- `db/db.py` — add `insert_expense(user_id, amount, category, date, description)` (write helper — `db/queries.py` is read-only per project rules)
- `templates/profile.html` — add "Add Expense" button
- `templates/base.html` — add "Add Expense" link in navbar for authenticated users

## Files to create

- `templates/add_expense.html` — the add-expense form template (extends `base.html`)
- `static/css/add_expense.css` — page-specific styles (use CSS variables from `static/css/style.css`; never hardcode hex values)

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL (use `?` placeholders)
- Foreign keys PRAGMA must be enabled on every connection (already done in `get_db()`)
- Unauthenticated access to both GET and POST `/expenses/add` must redirect to `url_for("login")` with 302
- `insert_expense` contract:
  - Signature: `insert_expense(user_id, amount, category, date, description)` where `amount` is `float`, `category`/`date` are `str`, `description` is `str|None`
  - Executes `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)` via `get_db()`, commits, and returns `cursor.lastrowid`
- Validation rules for POST (all server-side; client-side attributes are not sufficient):
  - `amount`: required (strip whitespace; missing/empty → error), must parse with `float()` (catch `ValueError` → error), must be `> 0` (0 or negative → error)
  - `category`: required, must be an exact (case-sensitive, no trimming) match to one of the 7 fixed categories: `Food`, `Transport`, `Bills`, `Health`, `Entertainment`, `Shopping`, `Other` (anything else → error)
  - `date`: required, must be a valid `YYYY-MM-DD` date (parse with `datetime.strptime(date_str, "%Y-%m-%d")`; catch `ValueError` → error); any valid calendar date is accepted (past, today, or future)
  - `description`: optional; strip whitespace; store `None` (→ `NULL` in DB) if blank; if non-blank, must be `<= 200` characters (longer → error)
  - On any validation error, re-render `add_expense.html` with status 200, passing `error` (string) and the previously submitted values pre-filled (`amount`, `category`, `date`, `description`)
- After successful insert, redirect to `url_for("profile")` with 302 — do NOT render the form again
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹ — never £ or $
- All internal links use `url_for()` — never hardcode URLs

## Tests to write

File: `tests/test_add_expense.py`

### Unit tests

| Function         | Input                                                                                         | Expected output                                   |
| ---------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `insert_expense` | valid `user_id`, `amount=50.0`, `category="Food"`, `date="2026-03-20"`, `description="Lunch"` | row inserted; querying the DB returns the new row; function returns new row id |
| `insert_expense` | `description=None`                                                                            | row inserted with `description` stored as `NULL`  |

### Route tests

`GET /expenses/add` — unauthenticated:

- Redirects to `/login` (302)

`GET /expenses/add` — authenticated:

- Returns 200
- Response body contains the category `<select>` with all 7 options
- Response body contains `<form` with `method` POST

`POST /expenses/add` — unauthenticated:

- Redirects to `/login` (302)

`POST /expenses/add` — authenticated, valid data (`amount=50.0`, `category=Food`, `date=2026-03-20`, `description=Lunch`):

- Redirects to `/profile` (302)
- New expense row exists in the database for the test user

`POST /expenses/add` — authenticated, missing amount:

- Returns 200 (re-renders form)
- Response body contains an error message

`POST /expenses/add` — authenticated, amount = 0:

- Returns 200 (re-renders form)
- Response body contains an error message

`POST /expenses/add` — authenticated, non-numeric amount:

- Returns 200 (re-renders form)
- Response body contains an error message

`POST /expenses/add` — authenticated, invalid category (not in fixed list):

- Returns 200 (re-renders form)
- Response body contains an error message

`POST /expenses/add` — authenticated, invalid date string:

- Returns 200 (re-renders form)
- Response body contains an error message

`POST /expenses/add` — authenticated, no description (optional field):

- Redirects to `/profile` (302)
- Row inserted with `description = NULL`

`POST /expenses/add` — authenticated, description > 200 chars:

- Returns 200 (re-renders form)
- Response body contains an error message

## Definition of done

- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows a form with amount, category, date, and description fields
- [ ] The category dropdown contains exactly: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- [ ] Submitting a valid expense redirects to `/profile` and the new expense appears in the transaction list
- [ ] Submitting with a missing or zero amount re-renders the form with an error and previously entered values retained
- [ ] Submitting with an invalid category re-renders the form with an error
- [ ] Submitting with an invalid date re-renders the form with an error
- [ ] Submitting without a description saves the expense with no description (no error)
- [ ] The "Add Expense" button on the profile page navigates to `/expenses/add` via `url_for('add_expense')`
- [ ] Navbar shows "Add Expense" link when logged in (via `url_for('add_expense')`)
