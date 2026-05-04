import sqlite3
from flask import g
from werkzeug.security import generate_password_hash

# Database file name
DB_FILE = "spendly.db"

# ----- Core Functions -----

def get_db():
    """Return a SQLite connection with row factory and foreign keys enabled.

    The connection is stored in Flask's :data:`g` so it is reused for the
    duration of the request and closed automatically when the request ends.
    """
    if "db" not in g:
        conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        # Ensure foreign key enforcement for the lifetime of the connection
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def init_db():
    """Create the `users` and `expenses` tables if they do not already exist."""
    db = get_db()
    cursor = db.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    db.commit()


def seed_db():
    """Insert a demo user and 8 sample expenses.

    The function checks whether the `users` table already contains rows and
    returns early if data exists to avoid duplicates.
    """
    db = get_db()
    cursor = db.cursor()
    # If any rows in users, skip seeding
    cursor.execute("SELECT 1 FROM users LIMIT 1")
    if cursor.fetchone():
        return

    # Insert a demo user
    demo_name = "Demo User"
    demo_email = "demo@spendly.com"
    demo_password = "demo123"
    password_hash = generate_password_hash(demo_password)
    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (demo_name, demo_email, password_hash),
    )
    demo_user_id = cursor.lastrowid

    # Eight sample expenses covering the 7 categories from the spec
    sample_expenses = [
        # Food
        (demo_user_id, 12.99, "Food", "2026-05-01", "Lunch at cafe"),
        # Transport
        (demo_user_id, 7.50, "Transport", "2026-05-02", "Bus fare"),
        # Bills
        (demo_user_id, 85.00, "Bills", "2026-05-03", "Electricity bill"),
        # Health
        (demo_user_id, 40.00, "Health", "2026-05-04", "Doctor appointment"),
        # Entertainment
        (demo_user_id, 15.00, "Entertainment", "2026-05-05", "Movie ticket"),
        # Shopping
        (demo_user_id, 55.25, "Shopping", "2026-05-06", "New shoes"),
        # Other
        (demo_user_id, 22.10, "Other", "2026-05-07", "Misc. expense"),
        # One more Food to have two Food entries
        (demo_user_id, 9.80, "Food", "2026-05-08", "Snack"),
    ]

    for expense in sample_expenses:
        cursor.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            expense,
        )

    db.commit()

# Optional: close the connection when Flask teardown
# Register close_db with Flask app context properly.
# It should be attached at runtime after app creation; here we just expose the function.

def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

