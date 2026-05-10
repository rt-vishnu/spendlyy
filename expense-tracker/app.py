import sqlite3
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
# Import database helpers
from database.db import get_db, init_db, seed_db, close_db
from database.queries import get_recent_transactions, get_user_by_id, get_summary_stats, get_category_breakdown

app = Flask(__name__)
app.secret_key = 'dev-secret-change-me'
app.teardown_appcontext(close_db)


def _parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date() if s else None
    except ValueError:
        return None


def _month_start_n_months_ago(today, n):
    month = today.month - n
    year = today.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    return date(year, month, 1)

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
    user_id = session["user_id"]

    active_from = _parse_date(request.args.get("from"))
    active_to   = _parse_date(request.args.get("to"))
    date_from = active_from.isoformat() if active_from else None
    date_to   = active_to.isoformat()   if active_to   else None

    today = date.today()
    first_this_month = today.replace(day=1)
    last_month_end   = first_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    three_months_start = _month_start_n_months_ago(today, 3)

    presets = {
        "This Month":    (first_this_month.isoformat(), today.isoformat()),
        "Last Month":    (last_month_start.isoformat(), last_month_end.isoformat()),
        "Last 3 Months": (three_months_start.isoformat(), today.isoformat()),
        "This Year":     (date(today.year, 1, 1).isoformat(), today.isoformat()),
    }

    user       = get_user_by_id(user_id)
    stats      = get_summary_stats(user_id, date_from, date_to)
    expenses   = get_recent_transactions(user_id, date_from=date_from, date_to=date_to)
    categories = get_category_breakdown(user_id, date_from, date_to)

    return render_template("profile.html",
        user=user, stats=stats, expenses=expenses, categories=categories,
        presets=presets, active_from=date_from, active_to=date_to,
    )


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
