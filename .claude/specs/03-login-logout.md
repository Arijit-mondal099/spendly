# Spec: Login and Logout

## Overview

Step 3 adds session-based authentication to Spendly: users can sign in with the
email and password they registered in Step 2, and sign out again. Until now the
app could create accounts but could not recognise who was using it — `POST /login`
did not exist and `GET /logout` was a raw-string stub. This step wires the existing
`login.html` form to a real authentication flow, introduces Flask session handling
(the first use of `session` and of an `app.secret_key` in the project), replaces the
logout stub with a real route, and makes the navbar reflect the signed-in state so
logout is reachable from the UI.

## Depends on

- **Step 1 — Database Setup**: `users` table with `password_hash` column,
  `get_user_by_email()` helper in `db/db.py`.
- **Step 2 — Registration**: registered users to log in as, werkzeug hashing
  convention (`generate_password_hash`), and the existing `login.html` page.

## Routes

- `POST /login` — authenticate email + password, start a session, redirect to the
  landing page on success; re-render `login.html` with a generic error on failure — guest-only
- `GET /login` — renders `login.html`, now wired for error display and email refill — guest-only
- `GET /register` — existing route gains a guard: signed-in users are redirected to
  the landing page — guest-only
- `GET /logout` — replace the raw-string stub: clear the session, redirect to the
  login page — logged-in (must redirect safely even when not logged in)

Guest-only means: when `session.user_id` exists, GET *and* POST requests are
redirected to the landing page before any form handling. Signed-out users have
normal access.

No other routes are added or changed in this step.

## Database changes

No database changes. The `users` table already stores `password_hash`, and the
existing `db/db.py` helpers (`get_user_by_email`) cover every query this step
needs. Password verification happens with `werkzeug.security.check_password_hash`
against the stored hash — no new columns, tables, or helper functions required.

## Templates

- **Create:** none
- **Modify:**
  - `templates/login.html` — fix the hardcoded `action="/login"` to
    `action="{{ url_for('login') }}"`; confirm the existing `{% if error %}`
    block displays the generic error and the email field refills from the
    value passed by the POST handler.
  - `templates/base.html` — make the navbar session-aware: when
    `session.user_id` exists show a "Log out" link (`url_for('logout')`);
    otherwise show the current "Sign in" / "Get started" links unchanged.

## Files to change

- `app.py` — add `secret_key` (generated once at startup via `secrets.token_hex`),
  import `session` from flask and `check_password_hash` from werkzeug.security,
  implement `POST /login` inside the existing `login()` view, replace the
  `logout()` stub body, and add a guest-only guard redirecting signed-in users
  from both auth views (`/login`, `/register`) to the landing page.
- `templates/login.html` — `url_for()` fix as above.
- `templates/base.html` — conditional navbar as above.

## Files to create

None.

## New dependencies

No new dependencies. `secrets` is Python standard library.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug — verify with `check_password_hash`, never compare plaintext to the hash column
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Session storage holds `user_id` only — nothing else about the user
- Set `app.secret_key` with `secrets.token_hex()` in `app.py`; do not introduce config files or env-var plumbing for it at this stage
- All database access goes through existing `db/db.py` helpers — no SQL in routes, no new DB functions
- Follow the established `register()` conventions: validate → call DB helper → render with an `error` template variable or redirect; no flash messages
- On failed login show one generic message ("Invalid email or password.") whether the email is unknown or the password is wrong — never reveal which
- Every internal link uses `url_for()`; never hardcode URLs
- Keep the app on port `5001`; do not touch the untouched stub routes (`/profile`, `/expenses/*`)

## Definition of done

Each item verified by running `python app.py` and exercising the app:

1. Server starts on port 5001 with no errors.
2. `GET /login` renders the sign-in form; submitting the seeded demo account
   (`demo@spendly.com` / `demo123`) redirects to the landing page.
3. Submitting a wrong password shows "Invalid email or password.", stays on the
   login page, and the email field keeps the entered value.
4. Submitting an unregistered email shows the same generic message — identical
   wording and styling to case 3.
5. After signing in, the navbar shows "Log out" instead of "Sign in"/"Get started".
6. Clicking "Log out" returns the navbar to the signed-out state, and revisiting
   `/logout` while signed out simply redirects to `/login` without erroring.
7. Signing in, signing out, then signing in again works repeatedly in the same
   browser session.
8. The registration flow works for signed-out visitors exactly as before; a
   signed-in visitor visiting `/register` is redirected to the landing page.
9. While signed in, visiting `/login` (GET or POST) also redirects to the landing
   page; after signing out, both auth pages render normally again.
10. `pytest` exits clean (no regressions; test suite may still be empty).
