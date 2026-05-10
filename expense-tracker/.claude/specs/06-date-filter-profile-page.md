# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date-range filter to the profile page so users can narrow the
transactions list, summary stats, and category breakdown to a specific period.
A compact filter bar sits above the stats with preset quick-picks (This Month,
Last Month, Last 3 Months, This Year) and a custom date-range picker (start
date / end date). Selecting any filter reloads the page with query-string
parameters (`from` and `to`); all four data sections update accordingly. This
is a pure server-side feature — no JavaScript required beyond the date
inputs' native browser behaviour.

## Depends on
- Step 1: Database setup (`expenses` table with `date TEXT` column exists)
- Step 2: Registration (users exist)
- Step 3: Login / Logout (`session["user_id"]` is set)
- Step 4: Profile page static UI (template structure in place)
- Step 5: Backend routes for profile page (`get_summary_stats`, `get_recent_transactions`, `get_category_breakdown` exist in `database/queries.py`)

## Routes
- `GET /profile` — extended with optional query params `from` and `to` (ISO date strings `YYYY-MM-DD`) — logged-in only

No new routes.

## Database changes
No database changes. The `expenses.date` column (`TEXT`, `YYYY-MM-DD`) already
supports range filtering via SQL `BETWEEN`.

## Templates
- **Modify**: `templates/profile.html`
  - Add a filter bar section above `.dashboard-stats` containing:
    - Four preset buttons: This Month, Last Month, Last 3 Months, This Year
    - A custom range form with two `<input type="date">` fields (From / To) and a Apply button
    - An active-filter label that shows the currently applied range when one is set (e.g. "Showing: 2026-04-01 → 2026-04-30")
    - A "Clear filter" link that navigates back to `/profile` (no params)
  - Each preset is a `<a>` link to `/profile?from=YYYY-MM-DD&to=YYYY-MM-DD` with dates computed in the route
  - The custom range form submits `GET /profile` with `from` and `to` fields
  - Preset link for the active period should have the `active` CSS class applied
  - The transactions table and category breakdown already use `{{ expenses }}` and `{{ categories }}` — no structural changes needed there

## Files to change
- `app.py` — update `profile()` route to:
  - Read `from` and `to` from `request.args`
  - Validate and sanitise both values (must match `YYYY-MM-DD` or be absent)
  - Pass validated `date_from` / `date_to` into all four query helpers
  - Compute preset date ranges (This Month, Last Month, Last 3 Months, This Year) and pass them to the template as `presets` dict so the template can build links without any Python in the template
  - Pass `active_from` and `active_to` back to the template so the active-filter label and active preset highlighting work
- `database/queries.py` — update all three data-query functions to accept optional `date_from` and `date_to` parameters:
  - `get_summary_stats(user_id, date_from=None, date_to=None)`
  - `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)`
  - `get_category_breakdown(user_id, date_from=None, date_to=None)`
  - When both are provided add `AND date BETWEEN ? AND ?` to the WHERE clause using parameterised queries; when absent the queries behave exactly as before

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles (the `style="width: {{ cat.pct }}%"` on the chart bar is the existing exception and must remain)
- Currency always displays as ₹ — never £ or $
- Date validation in `app.py` must use `datetime.strptime` with format `%Y-%m-%d`; invalid values are silently ignored (treated as absent) rather than returning a 400
- Preset date ranges are computed in `app.py` using `datetime.date.today()` — never hardcoded
- The filter bar must be visible on the profile page even when no filter is active
- When no filter is active, all sections show the user's full expense history (existing behaviour)
- The "Clear filter" link must only be rendered when at least one of `active_from` / `active_to` is set

## Definition of done
- [ ] Visiting `/profile` with no query params shows the full expense history (same as Step 5 behaviour — no regression)
- [ ] Clicking "This Month" filters all three sections to the current calendar month only
- [ ] Clicking "Last Month" filters all three sections to the previous calendar month only
- [ ] Clicking "Last 3 Months" filters all three sections to the past 3 months only
- [ ] Clicking "This Year" filters all three sections to the current calendar year only
- [ ] Entering a custom From / To date and clicking Apply filters correctly
- [ ] The active-filter label shows the active date range when a filter is applied
- [ ] The active preset button is visually highlighted (has CSS `active` class)
- [ ] The "Clear filter" link appears only when a filter is active and returns to the unfiltered profile
- [ ] Summary stats (total spent, transaction count, top category) update to reflect only the filtered expenses
- [ ] Category breakdown updates to reflect only the filtered expenses (percentages still sum to 100%)
- [ ] An invalid `from` or `to` query param (e.g. `?from=notadate`) is silently ignored and the full history is shown
- [ ] A new user with no expenses sees an empty state with no errors when any filter is applied
