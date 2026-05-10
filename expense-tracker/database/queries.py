from datetime import datetime
from database.db import get_db


def _date_clause(date_from, date_to):
    if date_from and date_to:
        return " AND date BETWEEN ? AND ?", (date_from, date_to)
    return "", ()


def get_user_by_id(user_id):
    db = get_db()
    row = db.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    dt = datetime.fromisoformat(row["created_at"])
    return {
        "name": row["name"],
        "email": row["email"],
        "initials": "".join(p[0].upper() for p in row["name"].split()[:2]),
        "member_since": dt.strftime("%B %Y"),
    }


def get_summary_stats(user_id, date_from=None, date_to=None):
    db = get_db()
    date_filter, date_params = _date_clause(date_from, date_to)
    params = (user_id,) + date_params
    row = db.execute(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS total "
        "FROM expenses WHERE user_id = ?" + date_filter,
        params,
    ).fetchone()
    top = db.execute(
        "SELECT category, SUM(amount) AS cat_total FROM expenses "
        "WHERE user_id = ?" + date_filter + " GROUP BY category ORDER BY cat_total DESC LIMIT 1",
        params,
    ).fetchone()
    return {
        "total_spent": f"₹{row['total']:.2f}",
        "transactions": row["cnt"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    db = get_db()
    date_filter, date_params = _date_clause(date_from, date_to)
    params = (user_id,) + date_params + (limit,)
    rows = db.execute(
        "SELECT date, description, category, amount FROM expenses "
        "WHERE user_id = ?" + date_filter + " ORDER BY date DESC LIMIT ?",
        params,
    ).fetchall()
    return [
        {
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": f"₹{row['amount']:.2f}",
        }
        for row in rows
    ]


_BAR_CLASS = {
    "food": "bar-food",
    "transport": "bar-travel",
    "bills": "bar-bills",
    "health": "bar-health",
    "entertainment": "bar-entertainment",
    "shopping": "bar-shopping",
    "other": "bar-other",
}


def get_category_breakdown(user_id, date_from=None, date_to=None):
    db = get_db()
    date_filter, date_params = _date_clause(date_from, date_to)
    params = (user_id,) + date_params
    rows = db.execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE user_id = ?" + date_filter + " GROUP BY category ORDER BY total DESC",
        params,
    ).fetchall()
    if not rows:
        return []
    grand_total = sum(r["total"] for r in rows)
    result = []
    pct_sum = 0
    for i, row in enumerate(rows):
        if i < len(rows) - 1:
            pct = round(row["total"] / grand_total * 100)
        else:
            pct = 100 - pct_sum
        pct_sum += pct
        result.append({
            "name": row["category"],
            "amount": f"₹{row['total']:.2f}",
            "pct": pct,
            "bar_class": _BAR_CLASS.get(row["category"].lower(), "bar-other"),
        })
    return result
