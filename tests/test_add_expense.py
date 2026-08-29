"""Tests for Step 7: Add Expense route and ``insert_expense`` DB helper.

These tests are derived from ``.claude/specs/07-add-expense.md`` — they define
the behavior contract for the feature, not the implementation. All assertions
scope DB lookups to a specific ``user_id`` (never a global row count) per
``testing.md``.
"""

from db.db import get_db, insert_expense


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _login(client, email="demo@spendly.com", password="demo123"):
    """Log the test client in as the seeded demo user."""
    return client.post("/login", data={"email": email, "password": password})


def _row_for_demo_user(demo_user_id, *, date_str, category, description):
    """Return the expense row inserted by the demo user for the given date
    and category. Scoped to ``demo_user_id`` so it is stable regardless of
    other users' expenses in the shared seed DB."""
    return get_db().execute(
        "SELECT amount, category, date, description FROM expenses "
        "WHERE user_id = ? AND date = ? AND category = ? "
        "ORDER BY id DESC LIMIT 1",
        (demo_user_id, date_str, category),
    ).fetchone()


# ------------------------------------------------------------------ #
# Unit tests: insert_expense                                           #
# ------------------------------------------------------------------ #

def test_insert_expense_with_description_persists_row_and_returns_id(
    app_ctx, demo_user_id
):
    """A valid insert lands in the table with the right values, and the
    function returns the new row's id."""
    new_id = insert_expense(
        user_id=demo_user_id,
        amount=50.0,
        category="Food",
        date="2026-03-20",
        description="Lunch",
    )

    assert isinstance(new_id, int)
    assert new_id > 0

    row = get_db().execute(
        "SELECT user_id, amount, category, date, description "
        "FROM expenses WHERE id = ?",
        (new_id,),
    ).fetchone()

    assert row is not None
    assert row["user_id"] == demo_user_id
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_insert_expense_with_none_description_stores_null(
    app_ctx, demo_user_id
):
    """``description=None`` is stored as SQL NULL, not the empty string."""
    new_id = insert_expense(
        user_id=demo_user_id,
        amount=12.0,
        category="Transport",
        date="2026-03-20",
        description=None,
    )

    row = get_db().execute(
        "SELECT description FROM expenses WHERE id = ?",
        (new_id,),
    ).fetchone()

    assert row is not None
    assert row["description"] is None


# ------------------------------------------------------------------ #
# Route tests: GET /expenses/add                                       #
# ------------------------------------------------------------------ #

def test_get_add_expense_redirects_when_anonymous(client):
    """An anonymous visitor is bounced to the login page (302)."""
    resp = client.get("/expenses/add")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_get_add_expense_returns_200_when_authenticated(client):
    """An authenticated GET renders the form with status 200."""
    assert _login(client).status_code == 302

    page = client.get("/expenses/add")
    assert page.status_code == 200


def test_get_add_expense_renders_form_with_post_method(
    client, demo_user_id
):
    """The rendered form posts back to ``/expenses/add`` via ``method="POST"``."""
    assert _login(client).status_code == 302

    body = client.get("/expenses/add").get_data(as_text=True)

    assert "<form" in body
    assert 'method="POST"' in body
    assert 'action="/expenses/add"' in body


def test_get_add_expense_includes_all_seven_categories(
    client, demo_user_id
):
    """The category ``<select>`` exposes exactly the 7 fixed options."""
    assert _login(client).status_code == 302

    body = client.get("/expenses/add").get_data(as_text=True)
    for category in (
        "Food", "Transport", "Bills", "Health",
        "Entertainment", "Shopping", "Other",
    ):
        assert f'value="{category}"' in body, (
            f"Expected category option {category!r} in the dropdown"
        )


# ------------------------------------------------------------------ #
# Route tests: POST /expenses/add                                      #
# ------------------------------------------------------------------ #

def test_post_add_expense_redirects_when_anonymous(client):
    """An anonymous POST is also bounced to the login page (302)."""
    resp = client.post(
        "/expenses/add",
        data={
            "amount": "10",
            "category": "Food",
            "date": "2026-03-20",
            "description": "",
        },
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_post_add_expense_valid_data_redirects_to_profile(
    client, demo_user_id
):
    """Valid input inserts the row and 302s to /profile."""
    assert _login(client).status_code == 302

    resp = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")

    row = _row_for_demo_user(
        demo_user_id, date_str="2026-03-20", category="Food",
        description="Lunch",
    )
    assert row is not None
    assert row["amount"] == 50.0
    assert row["description"] == "Lunch"


def test_post_add_expense_missing_amount_rerenders_with_error(
    client, demo_user_id
):
    """A blank amount re-renders the form with a 200 status and an error."""
    assert _login(client).status_code == 302

    page = client.post(
        "/expenses/add",
        data={
            "amount": "",
            "category": "Food",
            "date": "2026-03-20",
            "description": "",
        },
    )
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert 'class="auth-error"' in body
    assert "Amount" in body


def test_post_add_expense_zero_amount_rerenders_with_error(
    client, demo_user_id
):
    """An amount of 0 re-renders the form with a 200 status and an error."""
    assert _login(client).status_code == 302

    page = client.post(
        "/expenses/add",
        data={
            "amount": "0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "",
        },
    )
    assert page.status_code == 200
    assert 'class="auth-error"' in page.get_data(as_text=True)


def test_post_add_expense_non_numeric_amount_rerenders_with_error(
    client, demo_user_id
):
    """A non-numeric amount re-renders the form with a 200 status and an error."""
    assert _login(client).status_code == 302

    page = client.post(
        "/expenses/add",
        data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-03-20",
            "description": "",
        },
    )
    assert page.status_code == 200
    assert 'class="auth-error"' in page.get_data(as_text=True)


def test_post_add_expense_invalid_category_rerenders_with_error(
    client, demo_user_id
):
    """A category not in the 7-item fixed list re-renders the form with an error."""
    assert _login(client).status_code == 302

    page = client.post(
        "/expenses/add",
        data={
            "amount": "10",
            "category": "BogusCategory",
            "date": "2026-03-20",
            "description": "",
        },
    )
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert 'class="auth-error"' in body
    assert "category" in body.lower()


def test_post_add_expense_lowercase_category_rerenders_with_error(
    client, demo_user_id
):
    """Category match is case-sensitive: ``food`` (lowercase) must fail."""
    assert _login(client).status_code == 302

    page = client.post(
        "/expenses/add",
        data={
            "amount": "10",
            "category": "food",
            "date": "2026-03-20",
            "description": "",
        },
    )
    assert page.status_code == 200
    assert 'class="auth-error"' in page.get_data(as_text=True)


def test_post_add_expense_invalid_date_rerenders_with_error(
    client, demo_user_id
):
    """A non-parseable date string re-renders the form with a 200 + error."""
    assert _login(client).status_code == 302

    page = client.post(
        "/expenses/add",
        data={
            "amount": "10",
            "category": "Food",
            "date": "not-a-date",
            "description": "",
        },
    )
    assert page.status_code == 200
    assert 'class="auth-error"' in page.get_data(as_text=True)


def test_post_add_expense_no_description_persists_with_null(
    client, demo_user_id
):
    """Omitting the description (blank) saves the row with description IS NULL
    and 302s to /profile."""
    assert _login(client).status_code == 302

    resp = client.post(
        "/expenses/add",
        data={
            "amount": "12.5",
            "category": "Transport",
            "date": "2026-03-20",
            "description": "",
        },
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")

    row = get_db().execute(
        "SELECT description FROM expenses "
        "WHERE user_id = ? AND date = ? AND category = ? "
        "ORDER BY id DESC LIMIT 1",
        (demo_user_id, "2026-03-20", "Transport"),
    ).fetchone()
    assert row is not None
    assert row["description"] is None


def test_post_add_expense_description_too_long_rerenders_with_error(
    client, demo_user_id
):
    """A 201-character description re-renders the form with a 200 + error and
    is NOT saved."""
    assert _login(client).status_code == 302

    long_desc = "x" * 201
    page = client.post(
        "/expenses/add",
        data={
            "amount": "10",
            "category": "Food",
            "date": "2026-03-20",
            "description": long_desc,
        },
    )
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert 'class="auth-error"' in body

    # The row must not have been inserted.
    row = get_db().execute(
        "SELECT id FROM expenses "
        "WHERE user_id = ? AND date = ? AND description = ?",
        (demo_user_id, "2026-03-20", long_desc),
    ).fetchone()
    assert row is None
