# Spec: Date Filter for Recent Transactions in Profile Page

## Overview

Step 6 adds a date-range filter to the **Recent transactions** section of the
`/profile` page so the user can narrow the table to a specific period (last
7 days, last 30 days, last 90 days, this month, this year, or a fully custom
range). The filter is a simple `<form method="get">` with two date inputs and
a submit button — no JavaScript required. The chosen range is preserved by
re-rendering the same inputs with their submitted values. The "all time"
range remains the default so existing users see no behaviour change. Only the
transaction list and the summary stats are re-scoped by the filter; the user
info card and the category breakdown are unchanged in this step.

## Depends on

- Step 1: Database setup (tables and `get_db()` exist)
- Step 4: Profile page UI (transaction table and stat cards already exist)
- Step 5: Profile backend connection (`get_recent_transactions()`,
  `get_summary_stats()`, `get_category_breakdown()` already exist)

## Routes

No new routes. The existing `GET /profile` route is modified to:

- Read optional `start` and `end` query-string parameters (ISO `YYYY-MM-DD`)
- Pass the parsed range to the queries that scope by date
- Echo the submitted range back to the template so the filter controls can
  re-render with the user's last selection

## Database changes

No database changes. The `expenses` table already has a `date TEXT` column
suitable for range filtering.

## Templates

- **Modify**: `templates/profile.html`
  - Wrap the "Recent transactions" section title row with a small
    `<form method="get">` that contains two `<input type="date">` controls
    (`name="start"`, `name="end"`), a submit button labelled "Apply", and
    a "Clear" link that points back to `/profile` with no query string
  - Echo submitted `start` / `end` values into the `value` attributes of
    the date inputs so the selection persists across the page reload
  - Show a small inline message ("No transactions in this date range")
    when the filtered result is empty
  - Show a small "Showing X of Y transactions" hint above the table when a
    filter is active and the result is non-empty

No other templates change.

## Files to change

- `app.py` — parse `start` / `end` from `request.args`, validate them,
  pass the range into `get_recent_transactions()` and
  `get_summary_stats()`, and forward the active range to the template
- `db/queries.py` — extend `get_recent_transactions()` and
  `get_summary_stats()` with optional `start` / `end` keyword arguments
  that add a `WHERE date BETWEEN ? AND ?` clause when supplied
- `templates/profile.html` — add filter form, submit button, clear link,
  empty-state message, and result-count hint
- `static/css/profile.css` — minimal styles for the filter form layout
  (form row, inputs, buttons); reuse existing design tokens only

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Foreign keys PRAGMA must remain enabled on every connection
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must still display as ₹ — never £ or $
- `get_recent_transactions(user_id, limit=10, start=None, end=None)` —
  when `start` is provided, filter `date >= start`; when `end` is
  provided, filter `date <= end`; combine with `AND` if both are present
- `get_summary_stats(user_id, start=None, end=None)` — apply the same
  `WHERE date BETWEEN ? AND ?` (or its half-open variants) so the
  "Total spent", "Transactions", and "Top category" tiles reflect the
  filtered set
- `get_category_breakdown()` is **not** scoped by date in this step —
  the breakdown continues to reflect all-time spend
- `request.args.get("start")` and `request.args.get("end")` are treated
  as optional; missing or empty strings mean "no bound on that side"
- Invalid date strings (anything that fails `date.fromisoformat`) are
  silently ignored — the form re-renders with the offending field empty
  rather than raising
- The filter form must be a normal HTML form using `method="get"` so the
  URL is shareable and bookmarkable; no JavaScript required
- The "Clear" link is a plain `url_for("profile")` with no query string
  — never a hash link
- Route keeps the existing session/redirect guard intact
- The total-spend / count / top-category note text on the stat cards
  should still read sensibly when the filter is active (e.g.
  "in this date range" instead of "all time")

## Definition of done

- [ ] Visiting `/profile` with no query string shows the full transaction list and the all-time summary stats — behaviour is unchanged from Step 5
- [ ] Visiting `/profile?start=YYYY-MM-DD&end=YYYY-MM-DD` shows only expenses whose `date` falls inside the range (inclusive on both ends)
- [ ] The "Total spent" and "Transactions" stat cards reflect the filtered set, not all-time totals
- [ ] The "Top category" stat card reflects the filtered set
- [ ] The "Spending by category" section continues to show all-time breakdown (unchanged)
- [ ] The filter form re-renders with the user's last `start` / `end` selection
- [ ] Clicking the "Clear" link returns to `/profile` with no filter applied
- [ ] Submitting an invalid date string (e.g. `start=not-a-date`) does not raise — the page re-renders with that field empty
- [ ] When the filter produces an empty result, the table area shows "No transactions in this date range"
- [ ] All existing tests in `tests/test_backend_connection.py` still pass
