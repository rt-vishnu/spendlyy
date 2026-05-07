import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
# Import database helpers
from database.db import get_db, init_db, seed_db, close_db

app = Flask(__name__)
app.secret_key = 'dev-secret-change-me'
app.teardown_appcontext(close_db)

# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name:
            return render_template("register.html", error="Name is required.", name=name, email=email)
        if not email:
            return render_template("register.html", error="Email is required.", name=name, email=email)
        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters.", name=name, email=email)
        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match.", name=name, email=email)

        password_hash = generate_password_hash(password)
        try:
            db = get_db()
            db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return render_template("register.html", error="An account with that email already exists.", name=name, email=email)

        flash("Account created! Sign in to continue.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="Email and password are required.", email=email)

        db = get_db()
        row = db.execute(
            "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()

        if row is None or not check_password_hash(row["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.", email=email)

        session.clear()
        session["user_id"] = row["id"]
        session["user_name"] = row["name"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("dashboard.html", user_name=session["user_name"])


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    user = {
        "name": "Raviteja Vishnubhotla",
        "email": "ravi@spendly.com",
        "initials": "RV",
        "member_since": "January 15, 2026",
    }
    stats = {
        "total_spent": "₹247.64",
        "transactions": 8,
        "top_category": "Food",
    }
    expenses = [
        {"date": "May 07, 2026", "description": "Snack",              "category": "Food",          "amount": "₹9.80"},
        {"date": "May 06, 2026", "description": "New shoes",          "category": "Shopping",      "amount": "₹55.25"},
        {"date": "May 05, 2026", "description": "Movie ticket",       "category": "Entertainment", "amount": "₹15.00"},
        {"date": "May 04, 2026", "description": "Doctor appointment", "category": "Health",        "amount": "₹40.00"},
        {"date": "May 03, 2026", "description": "Electricity bill",   "category": "Bills",         "amount": "₹85.00"},
        {"date": "May 02, 2026", "description": "Bus fare",           "category": "Transport",     "amount": "₹7.50"},
        {"date": "May 01, 2026", "description": "Lunch at cafe",      "category": "Food",          "amount": "₹12.99"},
    ]
    categories = [
        {"name": "Bills",         "amount": "₹85.00", "pct": 34, "bar_class": "bar-bills"},
        {"name": "Shopping",      "amount": "₹55.25", "pct": 22, "bar_class": "bar-shopping"},
        {"name": "Health",        "amount": "₹40.00", "pct": 16, "bar_class": "bar-health"},
        {"name": "Food",          "amount": "₹22.79", "pct": 9,  "bar_class": "bar-food"},
        {"name": "Entertainment", "amount": "₹15.00", "pct": 6,  "bar_class": "bar-entertainment"},
        {"name": "Transport",     "amount": "₹7.50",  "pct": 3,  "bar_class": "bar-travel"},
    ]
    return render_template("profile.html", user=user, stats=stats, expenses=expenses, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    # Ensure the database is ready before starting the server
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
