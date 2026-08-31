"""Tests for Step 8: Edit Expense route and ``update_expense`` DB helper.

These tests are derived from ``.claude/specs/08-edit-expense.md`` — they define
the behavior contract for the feature, not the implementation. All assertions
scope DB lookups to a specific ``user_id`` (never a global row count) per
``testing.md``.
"""

from db.db import get_db, insert_expense, update_expense


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _login(client, email="demo@spendly.com", password="demo123"):
    """Log the test client in as the given user."""
    return client.post("/login", data={"email": email, "password": password})


def _create_expense(
    user_id, *, amount=10.0, category="Food",
    date="2026-01-15", description="seed",
):
    """Insert a row owned by ``user_id`` and return its id."""
    return insert_expense(
        user_id=user_id,
        amount=amount,
        category=category,
        date=date,
        description=description,
    )


def _fetch_expense(expense_id):
    """Return the full row for ``expense_id`` or ``None``."""
    return get_db().execute(
        "SELECT user_id, amount, category, date, description "
        "FROM expenses WHERE id = ?",
        (expense_id,),
    ).fetchone()


# ------------------------------------------------------------------ #
# Unit tests: update_expense                                          #
# ------------------------------------------------------------------ #

def test_update_expense_updates_row_and_returns_rowcount_one(
    app_ctx, demo_user_id
):
    """A valid update changes the row in place and reports rowcount=1."""
    expense_id = _create_expense(
        demo_user_id, amount=10.0, category="Food",
        date="2026-01-15", description="before",
    )

    updated = update_expense(
        expense_id=expense_id,
        user_id=demo_user_id,
        amount=99.0,
        category="Bills",
        date="2026-02-20",
        description="after",
    )

    assert updated == 1

    row = _fetch_expense(expense_id)
    assert row is not None
    assert row["user_id"] == demo_user_id
    assert row["amount"] == 99.0
    assert row["category"] == "Bills"
    assert row["date"] == "2026-02-20"
    assert row["description"] == "after"


def test_update_expense_with_none_description_stores_null(
    app_ctx, demo_user_id
):
    """``description=None`` is stored as SQL NULL, not the empty string."""
    expense_id = _create_expense(
        demo_user_id, amount=10.0, description="old",
    )

    update_expense(
        expense_id=expense_id,
        user_id=demo_user_id,
        amount=10.0,
        category="Food",
        date="2026-01-15",
        description=None,
    )

    row = _fetch_expense(expense_id)
    assert row is not None
    assert row["description"] is None


def test_update_expense_for_other_users_row_returns_zero_and_leaves_row_unchanged(
    app_ctx, demo_user_id, empty_user_id
):
    """Updating with a wrong ``user_id`` is a no-op: rowcount=0 and the
    original row is untouched."""
    expense_id = _create_expense(
        demo_user_id, amount=10.0, category="Food",
        date="2026-01-15", description="untouched",
    )

    updated = update_expense(
        expense_id=expense_id,
        user_id=empty_user_id,  # wrong owner
        amount=999.0,
        category="Bills",
        date="2099-12-31",
        description="hijack",
    )

    assert updated == 0

    row = _fetch_expense(expense_id)
    assert row is not None
    assert row["user_id"] == demo_user_id
    assert row["amount"] == 10.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-01-15"
    assert row["description"] == "untouched"


# ------------------------------------------------------------------ #
# Route tests: GET /expenses/<id>/edit                                #
# ------------------------------------------------------------------ #

def test_get_edit_expense_redirects_when_anonymous(client, demo_user_id):
    """An anonymous visitor is bounced to the login page (302)."""
    expense_id = _create_expense(demo_user_id)

    resp = client.get(f"/expenses/{expense_id}/edit")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_get_edit_expense_404_for_other_user(
    client, demo_user_id, empty_user_id
):
    """A logged-in user asking for another user's expense gets 404, not 403."""
    expense_id = _create_expense(demo_user_id)
    assert _login(client, email="empty@example.com", password="empty123").status_code == 302

    resp = client.get(f"/expenses/{expense_id}/edit")
    assert resp.status_code == 404


def test_get_edit_expense_404_for_missing_id(client, demo_user_id):
    """A non-existent expense id returns 404."""
    assert _login(client).status_code == 302

    resp = client.get("/expenses/999999/edit")
    assert resp.status_code == 404


def test_get_edit_expense_renders_form_prefilled(
    client, demo_user_id
):
    """The form is pre-filled with the current row's values and posts back
    to ``/expenses/<id>/edit``."""
    expense_id = _create_expense(
        demo_user_id, amount=42.5, category="Bills",
        date="2026-04-10", description="rent share",
    )
    assert _login(client).status_code == 302

    page = client.get(f"/expenses/{expense_id}/edit")
    assert page.status_code == 200
    body = page.get_data(as_text=True)

    # Form posts back to the edit URL via url_for.
    assert "<form" in body
    assert 'method="POST"' in body
    assert f'action="/expenses/{expense_id}/edit"' in body

    # Pre-filled values match the row.
    assert 'value="42.5"' in body
    assert 'value="2026-04-10"' in body
    assert 'value="rent share"' in body

    # Category <option> for "Bills" is marked selected.
    assert '<option value="Bills" selected' in body


# ------------------------------------------------------------------ #
# Route tests: POST /expenses/<id>/edit                               #
# ------------------------------------------------------------------ #

def test_post_edit_expense_redirects_when_anonymous(client, demo_user_id):
    """An anonymous POST is bounced to the login page (302)."""
    expense_id = _create_expense(demo_user_id)

    resp = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "10", "category": "Food",
            "date": "2026-01-15", "description": "",
        },
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_post_edit_expense_valid_updates_row_and_redirects_to_profile(
    client, demo_user_id
):
    """Valid input updates the row and 302s to /profile."""
    expense_id = _create_expense(
        demo_user_id, amount=10.0, category="Food",
        date="2026-01-15", description="before",
    )
    assert _login(client).status_code == 302

    resp = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "75.25", "category": "Transport",
            "date": "2026-05-20", "description": "after",
        },
    )

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")

    row = _fetch_expense(expense_id)
    assert row is not None
    assert row["amount"] == 75.25
    assert row["category"] == "Transport"
    assert row["date"] == "2026-05-20"
    assert row["description"] == "after"


def test_post_edit_expense_404_for_other_user(
    client, demo_user_id, empty_user_id
):
    """A user editing another user's expense gets 404 and the row is
    unchanged."""
    expense_id = _create_expense(
        demo_user_id, amount=10.0, category="Food",
        date="2026-01-15", description="untouched",
    )
    assert _login(client, email="empty@example.com", password="empty123").status_code == 302

    resp = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "999", "category": "Bills",
            "date": "2099-12-31", "description": "hijack",
        },
    )
    assert resp.status_code == 404

    row = _fetch_expense(expense_id)
    assert row is not None
    assert row["amount"] == 10.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-01-15"
    assert row["description"] == "untouched"


def test_post_edit_expense_missing_amount_rerenders(
    client, demo_user_id
):
    """A blank amount re-renders the form with a 200 status and an error,
    and the row is unchanged."""
    expense_id = _create_expense(
        demo_user_id, amount=10.0, description="unchanged",
    )
    assert _login(client).status_code == 302

    page = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "", "category": "Food",
            "date": "2026-01-15", "description": "x",
        },
    )
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert 'class="auth-error"' in body
    assert "Amount" in body

    row = _fetch_expense(expense_id)
    assert row is not None
    assert row["amount"] == 10.0
    assert row["description"] == "unchanged"


def test_post_edit_expense_invalid_category_rerenders(
    client, demo_user_id
):
    """A category not in the 7-item fixed list re-renders with an error and
    the row is unchanged."""
    expense_id = _create_expense(
        demo_user_id, amount=10.0, category="Food", description="unchanged",
    )
    assert _login(client).status_code == 302

    page = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "10", "category": "BogusCategory",
            "date": "2026-01-15", "description": "",
        },
    )
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert 'class="auth-error"' in body
    assert "category" in body.lower()

    row = _fetch_expense(expense_id)
    assert row is not None
    assert row["category"] == "Food"
    assert row["description"] == "unchanged"


def test_post_edit_expense_invalid_date_rerenders(
    client, demo_user_id
):
    """A non-parseable date re-renders with an error and the row is
    unchanged."""
    expense_id = _create_expense(
        demo_user_id, amount=10.0, date="2026-01-15", description="unchanged",
    )
    assert _login(client).status_code == 302

    page = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "10", "category": "Food",
            "date": "not-a-date", "description": "",
        },
    )
    assert page.status_code == 200
    assert 'class="auth-error"' in page.get_data(as_text=True)

    row = _fetch_expense(expense_id)
    assert row is not None
    assert row["date"] == "2026-01-15"
    assert row["description"] == "unchanged"


def test_post_edit_expense_blank_description_clears_to_null(
    client, demo_user_id
):
    """Submitting an empty description stores NULL in the DB."""
    expense_id = _create_expense(
        demo_user_id, amount=10.0, description="to be cleared",
    )
    assert _login(client).status_code == 302

    resp = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "10", "category": "Food",
            "date": "2026-01-15", "description": "",
        },
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")

    row = _fetch_expense(expense_id)
    assert row is not None
    assert row["description"] is None


# ------------------------------------------------------------------ #
# Route tests: /profile surfaces an Edit link per transaction         #
# ------------------------------------------------------------------ #

def test_profile_renders_edit_link_for_each_transaction(
    client, demo_user_id
):
    """The recent-transactions table contains an Edit link for each row,
    built via ``url_for('edit_expense', id=...)``."""
    # Use today's date so the row sorts into the top 10 (the profile
    # shows the 10 most recent transactions).
    from datetime import date
    today = date.today().isoformat()
    expense_id = _create_expense(
        demo_user_id, amount=12.0, category="Transport",
        date=today, description="link test",
    )
    assert _login(client).status_code == 302

    body = client.get("/profile").get_data(as_text=True)
    assert f'href="/expenses/{expense_id}/edit"' in body
