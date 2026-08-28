"""Tests for Step 6: date-range filter for the Recent transactions card.

Order/count assertions are relational / DB-derived on purpose: seed_db()
clamps expense dates to today early in the month, so absolute row counts in
a given window would flake depending on the run date.
"""

import re
from datetime import date

from db.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)


def _login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


# ------------------------------------------------------------------ #
# Unit tests: filtered query helpers                                  #
# ------------------------------------------------------------------ #

def test_recent_transactions_no_filter_returns_all(app_ctx, demo_user_id):
    """Regression: kwargs default to None, query is identical to Step 5."""
    assert len(get_recent_transactions(demo_user_id)) == 8


def test_recent_transactions_start_only(app_ctx, demo_user_id):
    # Pick a start date that is mid-month so at least some seed rows fall
    # after it (the seed data sits on days 1, 3, 5, 7, 10, 13, 16, 19).
    start = date.today().replace(day=10)
    rows = get_recent_transactions(demo_user_id, start=start.isoformat())

    assert len(rows) > 0
    assert all(date.fromisoformat(r["date"]) >= start for r in rows)


def test_recent_transactions_end_only(app_ctx, demo_user_id):
    today = date.today()
    rows = get_recent_transactions(demo_user_id, end=today.isoformat())

    assert all(date.fromisoformat(r["date"]) <= today for r in rows)
    # The first-of-month expense must be included (offset 0).
    first = today.replace(day=1).isoformat()
    assert any(r["date"] == first for r in rows)


def test_recent_transactions_inclusive_both_ends(app_ctx, demo_user_id):
    first = date.today().replace(day=1)
    today = date.today()
    rows = get_recent_transactions(
        demo_user_id,
        start=first.isoformat(),
        end=today.isoformat(),
    )

    # Inclusive on both ends: every returned row sits in [first, today],
    # and the first-of-month row is present (the offset-0 expense).
    dates = {r["date"] for r in rows}
    assert first.isoformat() in dates
    assert all(first <= date.fromisoformat(r["date"]) <= today for r in rows)


def test_recent_transactions_inverted_range_returns_empty(app_ctx, demo_user_id):
    rows = get_recent_transactions(
        demo_user_id, start="2999-01-01", end="1999-12-31"
    )
    assert rows == []


def test_summary_stats_filtered_within_unfiltered(app_ctx, demo_user_id):
    """Filtered totals are always <= unfiltered totals."""
    unfiltered = get_summary_stats(demo_user_id)
    filtered = get_summary_stats(
        demo_user_id,
        start=date.today().replace(day=1).isoformat(),
        end=date.today().isoformat(),
    )

    assert filtered["total_spent"] <= unfiltered["total_spent"]
    assert filtered["transaction_count"] <= unfiltered["transaction_count"]


def test_summary_stats_empty_range_is_zeros(app_ctx, demo_user_id):
    out = get_summary_stats(
        demo_user_id, start="1999-01-01", end="1999-12-31"
    )
    assert out == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


def test_summary_stats_empty_user_with_range(app_ctx, empty_user_id):
    out = get_summary_stats(
        empty_user_id,
        start="2000-01-01",
        end=date.today().isoformat(),
    )
    assert out == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


def test_category_breakdown_unaffected_by_filter(app_ctx, demo_user_id):
    """The breakdown is all-time, never scoped by the date filter.

    Guard against a future regression where start/end kwargs are silently
    threaded in by asserting the function's signature carries no date
    parameters — the caller (the /profile route) only ever passes user_id.
    """
    import inspect
    params = inspect.signature(get_category_breakdown).parameters
    assert "start" not in params
    assert "end" not in params

    # And sanity-check the data shape so this test would notice a broken
    # breakdown (not just a smuggled-in filter).
    breakdown = get_category_breakdown(demo_user_id)
    assert len(breakdown) == 7  # 7 distinct seed categories


# ------------------------------------------------------------------ #
# Route tests: GET /profile with date range                           #
# ------------------------------------------------------------------ #

def test_profile_no_query_unchanged_from_step5(client, demo_user_id):
    """Regression: no-filter behaviour must match Step 5 exactly."""
    assert _login(client).status_code == 302
    body = client.get("/profile").get_data(as_text=True)

    assert "₹314.44" in body
    assert body.count('class="profile-amount"') == 8
    # No "Showing" hint and no empty-state message when no filter is active.
    assert "Showing" not in body
    assert "No transactions in this date range" not in body


def test_profile_start_only_filters_table(client, demo_user_id):
    assert _login(client).status_code == 302
    # Use a mid-month start so the filtered set is non-empty (the seed data
    # lives on days 1, 3, 5, 7, 10, 13, 16, 19; day 10 keeps four of them).
    start = date.today().replace(day=10).isoformat()
    body = client.get(f"/profile?start={start}").get_data(as_text=True)

    # Derive both halves from the response so the test is robust to any
    # future change in seed data.
    match = re.search(r"Showing (\d+) of (\d+) transactions", body)
    assert match is not None
    shown, total = int(match.group(1)), int(match.group(2))
    assert total == get_summary_stats(demo_user_id)["transaction_count"]
    # The filtered row count must be strictly less than the unfiltered total.
    assert shown < total


def test_profile_both_ends_inclusive(client, demo_user_id):
    assert _login(client).status_code == 302
    first = date.today().replace(day=1).isoformat()
    today = date.today().isoformat()
    body = client.get(f"/profile?start={first}&end={today}").get_data(as_text=True)

    # Derive the expected filtered count from the helper so this is robust
    # to the seed function's month-clamping behaviour.
    expected_rows = get_recent_transactions(
        demo_user_id, start=first, end=today
    )
    match = re.search(r"Showing (\d+) of \d+ transactions", body)
    assert match is not None
    assert int(match.group(1)) == len(expected_rows)


def test_profile_inverted_range_renders_empty_state(client, demo_user_id):
    assert _login(client).status_code == 302
    body = client.get(
        "/profile?start=2999-01-01&end=1999-12-31"
    ).get_data(as_text=True)

    assert "No transactions in this date range" in body
    # Empty-state branch is exclusive: the "Showing" hint must not appear.
    assert "Showing" not in body


def test_profile_invalid_date_is_silently_ignored(client, demo_user_id):
    assert _login(client).status_code == 302
    page = client.get("/profile?start=not-a-date&end=2024-13-40")
    assert page.status_code == 200
    body = page.get_data(as_text=True)

    # No filter applied → full unfiltered list, no "Showing" hint.
    assert "Showing" not in body
    assert body.count('class="profile-amount"') == 8


def test_profile_filter_echoes_submitted_values(client, demo_user_id):
    assert _login(client).status_code == 302
    first = date.today().replace(day=1).isoformat()
    today = date.today().isoformat()
    body = client.get(f"/profile?start={first}&end={today}").get_data(as_text=True)

    assert f'value="{first}"' in body
    assert f'value="{today}"' in body


def test_profile_clear_link_is_unfiltered_url(client, demo_user_id):
    assert _login(client).status_code == 302
    body = client.get(
        "/profile?start=2024-01-01&end=2024-12-31"
    ).get_data(as_text=True)

    # The Clear link must be a plain url_for('profile') with no query string.
    # Match the entire anchor tag with both href and class regardless of
    # attribute order.
    assert re.search(
        r'<a\s+href="/profile"\s+class="[^"]*profile-filter-clear"[^>]*>',
        body,
    ) is not None
    # And it must not carry the filter query string.
    assert 'href="/profile?start=' not in body


def test_profile_anonymous_with_filter_still_redirects(client):
    """Filter in the query string does not bypass the login guard."""
    resp = client.get("/profile?start=2024-01-01&end=2024-12-31")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_profile_empty_user_with_filter(client):
    """A user with no expenses + an active filter sees the empty-state."""
    resp = client.post(
        "/register",
        data={
            "name": "Filtered User",
            "email": "filtered@example.com",
            "password": "filterpw1",
        },
    )
    assert resp.status_code == 302

    resp = client.post(
        "/login",
        data={"email": "filtered@example.com", "password": "filterpw1"},
    )
    assert resp.status_code == 302

    page = client.get(
        f"/profile?start=2000-01-01&end={date.today().isoformat()}"
    )
    assert page.status_code == 200
    body = page.get_data(as_text=True)

    assert "No transactions in this date range" in body
    assert "Filtered User" in body
    # No filter table is rendered for an empty result.
    assert body.count('class="profile-amount"') == 0
