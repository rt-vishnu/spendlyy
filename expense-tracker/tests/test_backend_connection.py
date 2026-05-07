import pytest
from app import app as flask_app
import database.db as db_module
from database.db import init_db, seed_db
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)

_ORIGINAL_DB = db_module.DB_FILE


@pytest.fixture
def app(tmp_path):
    db_module.DB_FILE = str(tmp_path / "test.db")
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    with flask_app.app_context():
        init_db()
        seed_db()
    yield flask_app
    db_module.DB_FILE = _ORIGINAL_DB


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_user_id(app):
    with app.app_context():
        db = db_module.get_db()
        row = db.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()
        return row["id"]


# ── Unit tests: get_user_by_id ──────────────────────────────────────────────

def test_get_user_by_id_valid(app, seed_user_id):
    with app.app_context():
        user = get_user_by_id(seed_user_id)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["initials"] == "DU"
    assert "member_since" in user


def test_get_user_by_id_nonexistent(app):
    with app.app_context():
        result = get_user_by_id(99999)
    assert result is None


# ── Unit tests: get_summary_stats ───────────────────────────────────────────

def test_get_summary_stats_with_expenses(app, seed_user_id):
    with app.app_context():
        stats = get_summary_stats(seed_user_id)
    assert stats["transactions"] == 8
    assert stats["total_spent"] == "₹247.64"
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(app):
    with app.app_context():
        db = db_module.get_db()
        db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                   ("Empty User", "empty@test.com", "hash"))
        db.commit()
        new_id = db.execute("SELECT id FROM users WHERE email = ?", ("empty@test.com",)).fetchone()["id"]
        stats = get_summary_stats(new_id)
    assert stats["transactions"] == 0
    assert stats["total_spent"] == "₹0.00"
    assert stats["top_category"] == "—"


# ── Unit tests: get_recent_transactions ─────────────────────────────────────

def test_get_recent_transactions_with_expenses(app, seed_user_id):
    with app.app_context():
        txns = get_recent_transactions(seed_user_id)
    assert len(txns) == 8
    for t in txns:
        assert "date" in t
        assert "description" in t
        assert "category" in t
        assert t["amount"].startswith("₹")
    assert txns[0]["date"] == "2026-05-08"


def test_get_recent_transactions_no_expenses(app):
    with app.app_context():
        db = db_module.get_db()
        db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                   ("Empty2 User", "empty2@test.com", "hash"))
        db.commit()
        new_id = db.execute("SELECT id FROM users WHERE email = ?", ("empty2@test.com",)).fetchone()["id"]
        txns = get_recent_transactions(new_id)
    assert txns == []


# ── Unit tests: get_category_breakdown ──────────────────────────────────────

def test_get_category_breakdown_with_expenses(app, seed_user_id):
    with app.app_context():
        cats = get_category_breakdown(seed_user_id)
    assert len(cats) == 7
    assert sum(c["pct"] for c in cats) == 100
    assert cats[0]["name"] == "Bills"
    for c in cats:
        assert c["amount"].startswith("₹")
        assert isinstance(c["pct"], int)
        assert "bar_class" in c


def test_get_category_breakdown_no_expenses(app):
    with app.app_context():
        db = db_module.get_db()
        db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                   ("Empty3 User", "empty3@test.com", "hash"))
        db.commit()
        new_id = db.execute("SELECT id FROM users WHERE email = ?", ("empty3@test.com",)).fetchone()["id"]
        cats = get_category_breakdown(new_id)
    assert cats == []


# ── Route tests ──────────────────────────────────────────────────────────────

def test_profile_unauthenticated(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_authenticated_seed_user(client, app, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body
    assert "247.64" in body
    assert "Bills" in body


def test_profile_new_user_no_crash(client, app):
    with app.app_context():
        db = db_module.get_db()
        db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                   ("New User", "new@test.com", "hash"))
        db.commit()
        new_id = db.execute("SELECT id FROM users WHERE email = ?", ("new@test.com",)).fetchone()["id"]
    with client.session_transaction() as sess:
        sess["user_id"] = new_id
        sess["user_name"] = "New User"
    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "₹0.00" in body
