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


def _date_clauses(user_id, start, end):
    """Return (where_sql, params) for an optional inclusive date range."""
    clauses, params = ["user_id = ?"], [user_id]
    if start is not None:
        clauses.append("date >= ?")
        params.append(start)
    if end is not None:
        clauses.append("date <= ?")
        params.append(end)
    return " AND ".join(clauses), params


def get_summary_stats(user_id, start=None, end=None):
    """Return {'total_spent', 'transaction_count', 'top_category'} for this
    user, optionally scoped to an inclusive date range. Zeros and an em-dash
    when the (filtered) window has no expenses."""
    db = get_db()
    where_sql, params = _date_clauses(user_id, start, end)

    totals = db.execute(
        f"""
        SELECT COALESCE(SUM(amount), 0) AS total_spent,
               COUNT(*)                 AS transaction_count
        FROM expenses WHERE {where_sql}
        """,
        params,
    ).fetchone()
    top = db.execute(
        f"""
        SELECT category, SUM(amount) AS total
        FROM expenses WHERE {where_sql}
        GROUP BY category
        ORDER BY total DESC, category ASC
        LIMIT 1
        """,
        params,
    ).fetchone()
    return {
        "total_spent": round(totals["total_spent"], 2),
        "transaction_count": totals["transaction_count"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, start=None, end=None):
    """Return up to `limit` expenses for this user, newest first, as plain
    dicts with raw values (ISO date string, float amount). Optionally scoped
    to an inclusive date range via `start` / `end` (ISO YYYY-MM-DD)."""
    where_sql, params = _date_clauses(user_id, start, end)
    rows = get_db().execute(
        f"""
        SELECT id, date, description, category, amount
        FROM expenses WHERE {where_sql}
        ORDER BY date DESC, id DESC
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()
    return [
        {
            "id": row["id"],
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
