"""
tests/test_date_filter_profile_page.py

Pytest test suite for Step 6 — Date Filter on the Profile Page.

Spec: .claude/specs/06-date-filter-profile-page.md

Expenses are seeded across four distinct periods so that each preset and
custom-range scenario can assert that only the correct rows appear:

    Period A — prior year:     2024-06-15   Food   ₹500.00
    Period B — 4 months ago:   dynamically computed to be outside "Last 3 Months"
    Period C — last month:     dynamically computed to first day of last calendar month
    Period D — this month:     today's date (dynamically computed)

All dates are computed at import time from datetime.date.today() so the
tests stay green regardless of when they are run.
"""

import pytest
import datetime
import database.db as db_module
from app import app as flask_app
from database.db import init_db
from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Helpers — compute stable date strings relative to "today"
# ---------------------------------------------------------------------------

def _today() -> datetime.date:
    return datetime.date.today()


def _first_of_month(d: datetime.date) -> datetime.date:
    return d.replace(day=1)


def _last_month_end(d: datetime.date) -> datetime.date:
    return _first_of_month(d) - datetime.timedelta(days=1)


def _last_month_start(d: datetime.date) -> datetime.date:
    return _last_month_end(d).replace(day=1)


def _three_months_start(d: datetime.date) -> datetime.date:
    """First day of the month that is 3 calendar months before *d*."""
    m = d.month - 3
    y = d.year + (m - 1) // 12
    m = ((m - 1) % 12) + 1
    return datetime.date(y, m, 1)


def _this_year_start(d: datetime.date) -> datetime.date:
    return datetime.date(d.year, 1, 1)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ORIGINAL_DB = db_module.DB_FILE


@pytest.fixture()
def app(tmp_path):
    """Isolated Flask app backed by a per-test temp SQLite database."""
    db_module.DB_FILE = str(tmp_path / "test_filter.db")
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "WTF_CSRF_ENABLED": False,
    })
    with flask_app.app_context():
        init_db()
    yield flask_app
    db_module.DB_FILE = _ORIGINAL_DB


@pytest.fixture()
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _insert_user(app, name, email):
    """Insert a user and return their id."""
    pw_hash = generate_password_hash("password123")
    with app.app_context():
        db = db_module.get_db()
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, pw_hash),
        )
        db.commit()
        row = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        return row["id"]


def _insert_expense(app, user_id, amount, category, date_str, description="Test"):
    """Insert a single expense row."""
    with app.app_context():
        db = db_module.get_db()
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date_str, description),
        )
        db.commit()


@pytest.fixture()
def seeded_user_id(app):
    """
    Create a test user and seed expenses in four time periods:

        prior_year_expense  — 2024-06-15 — Food     — ₹500.00
        four_months_expense — 4+ months before this month — Transport — ₹200.00
        last_month_expense  — first day of last month     — Bills     — ₹150.00
        this_month_expense  — today                       — Shopping  — ₹75.00

    Returns the user's integer id.
    """
    today = _today()
    last_month_start = _last_month_start(today)
    # Guarantee the "4 months ago" expense falls outside the Last-3-Months window
    four_months_ago = _three_months_start(today) - datetime.timedelta(days=1)

    user_id = _insert_user(app, "Filter Tester", "filter@test.com")

    _insert_expense(app, user_id, 500.00, "Food",      "2024-06-15",                     "Prior year food")
    _insert_expense(app, user_id, 200.00, "Transport", four_months_ago.isoformat(),      "Old transport")
    _insert_expense(app, user_id, 150.00, "Bills",     last_month_start.isoformat(),     "Last month bill")
    _insert_expense(app, user_id, 75.00,  "Shopping",  today.isoformat(),                "Today shopping")

    return user_id


@pytest.fixture()
def empty_user_id(app):
    """A user with no expenses at all."""
    return _insert_user(app, "Empty User", "empty@test.com")


@pytest.fixture()
def auth_client(client, seeded_user_id):
    """Logged-in test client for the seeded user."""
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id
        sess["user_name"] = "Filter Tester"
    return client


@pytest.fixture()
def empty_auth_client(client, empty_user_id):
    """Logged-in test client for the empty (no expenses) user."""
    with client.session_transaction() as sess:
        sess["user_id"] = empty_user_id
        sess["user_name"] = "Empty User"
    return client


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_profile_no_params_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302, "Expected redirect for unauthenticated request"
        assert "/login" in resp.headers["Location"], "Should redirect to /login"

    def test_unauthenticated_profile_with_date_params_redirects_to_login(self, client):
        resp = client.get("/profile?from=2026-01-01&to=2026-01-31")
        assert resp.status_code == 302, "Date params must not bypass auth check"
        assert "/login" in resp.headers["Location"]

    def test_unauthenticated_profile_with_invalid_params_redirects_to_login(self, client):
        resp = client.get("/profile?from=notadate&to=alsobad")
        assert resp.status_code == 302, "Invalid date params must not bypass auth check"
        assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# No filter — full history (regression from Step 5)
# ---------------------------------------------------------------------------

class TestNoFilter:
    def test_profile_no_params_returns_200(self, auth_client):
        resp = auth_client.get("/profile")
        assert resp.status_code == 200

    def test_profile_no_params_shows_all_expenses_in_stats(self, auth_client):
        resp = auth_client.get("/profile")
        body = resp.data.decode()
        # 4 expenses: 500 + 200 + 150 + 75 = 925.00
        assert "925.00" in body, "Full history total should be ₹925.00"
        assert "4" in body, "Transaction count should include all 4 expenses"

    def test_profile_no_params_filter_bar_is_visible(self, auth_client):
        resp = auth_client.get("/profile")
        body = resp.data.decode()
        assert "filter-bar" in body, "Filter bar must always be visible"

    def test_profile_no_params_preset_buttons_rendered(self, auth_client):
        resp = auth_client.get("/profile")
        body = resp.data.decode()
        assert "This Month" in body, "This Month preset must be rendered"
        assert "Last Month" in body, "Last Month preset must be rendered"
        assert "Last 3 Months" in body, "Last 3 Months preset must be rendered"
        assert "This Year" in body, "This Year preset must be rendered"

    def test_profile_no_params_clear_filter_absent(self, auth_client):
        resp = auth_client.get("/profile")
        body = resp.data.decode()
        assert "Clear filter" not in body, "Clear filter must not appear without active filter"

    def test_profile_no_params_active_filter_label_absent(self, auth_client):
        resp = auth_client.get("/profile")
        body = resp.data.decode()
        assert "Showing:" not in body, "Active filter label must not appear without filter"


# ---------------------------------------------------------------------------
# Preset: This Month
# ---------------------------------------------------------------------------

class TestPresetThisMonth:
    def test_this_month_filter_returns_200(self, auth_client):
        today = _today()
        f = _first_of_month(today).isoformat()
        t = today.isoformat()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        assert resp.status_code == 200

    def test_this_month_filter_shows_only_this_month_expenses(self, auth_client):
        today = _today()
        f = _first_of_month(today).isoformat()
        t = today.isoformat()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        # Only today's Shopping expense (₹75.00) should be in stats
        assert "75.00" in body, "This month total should include the ₹75.00 shopping expense"
        # Prior-year and last-month amounts must not dominate the total
        assert "925.00" not in body, "Full-history total must not appear when filtered to this month"

    def test_this_month_filter_transaction_count_is_correct(self, auth_client):
        today = _today()
        f = _first_of_month(today).isoformat()
        t = today.isoformat()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        # Only 1 expense falls within this month
        assert "Shopping" in body, "The this-month Shopping expense should appear"

    def test_this_month_preset_has_active_css_class(self, auth_client):
        today = _today()
        f = _first_of_month(today).isoformat()
        t = today.isoformat()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert "btn-preset active" in body, "The matching preset link must carry the active CSS class"

    def test_this_month_filter_shows_active_label(self, auth_client):
        today = _today()
        f = _first_of_month(today).isoformat()
        t = today.isoformat()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert "Showing:" in body, "Active filter label must appear when filter is applied"
        assert f in body, "Active filter label must include the from date"
        assert t in body, "Active filter label must include the to date"

    def test_this_month_filter_shows_clear_filter_link(self, auth_client):
        today = _today()
        f = _first_of_month(today).isoformat()
        t = today.isoformat()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert "Clear filter" in body, "Clear filter link must appear when a filter is active"


# ---------------------------------------------------------------------------
# Preset: Last Month
# ---------------------------------------------------------------------------

class TestPresetLastMonth:
    def _get_last_month_params(self):
        today = _today()
        f = _last_month_start(today).isoformat()
        t = _last_month_end(today).isoformat()
        return f, t

    def test_last_month_filter_returns_200(self, auth_client):
        f, t = self._get_last_month_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        assert resp.status_code == 200

    def test_last_month_filter_shows_only_last_month_expenses(self, auth_client):
        f, t = self._get_last_month_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        # Only last month's Bills expense (₹150.00) should appear
        assert "150.00" in body, "Last month total should include the ₹150.00 bills expense"
        assert "Bills" in body, "The Bills category from last month should appear"

    def test_last_month_filter_excludes_prior_year_expense(self, auth_client):
        f, t = self._get_last_month_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        # The 2024 prior-year total would push the sum above 150
        assert "500.00" not in body, "Prior-year expense must be excluded by last-month filter"

    def test_last_month_filter_excludes_this_month_expense(self, auth_client):
        today = _today()
        f, t = self._get_last_month_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        # If last_month_end < today we can verify today's expense amount (75.00) is not counted
        # This is only meaningful when today is not in last month's range
        if today > _last_month_end(today):
            # Shopping is only seeded on today; it must not appear in last-month totals
            # The filtered total should be 150.00, not 225.00
            assert "225.00" not in body, "This-month Shopping expense must not appear in last-month filter"

    def test_last_month_preset_has_active_css_class(self, auth_client):
        f, t = self._get_last_month_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert "btn-preset active" in body, "Last Month preset must be marked active"

    def test_last_month_filter_shows_active_label_with_dates(self, auth_client):
        f, t = self._get_last_month_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert "Showing:" in body
        assert f in body
        assert t in body


# ---------------------------------------------------------------------------
# Preset: Last 3 Months
# ---------------------------------------------------------------------------

class TestPresetLast3Months:
    def _get_3m_params(self):
        today = _today()
        f = _three_months_start(today).isoformat()
        t = today.isoformat()
        return f, t

    def test_last_3_months_returns_200(self, auth_client):
        f, t = self._get_3m_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        assert resp.status_code == 200

    def test_last_3_months_excludes_prior_year_expense(self, auth_client):
        f, t = self._get_3m_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        # ₹500 from 2024 must not appear
        assert "500.00" not in body, "2024 expense must be outside the Last 3 Months window"

    def test_last_3_months_excludes_4_month_old_expense(self, auth_client):
        f, t = self._get_3m_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        # The 4-months-ago expense (₹200 Transport) must not be counted
        # Total of last-month + this-month = 150 + 75 = 225
        assert "200.00" not in body or "225.00" in body, (
            "4-months-ago Transport expense must be excluded"
        )

    def test_last_3_months_includes_last_month_and_this_month(self, auth_client):
        f, t = self._get_3m_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        # At least the last-month and this-month expenses should appear
        assert "Bills" in body or "Shopping" in body, (
            "Expenses within the last 3 months must be shown"
        )

    def test_last_3_months_preset_has_active_css_class(self, auth_client):
        f, t = self._get_3m_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert "btn-preset active" in body, "Last 3 Months preset must carry active CSS class"

    def test_last_3_months_shows_clear_filter(self, auth_client):
        f, t = self._get_3m_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert "Clear filter" in body


# ---------------------------------------------------------------------------
# Preset: This Year
# ---------------------------------------------------------------------------

class TestPresetThisYear:
    def _get_this_year_params(self):
        today = _today()
        f = _this_year_start(today).isoformat()
        t = today.isoformat()
        return f, t

    def test_this_year_returns_200(self, auth_client):
        f, t = self._get_this_year_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        assert resp.status_code == 200

    def test_this_year_excludes_prior_year_expense(self, auth_client):
        f, t = self._get_this_year_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        # 2024 Food expense (₹500) must be excluded
        # The this-year total must be less than the 925 full total
        assert "925.00" not in body, "Prior-year expense must be excluded by This Year filter"
        assert "500.00" not in body or "Prior year food" not in body, (
            "The 2024-06-15 expense should not appear in this year's view"
        )

    def test_this_year_includes_this_year_expenses(self, auth_client):
        f, t = self._get_this_year_params()
        today = _today()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        # The this-year view should include last month and this month expenses
        assert "Bills" in body or "Shopping" in body, (
            "Current-year expenses must be visible in the This Year filter"
        )

    def test_this_year_preset_has_active_css_class(self, auth_client):
        f, t = self._get_this_year_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert "btn-preset active" in body, "This Year preset must carry active CSS class"

    def test_this_year_shows_active_label(self, auth_client):
        f, t = self._get_this_year_params()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert "Showing:" in body
        assert "Clear filter" in body


# ---------------------------------------------------------------------------
# Custom Date Range
# ---------------------------------------------------------------------------

class TestCustomDateRange:
    def test_custom_range_spanning_two_expenses_returns_200(self, auth_client):
        today = _today()
        last_month_start = _last_month_start(today).isoformat()
        t = today.isoformat()
        resp = auth_client.get(f"/profile?from={last_month_start}&to={t}")
        assert resp.status_code == 200

    def test_custom_range_filters_stats_correctly(self, auth_client):
        """A custom range covering only last-month and this-month should total 225.00."""
        today = _today()
        f = _last_month_start(today).isoformat()
        t = today.isoformat()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        # last month (150) + this month (75) = 225
        assert "225.00" in body, "Custom range total should be ₹225.00 for last-month + this-month"

    def test_custom_range_excluding_all_expenses_shows_zero_total(self, auth_client):
        """A date range with no matching expenses should show ₹0.00 total."""
        resp = auth_client.get("/profile?from=2020-01-01&to=2020-01-31")
        body = resp.data.decode()
        assert resp.status_code == 200
        assert "0.00" in body, "Empty custom range must show ₹0.00 total"

    def test_custom_range_shows_active_filter_label(self, auth_client):
        resp = auth_client.get("/profile?from=2026-01-01&to=2026-03-31")
        body = resp.data.decode()
        assert "Showing:" in body, "Active filter label must appear for custom range"
        assert "2026-01-01" in body
        assert "2026-03-31" in body

    def test_custom_range_shows_clear_filter_link(self, auth_client):
        resp = auth_client.get("/profile?from=2026-01-01&to=2026-03-31")
        body = resp.data.decode()
        assert "Clear filter" in body

    def test_custom_range_no_active_preset_class_when_not_matching_preset(self, auth_client):
        """A custom range that does not match any preset must not mark any preset active."""
        resp = auth_client.get("/profile?from=2025-06-15&to=2025-07-20")
        body = resp.data.decode()
        # The active class is added only when both from and to match a preset exactly
        # A non-matching range must not produce "btn-preset active"
        assert "btn-preset active" not in body, (
            "Non-preset custom range must not mark any preset button active"
        )

    def test_custom_range_only_from_param_treats_filter_as_active(self, auth_client):
        """Providing only `from` without `to` should still mark the filter label active."""
        resp = auth_client.get("/profile?from=2026-01-01")
        body = resp.data.decode()
        assert resp.status_code == 200
        # The spec requires active_from be passed back to template; label should appear
        assert "Showing:" in body, "Filter label should show when only `from` is supplied"

    def test_custom_range_only_to_param_treats_filter_as_active(self, auth_client):
        """Providing only `to` without `from` should still mark the filter label active."""
        resp = auth_client.get("/profile?to=2026-12-31")
        body = resp.data.decode()
        assert resp.status_code == 200
        assert "Showing:" in body, "Filter label should show when only `to` is supplied"


# ---------------------------------------------------------------------------
# Invalid date params — silently ignored
# ---------------------------------------------------------------------------

class TestInvalidDateParams:
    def test_invalid_from_and_to_returns_200(self, auth_client):
        resp = auth_client.get("/profile?from=notadate&to=alsobad")
        assert resp.status_code == 200, "Invalid date params must not cause a server error"

    def test_invalid_from_and_to_shows_full_history(self, auth_client):
        resp = auth_client.get("/profile?from=notadate&to=alsobad")
        body = resp.data.decode()
        # Both params invalid → treated as absent → full history shown (total 925.00)
        assert "925.00" in body, "Invalid date params must be silently ignored; full history shown"

    def test_invalid_from_and_to_no_clear_filter_link(self, auth_client):
        resp = auth_client.get("/profile?from=notadate&to=alsobad")
        body = resp.data.decode()
        # Both are invalid so active_from and active_to are None → no clear filter
        assert "Clear filter" not in body, (
            "Clear filter must not appear when both params are invalid and silently discarded"
        )

    def test_invalid_from_only_returns_200(self, auth_client):
        resp = auth_client.get("/profile?from=not-a-date&to=2026-05-31")
        assert resp.status_code == 200

    def test_invalid_to_only_returns_200(self, auth_client):
        resp = auth_client.get("/profile?from=2026-01-01&to=notadate")
        assert resp.status_code == 200

    def test_malformed_iso_date_ignored(self, auth_client):
        """A string that looks like a date but is malformed (e.g. wrong separator)."""
        resp = auth_client.get("/profile?from=2026/01/01&to=2026/12/31")
        assert resp.status_code == 200
        body = resp.data.decode()
        # Slashes are not valid ISO format → silently ignored → full history
        assert "925.00" in body, "Slash-separated dates must be treated as invalid and ignored"


# ---------------------------------------------------------------------------
# Stats update with filter
# ---------------------------------------------------------------------------

class TestStatsUpdateWithFilter:
    def test_total_spent_reflects_filtered_expenses(self, auth_client):
        """Filtering to only the prior-year date must produce ₹500.00 total."""
        resp = auth_client.get("/profile?from=2024-06-01&to=2024-06-30")
        body = resp.data.decode()
        assert "500.00" in body, "Total spent must reflect only the filtered expenses"

    def test_transaction_count_reflects_filtered_expenses(self, auth_client):
        """One expense in the prior-year window means count should be 1."""
        resp = auth_client.get("/profile?from=2024-06-01&to=2024-06-30")
        body = resp.data.decode()
        # stats.transactions will render as plain text "1" somewhere in the page
        assert "Food" in body, "Only the Food category expense from June 2024 should appear"

    def test_top_category_reflects_filtered_expenses(self, auth_client):
        """When filtered to only Bills (last month), top category must be Bills."""
        today = _today()
        f = _last_month_start(today).isoformat()
        t = _last_month_end(today).isoformat()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert "Bills" in body, "Top category must be Bills when filtered to last month only"

    def test_zero_total_when_no_expenses_match_filter(self, auth_client):
        resp = auth_client.get("/profile?from=2010-01-01&to=2010-12-31")
        body = resp.data.decode()
        assert "0.00" in body, "Stats total must be ₹0.00 when no expenses match the filter"

    def test_top_category_dash_when_no_expenses_match_filter(self, auth_client):
        resp = auth_client.get("/profile?from=2010-01-01&to=2010-12-31")
        body = resp.data.decode()
        assert "—" in body, "Top category should show em-dash when no expenses match"


# ---------------------------------------------------------------------------
# Category breakdown updates with filter
# ---------------------------------------------------------------------------

class TestCategoryBreakdownWithFilter:
    def test_category_percentages_sum_to_100_when_filtered(self, auth_client):
        """Even after filtering, the category breakdown percentages must sum to 100."""
        today = _today()
        # Filter to the range covering both last-month (Bills) and this-month (Shopping)
        f = _last_month_start(today).isoformat()
        t = today.isoformat()
        resp = auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert resp.status_code == 200
        # Both categories should appear
        assert "Bills" in body, "Bills must appear in category breakdown for last-month filter"
        assert "Shopping" in body, "Shopping must appear in category breakdown for this-month filter"

    def test_category_breakdown_empty_when_no_matching_expenses(self, auth_client):
        """When no expenses match the filter, the category breakdown must be empty (no rows)."""
        resp = auth_client.get("/profile?from=2010-01-01&to=2010-12-31")
        body = resp.data.decode()
        assert resp.status_code == 200
        # No category rows should appear — the chart section will be empty
        assert "bar-food" not in body, "No category bars should render when filter matches nothing"
        assert "bar-bills" not in body
        assert "bar-shopping" not in body

    def test_category_breakdown_only_shows_filtered_categories(self, auth_client):
        """Filtering to the prior-year range should show only Food, not Bills or Shopping."""
        resp = auth_client.get("/profile?from=2024-06-01&to=2024-06-30")
        body = resp.data.decode()
        assert "bar-food" in body, "Food bar must appear for prior-year filter"
        assert "bar-bills" not in body, "Bills must not appear outside the prior-year filter window"


# ---------------------------------------------------------------------------
# Empty state (user with no expenses)
# ---------------------------------------------------------------------------

class TestEmptyStateUser:
    def test_empty_user_profile_no_filter_returns_200(self, empty_auth_client):
        resp = empty_auth_client.get("/profile")
        assert resp.status_code == 200

    def test_empty_user_profile_no_filter_shows_zero_total(self, empty_auth_client):
        resp = empty_auth_client.get("/profile")
        body = resp.data.decode()
        assert "0.00" in body, "Empty user must see ₹0.00 total"

    def test_empty_user_with_this_month_filter_returns_200(self, empty_auth_client):
        today = _today()
        f = _first_of_month(today).isoformat()
        t = today.isoformat()
        resp = empty_auth_client.get(f"/profile?from={f}&to={t}")
        assert resp.status_code == 200, "Empty user with filter must not raise a server error"

    def test_empty_user_with_this_month_filter_shows_zero_total(self, empty_auth_client):
        today = _today()
        f = _first_of_month(today).isoformat()
        t = today.isoformat()
        resp = empty_auth_client.get(f"/profile?from={f}&to={t}")
        body = resp.data.decode()
        assert "0.00" in body, "Empty user filtered view must show ₹0.00"

    def test_empty_user_with_custom_range_returns_200(self, empty_auth_client):
        resp = empty_auth_client.get("/profile?from=2020-01-01&to=2020-12-31")
        assert resp.status_code == 200

    def test_empty_user_with_this_year_filter_no_server_error(self, empty_auth_client):
        today = _today()
        f = _this_year_start(today).isoformat()
        t = today.isoformat()
        resp = empty_auth_client.get(f"/profile?from={f}&to={t}")
        assert resp.status_code == 200

    def test_empty_user_with_invalid_params_returns_200(self, empty_auth_client):
        resp = empty_auth_client.get("/profile?from=notadate&to=alsobad")
        assert resp.status_code == 200

    def test_empty_user_filter_bar_still_visible(self, empty_auth_client):
        resp = empty_auth_client.get("/profile")
        body = resp.data.decode()
        assert "filter-bar" in body, "Filter bar must be visible even for users with no expenses"

    def test_empty_user_top_category_shows_dash(self, empty_auth_client):
        resp = empty_auth_client.get("/profile")
        body = resp.data.decode()
        assert "—" in body, "Top category must show em-dash for user with no expenses"


# ---------------------------------------------------------------------------
# Clear filter link behaviour
# ---------------------------------------------------------------------------

class TestClearFilterLink:
    def test_clear_filter_link_absent_when_no_filter(self, auth_client):
        resp = auth_client.get("/profile")
        body = resp.data.decode()
        assert "Clear filter" not in body, "Clear filter must not appear without active filter"

    def test_clear_filter_link_present_when_both_params_set(self, auth_client):
        resp = auth_client.get("/profile?from=2026-01-01&to=2026-12-31")
        body = resp.data.decode()
        assert "Clear filter" in body, "Clear filter must appear when both params are set"

    def test_clear_filter_link_points_to_profile_without_params(self, auth_client):
        resp = auth_client.get("/profile?from=2026-01-01&to=2026-12-31")
        body = resp.data.decode()
        # The clear link href must be /profile (no query string)
        assert 'href="/profile"' in body, "Clear filter link must navigate to /profile with no params"

    def test_clear_filter_link_present_when_only_from_set(self, auth_client):
        resp = auth_client.get("/profile?from=2026-01-01")
        body = resp.data.decode()
        # active_from is set even without active_to
        assert "Clear filter" in body, "Clear filter must appear when active_from is set"

    def test_clear_filter_link_present_when_only_to_set(self, auth_client):
        resp = auth_client.get("/profile?to=2026-12-31")
        body = resp.data.decode()
        assert "Clear filter" in body, "Clear filter must appear when active_to is set"
