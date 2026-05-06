# Spec: Registration

## Overview
Implement user registration so new visitors can create a Spendly account. This step wires up the existing `GET /register` stub into a fully functional signup flow: the form collects name, email, and password; the server validates the input, hashes the password with werkzeug, inserts the new user into the `users` table, and redirects to the login page on success. Flash messages surface inline errors (duplicate email, mismatched passwords, empty fields) without a full page reload cycle.

## Depends on
- Step 01 — Database Setup: `users` table and `get_db()` must be in place.

## Routes
- `GET /register` — Render the registration form — public (already exists, no change needed)
- `POST /register` — Validate form data, insert user, redirect — public

## Database changes
No database changes. The `users` table from Step 01 already has the required columns (`name`, `email`, `password_hash`, `created_at`). The UNIQUE constraint on `email` handles duplicate detection at the DB level.

## Templates
- **Modify:** `templates/register.html` — replace static placeholder with a real form (name, email, password, confirm password fields); display flashed error/success messages
- **Modify:** `templates/base.html` — add a flash message display block (one place, reused by all pages)

## Files to change
- `app.py` — add `POST /register` route; import `request`, `redirect`, `url_for`, `flash`, `session`; set `app.secret_key`
- `templates/register.html` — real form + flash message rendering
- `templates/base.html` — flash message block

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security` is already installed with Flask.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` — never store plaintext
- Use CSS variables — never hardcode hex values in templates or stylesheets
- All templates extend `base.html`
- `app.secret_key` must be set for `flash()` to work — use a hard-coded dev string for now (e.g. `"dev-secret-change-me"`)
- Catch `sqlite3.IntegrityError` to detect duplicate email — do not rely solely on a pre-check `SELECT`
- After successful registration redirect to `url_for('login')` with a success flash message
- Validate server-side: name non-empty, valid email format (basic check), password ≥ 6 chars, passwords match

## Definition of done
- [ ] `GET /register` renders the form with name, email, password, and confirm-password fields
- [ ] Submitting valid details creates a new row in `users` with a hashed password
- [ ] Submitting a duplicate email shows an inline error: "An account with that email already exists"
- [ ] Submitting mismatched passwords shows an inline error: "Passwords do not match"
- [ ] Submitting an empty name or email shows an appropriate inline error
- [ ] Submitting a password shorter than 6 characters shows an inline error
- [ ] Successful registration redirects to `/login` with a success message visible
- [ ] Flash messages are visible on the page (not only in the console)
- [ ] App starts without errors after changes to `app.py`
- [ ] No plaintext passwords exist in `spendly.db` after registration
