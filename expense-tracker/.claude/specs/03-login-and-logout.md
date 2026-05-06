# Spec: Login and Logout

## Overview
Implement session-based login and logout so registered users can authenticate with Spendly. This step wires up the existing `GET /login` stub into a full login flow: the form collects email and password, the server validates credentials against the `users` table using werkzeug's `check_password_hash`, stores the user's `id` and `name` in Flask's signed cookie session, and redirects to a minimal dashboard on success. The `GET /logout` stub is replaced with a handler that clears the session and redirects to the landing page. A simple `GET /dashboard` route (placeholder for future steps) acts as the post-login landing zone.

## Depends on
- Step 01 — Database Setup: `users` table and `get_db()` must be in place.
- Step 02 — Registration: at least one user must exist in the database to test login.

## Routes
- `GET /login` — Render the login form — public (already exists, upgrading from stub)
- `POST /login` — Validate credentials, set session, redirect to dashboard — public
- `GET /logout` — Clear session, redirect to landing page — public (already exists as placeholder)
- `GET /dashboard` — Render the post-login dashboard — logged-in only (new)

## Database changes
No database changes. The `users` table already has `id`, `email`, and `password_hash`, which are all that login requires.

## Templates
- **Modify:** `templates/login.html` — replace static placeholder with a real form (email and password fields); display flashed error/success messages
- **Create:** `templates/dashboard.html` — minimal logged-in landing page showing a welcome message, the user's name, and a logout link

## Files to change
- `app.py` — add `session` to Flask imports; add `check_password_hash` to werkzeug imports; implement `POST /login`; replace `GET /logout` stub; add `GET /dashboard` route
- `templates/login.html` — real form with email, password fields and flash message rendering

## Files to create
- `templates/dashboard.html` — new template extending `base.html`

## New dependencies
No new dependencies. `werkzeug.security` and `flask.session` are already available.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use string formatting in SQL
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plaintext
- Use CSS variables — never hardcode hex values in templates or stylesheets
- All templates extend `base.html`
- Store only `user_id` and `user_name` in `session` — never store the password hash or full user row
- On failed login show a generic error ("Invalid email or password") — do not distinguish between unknown email and wrong password
- After successful login redirect to `url_for('dashboard')`
- After logout clear the entire session with `session.clear()` and redirect to `url_for('landing')`
- Protect `GET /dashboard` with an inline session check: if `session.get('user_id')` is falsy, redirect to `url_for('login')`
- `app.secret_key` is already set in `app.py` — do not change it
- make sure to not again access /login and /register once user logged in

## Definition of done
- [ ] `GET /login` renders a form with email and password fields
- [ ] Submitting valid credentials sets the session and redirects to `/dashboard`
- [ ] `/dashboard` displays the logged-in user's name
- [ ] Submitting an unknown email shows: "Invalid email or password"
- [ ] Submitting a correct email with the wrong password shows: "Invalid email or password"
- [ ] Submitting empty email or password shows a validation error before hitting the database
- [ ] `GET /logout` clears the session and redirects to the landing page (`/`)
- [ ] Visiting `/dashboard` without being logged in redirects to `/login`
- [ ] After logout, visiting `/dashboard` redirects to `/login`
- [ ] App starts without errors after changes to `app.py`
