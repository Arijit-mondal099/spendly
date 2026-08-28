---
paths:
  - "app.py"
  - "db/db.py"
---

# Security Rules

- Passwords are hashed with `werkzeug.security.generate_password_hash` before storage and verified with `check_password_hash`. Never store or compare plaintext passwords.
- Session data is set via Flask's `session` object only — no custom cookie handling, no tokens stored client-side.
- `/logout` must call `session.clear()`, not just remove individual keys.
- Any route that reads `session['user_id']` (or similar) to gate access must check it's present and `abort(401)` or redirect to `/login` if not — never assume the key exists.
- Never log or print raw request form data on `/register` or `/login` (it may contain passwords).
