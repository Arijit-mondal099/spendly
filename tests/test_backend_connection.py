"""Tests for Step 5: wiring the /profile route to live database queries.

Covers the four db.queries helpers against a seeded temp database and the
/profile route through the real login flow. Order assertions are relational /
DB-derived on purpose: seed_db() clamps expense dates to today early in the
month, so absolute orderings would flake depending on the run date.
"""

import re
from datetime import date, datetime

import pytest

from db.db import get_db
from db.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

# Seed data inserted by seed_db(): 8 expenses across 7 categories.
SEED_AMOUNTS = {54.20, 32.00, 96.40, 18.75, 23.10, 15.00, 49.99, 25.00}
SEED_TOTAL = 314.44
SEED_CATEGORIES = {
    "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other",
}


# ------------------------------------------------------------------ #
# Unit tests: db.queries helpers                                      #
# ------------------------------------------------------------------ #

def test_get_user_by_id_returns_seed_user(app_ctx, demo_user_id):
    user = get_user_by_id(demo_user_id)

    assert set(user.keys()) == {"name", "email", "member_since"}
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    # Derive the expectation from the stored timestamp, never from today's
    # date: the DB may have been seeded just before a month boundary.
    row = get_db().execute(
        "SELECT created_at FROM users WHERE id = ?", (demo_user_id,)
    ).fetchone()
    expected = datetime.strptime(
        row["created_at"], "%Y-%m-%d %H:%M:%S"
    ).strftime("%B %Y")
    assert user["member_since"] == expected


def test_get_user_by_id_missing_returns_none(app_ctx):
    assert get_user_by_id(999999) is None


def test_summary_stats_with_expenses(app_ctx, demo_user_id):
    stats = get_summary_stats(demo_user_id)

    assert stats["total_spent"] == pytest.approx(SEED_TOTAL)
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_summary_stats_no_expenses(app_ctx, empty_user_id):
    assert get_summary_stats(empty_user_id) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


def test_recent_transactions_newest_first(app_ctx, demo_user_id):
    transactions = get_recent_transactions(demo_user_id)

    assert len(transactions) == 8  # within the default limit of 10
    for tx in transactions:
        assert set(tx.keys()) == {"id", "date", "description", "category", "amount"}

    dates = [date.fromisoformat(t["date"]) for t in transactions]
    assert all(a >= b for a, b in zip(dates, dates[1:]))

    assert sorted(t["amount"] for t in transactions) == pytest.approx(
        sorted(SEED_AMOUNTS)
    )
    missing_description = [t for t in transactions if t["description"] is None]
    assert len(missing_description) == 1
    assert missing_description[0]["amount"] == pytest.approx(49.99)
    assert {t["category"] for t in transactions} == SEED_CATEGORIES


def test_recent_transactions_respects_limit(app_ctx, demo_user_id):
    full = get_recent_transactions(demo_user_id)
    limited = get_recent_transactions(demo_user_id, limit=3)

    assert len(limited) == 3
    assert limited == full[:3]


def test_recent_transactions_empty(app_ctx, empty_user_id):
    assert get_recent_transactions(empty_user_id) == []


def test_category_breakdown_order_and_pct_sum(app_ctx, demo_user_id):
    breakdown = get_category_breakdown(demo_user_id)

    rows = get_db().execute(
        "SELECT category, SUM(amount) FROM expenses WHERE user_id = ? "
        "GROUP BY category",
        (demo_user_id,),
    ).fetchall()
    totals = {category: total for category, total in rows}
    expected_order = [
        category
        for category, _ in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    ]

    assert [row["name"] for row in breakdown] == expected_order
    assert len(breakdown) == 7

    pcts = [row["pct"] for row in breakdown]
    assert all(isinstance(pct, int) for pct in pcts)
    assert sum(pcts) == 100
    assert max(breakdown, key=lambda row: row["pct"])["name"] == "Bills"

    for row in breakdown:
        assert row["amount"] == pytest.approx(totals[row["name"]])


def test_category_breakdown_empty(app_ctx, empty_user_id):
    assert get_category_breakdown(empty_user_id) == []


# ------------------------------------------------------------------ #
# Route tests: GET /profile                                           #
# ------------------------------------------------------------------ #

def _login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


def test_profile_redirects_anonymous_to_login(client):
    resp = client.get("/profile")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_profile_authenticated_renders_seed_data(client, demo_user_id):
    assert _login(client).status_code == 302

    page = client.get("/profile")
    assert page.status_code == 200
    body = page.get_data(as_text=True)

    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body
    assert re.search(r"Member since [A-Z][a-z]+ \d{4}", body)
    assert f"{SEED_TOTAL:.2f}" in body
    assert "Bills" in body
    assert body.count('class="profile-amount"') == 8


def test_profile_transactions_newest_first_in_html(client, demo_user_id):
    assert _login(client).status_code == 302
    body = client.get("/profile").get_data(as_text=True)

    # Expected presentation order straight from the DB; skip the NULL
    # description (it renders as the ambiguous "—" fallback).
    rows = get_db().execute(
        "SELECT description FROM expenses WHERE user_id = ? "
        "ORDER BY date DESC, id DESC",
        (demo_user_id,),
    ).fetchall()
    descriptions = [r["description"] for r in rows if r["description"] is not None]

    positions = [body.find(description) for description in descriptions]
    assert all(position != -1 for position in positions)
    assert all(a < b for a, b in zip(positions, positions[1:]))


def test_profile_shows_all_seven_categories(client, demo_user_id):
    assert _login(client).status_code == 302
    body = client.get("/profile").get_data(as_text=True)

    assert body.count("<progress") == 7
    for name in SEED_CATEGORIES:
        assert name in body


def test_profile_zero_expense_user_end_to_end(client):
    resp = client.post(
        "/register",
        data={
            "name": "New User",
            "email": "new@example.com",
            "password": "newuser123",
        },
    )
    assert resp.status_code == 302

    resp = client.post(
        "/login",
        data={"email": "new@example.com", "password": "newuser123"},
    )
    assert resp.status_code == 302

    page = client.get("/profile")
    assert page.status_code == 200
    body = page.get_data(as_text=True)

    assert "New User" in body
    assert "₹0.00" in body
    assert body.count('class="profile-amount"') == 0
    assert body.count("<progress") == 0
    assert "Traceback" not in body
