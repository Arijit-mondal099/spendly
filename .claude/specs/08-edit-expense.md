# Spec: Edit Expense

## Overview

Step 8 lets a logged-in user edit an existing expense they previously created.
The `GET /expenses/<id>/edit` route is currently a stub returning a placeholder
string; this step upgrades it to a full GET + POST handler that loads the
expense by id, pre-fills the form with its current values, validates submitted
changes, and updates the row in the `expenses` table. On success, the user is
redirected back to the profile page. A user can only edit their own expenses
— accessing another user's expense returns 404. A reusable
`update_expense` query helper is added to `db/db.py` (writes belong there, not
in `db/queries.py`). An "Edit" link/button is added to the recent
transactions list on the profile page so users can navigate to the form.

## Depends on

- Step 1: Database setup (`expenses` table exists with all required columns)
- Step 3: Login / Logout (`session["user_id"]` is set and checked)
- Step 4 / 5: Profile page exists and renders the recent transactions list (the natural redirect target and source of the "Edit" link)
- Step 7: Add Expense (same form shape, same `VALID_CATEGORIES` / `MAX_AMOUNT` / `MAX_DESCRIPTION_LENGTH` constants, same `add_expense.html` styling and CSS file conventions)

## Routes

- `GET /expenses/<int:id>/edit` — render the edit form pre-filled with the current expense values — logged-in only (302 to `/login` if unauthenticated, 404 if the expense doesn't exist or belongs to another user)
- `POST /expenses/<int:id>/edit` — validate the submitted fields and update the row in the `expenses` table — logged-in only (302 to `/login` if unauthenticated, 404 if the expense doesn't exist or belongs to another user)

## Database changes

No database changes. The `expenses` table already has all required columns:
`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

## Templates

- **Create**: `templates/edit_expense.html`
  - Extends `base.html`
  - Form with `method="POST"` and `action="{{ url_for('edit_expense', id=expense.id) }}"` (never hardcode `/expenses/<id>/edit`)
  - Fields (same shape as `add_expense.html`, pre-filled with the current row's values):
    - `amount` — number input, `step="0.01"`, `min="0.01"`, `required`
    - `category` — `<select>` with the 7 fixed options: Food, Transport, Bills, Health, Entertainment, Shopping, Other
    - `date` — `<input type="date">`, `required`, pre-filled with the current `date`
    - `description` — text input, optional, `maxlength="200"`
  - Submit button ("Save Changes") and a cancel link back to `{{ url_for('profile') }}`
  - Display error message when validation fails via `{% if error %}<p class="auth-error">{{ error }}</p>{% endif %}` (same pattern as `add_expense.html`), re-populating previously submitted values via the `value` attributes and `selected` on category
  - Dedicated stylesheet `static/css/edit_expense.css` linked in `{% block head %}` — no inline `<style>` tags
- **Modify**: `templates/profile.html`
  - Add an "Edit" link/button on each row of the recent transactions list, pointing to `{{ url_for('edit_expense', id=tx.id) }}`. (If the row dicts passed to the template don't yet include `id`, the route in `app.py` should be updated to include it — see `Files to change` below.)

## Files to change

- `app.py` — replace the GET-only placeholder at `/expenses/<int:id>/edit` with a GET+POST handler:
  - GET: redirect to `url_for("login")` if not authenticated (302); look up the expense by id, scoped to the current user (`WHERE id = ? AND user_id = ?`); if not found, `abort(404)`; otherwise render `edit_expense.html` pre-filled with the row's current values
  - POST: redirect to `url_for("login")` if not authenticated (302); look up the expense by id, scoped to the current user; if not found, `abort(404)`; otherwise read form fields, validate (same rules as `add_expense`), call `update_expense`, redirect to `url_for("profile")` on success or re-render form with `error` and submitted values on failure
  - Must declare `methods=["GET", "POST"]` on the route
  - Update the `profile` route's `transactions` list comprehension to include `id` in each row dict (so the template can build the edit link). This may require updating `get_recent_transactions` in `db/queries.py` to return `id` as well — see below.
- `db/db.py` — add `update_expense(expense_id, user_id, amount, category, date, description)` (write helper — `db/queries.py` is read-only per project rules)
- `db/queries.py` — update `get_recent_transactions` to also return the `id` column (so the profile template can link to the edit page). The returned dict for each row should add an `id` key.
- `templates/profile.html` — add an "Edit" link/button on each transaction row pointing to `{{ url_for('edit_expense', id=tx.id) }}`

## Files to create

- `templates/edit_expense.html` — the edit-expense form template (extends `base.html`)
- `static/css/edit_expense.css` — page-specific styles (use CSS variables from `static/css/style.css`; never hardcode hex values). Should mirror the structure of `static/css/add_expense.css` since the form layout is identical.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL (use `?` placeholders)
- Foreign keys PRAGMA must be enabled on every connection (already done in `get_db()`)
- Unauthenticated access to both GET and POST `/expenses/<id>/edit` must redirect to `url_for("login")` with 302
- Authorization: a user may only edit their own expenses. The lookup query must scope by both `id` and `user_id` (e.g. `SELECT ... WHERE id = ? AND user_id = ?`). If the row does not exist for the current user, return 404 via `flask.abort(404)`. Do NOT return 403 (which would leak the existence of the row).
- `update_expense` contract:
  - Signature: `update_expense(expense_id, user_id, amount, category, date, description)` where `amount` is `float`, `category`/`date` are `str`, `description` is `str|None`
  - Executes `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?` via `get_db()`, commits, and returns the number of rows affected (`cursor.rowcount`). A `rowcount` of 0 indicates the row no longer exists or belongs to another user — the route handler should `abort(404)` in that case.
- Validation rules for POST (identical to Step 7; reuse the same constants `VALID_CATEGORIES`, `MAX_AMOUNT`, `MAX_DESCRIPTION_LENGTH` already defined in `app.py`):
  - `amount`: required (strip whitespace; missing/empty → error), must parse with `float()` (catch `ValueError` → error), must be `> 0` (0 or negative → error)
  - `category`: required, must be an exact (case-sensitive, no trimming) match to one of the 7 fixed categories: `Food`, `Transport`, `Bills`, `Health`, `Entertainment`, `Shopping`, `Other` (anything else → error)
  - `date`: required, must be a valid `YYYY-MM-DD` date (parse with `datetime.strptime(date_str, "%Y-%m-%d")`; catch `ValueError` → error); any valid calendar date is accepted (past, today, or future)
  - `description`: optional; strip whitespace; store `None` (→ `NULL` in DB) if blank; if non-blank, must be `<= 200` characters (longer → error)
  - On any validation error, re-render `edit_expense.html` with status 200, passing `error` (string) and the previously submitted values pre-filled (`amount`, `category`, `date`, `description`)
- After successful update, redirect to `url_for("profile")` with 302 — do NOT render the form again
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹ — never £ or $
- All internal links use `url_for()` — never hardcode URLs
- Do not change the existing `add_expense` route or `add_expense.html` — this step is additive. The form templates are separate; do not try to share one template between add and edit.

## Tests to write

File: `tests/test_edit_expense.py`

### Unit tests

| Function         | Input                                                                                                  | Expected output                                                                                                |
| ---------------- | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| `update_expense` | valid `expense_id` belonging to `user_id`, new `amount=99.0`, new `category="Bills"`, new `date`, desc  | row updated; querying the DB returns the new values; `rowcount` is 1                                            |
| `update_expense` | `description=None`                                                                                     | `description` column stored as `NULL`                                                                          |
| `update_expense` | `expense_id` belonging to a *different* user                                                           | `rowcount` is 0; the row in the DB is unchanged                                                                |

### Route tests

`GET /expenses/<id>/edit` — unauthenticated:

- Redirects to `/login` (302)

`GET /expenses/<id>/edit` — authenticated, expense belongs to current user:

- Returns 200
- Response body contains the form's `action` attribute with the correct `url_for('edit_expense', id=...)` path
- Response body contains pre-filled `value` attributes for `amount`, `date`, and `description` matching the existing row
- Response body contains the category `<select>` with the row's current category marked `selected`

`GET /expenses/<id>/edit` — authenticated, expense belongs to a *different* user:

- Returns 404

`GET /expenses/<id>/edit` — authenticated, expense id does not exist:

- Returns 404

`POST /expenses/<id>/edit` — unauthenticated:

- Redirects to `/login` (302)

`POST /expenses/<id>/edit` — authenticated, valid data, own expense:

- Redirects to `/profile` (302)
- The row in the DB now has the new `amount`, `category`, `date`, `description` values

`POST /expenses/<id>/edit` — authenticated, valid data, but expense belongs to another user:

- Returns 404
- The other user's row in the DB is unchanged

`POST /expenses/<id>/edit` — authenticated, missing amount:

- Returns 200 (re-renders form)
- Response body contains an error message
- The row in the DB is unchanged

`POST /expenses/<id>/edit` — authenticated, invalid category:

- Returns 200 (re-renders form)
- Response body contains an error message
- The row in the DB is unchanged

`POST /expenses/<id>/edit` — authenticated, invalid date string:

- Returns 200 (re-renders form)
- Response body contains an error message
- The row in the DB is unchanged

`POST /expenses/<id>/edit` — authenticated, description cleared (submitted blank):

- Redirects to `/profile` (302)
- The row's `description` is now `NULL` in the DB

`GET /profile` — authenticated:

- Response body contains an "Edit" link for each transaction row, with the `href` produced by `url_for('edit_expense', id=...)`

## Definition of done

- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for an expense that belongs to the current user shows a form pre-filled with that expense's current values
- [ ] Visiting `/expenses/<id>/edit` for an expense that belongs to another user returns 404 (not 403)
- [ ] Visiting `/expenses/<id>/edit` for a non-existent id returns 404
- [ ] Submitting a valid edit redirects to `/profile` and the row in the DB reflects the new values
- [ ] Submitting with a missing or zero amount re-renders the form with an error and previously entered values retained
- [ ] Submitting with an invalid category re-renders the form with an error
- [ ] Submitting with an invalid date re-renders the form with an error
- [ ] Submitting a blank description clears the description in the DB (stored as `NULL`)
- [ ] The recent transactions list on the profile page shows an "Edit" link for each row, built via `url_for('edit_expense', id=...)`
- [ ] All new DB access goes through `db/db.py` (`update_expense`) and uses parameterised `?` placeholders
