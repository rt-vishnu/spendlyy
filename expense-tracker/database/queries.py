from database.db import get_db

def get_user_by_id(user_id):
    db = get_db()
    row = db.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    from datetime import datetime
    dt = datetime.fromisoformat(row["created_at"])
    return {
        "name": row["name"],
        "email": row["email"],
        "initials": "".join(p[0].upper() for p in row["name"].split()[:2]),
        "member_since": dt.strftime("%B %Y"),
    }
def get_summary_stats(user_id):
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    top = db.execute(
        "SELECT category, SUM(amount) AS cat_total FROM expenses "
        "WHERE user_id = ? GROUP BY category ORDER BY cat_total DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    return {
        "total_spent": f"₹{row['total']:.2f}",
        "transactions": row["cnt"],
        "top_category": top["category"] if top else "—",
    }
def get_recent_transactions(user_id, limit=10):
    db = get_db()
    rows = db.execute(
        "SELECT date, description, category, amount FROM expenses "
        "WHERE user_id = ? ORDER BY date DESC LIMIT ?",
        (user_id, limit),
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

def get_category_breakdown(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE user_id = ? GROUP BY category ORDER BY total DESC",
        (user_id,),
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
