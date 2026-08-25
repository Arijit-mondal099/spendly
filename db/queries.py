"""Read-only query helpers for Spendly: get_user_by_id(), get_summary_stats(),
get_recent_transactions(), get_category_breakdown()."""

from datetime import datetime

from db.db import get_db


def get_user_by_id(user_id):
    """Return {'name', 'email', 'member_since'} for this user id, or None."""
    row = get_db().execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None

    member_since = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": member_since.strftime("%B %Y"),
    }


def get_summary_stats(user_id):
    """Return {'total_spent', 'transaction_count', 'top_category'} for this
    user. Zeros and an em-dash when the user has no expenses."""
    db = get_db()
    totals = db.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total_spent,
               COUNT(*)                 AS transaction_count
        FROM expenses WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    top = db.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM expenses WHERE user_id = ?
        GROUP BY category
        ORDER BY total DESC, category ASC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    return {
        "total_spent": round(totals["total_spent"], 2),
        "transaction_count": totals["transaction_count"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10):
    """Return up to `limit` expenses for this user, newest first, as plain
    dicts with raw values (ISO date string, float amount)."""
    rows = get_db().execute(
        """
        SELECT date, description, category, amount
        FROM expenses WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [
        {
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        }
        for row in rows
    ]


def get_category_breakdown(user_id):
    """Return [{'name', 'amount', 'pct'}] ordered by amount desc; pct values
    are integers summing to exactly 100 (largest category absorbs rounding)."""
    rows = get_db().execute(
        """
        SELECT category AS name, SUM(amount) AS amount
        FROM expenses WHERE user_id = ?
        GROUP BY category
        ORDER BY amount DESC, name ASC
        """,
        (user_id,),
    ).fetchall()
    if not rows:
        return []

    grand_total = sum(row["amount"] for row in rows)
    pcts = [round(row["amount"] * 100 / grand_total) for row in rows]
    remainder = 100 - sum(pcts)
    # Rows are amount-desc, so index 0 is the largest category: its share is
    # always large enough to absorb the small rounding remainder.
    pcts[0] += remainder

    return [
        {"name": row["name"], "amount": round(row["amount"], 2), "pct": pct}
        for row, pct in zip(rows, pcts)
    ]
