"""Pytest fixtures for Spendly: an isolated temp database and a Flask test
client.

The session-scoped ``app`` fixture repoints ``db.db._DATABASE_PATH`` at a temp
file BEFORE importing app, so the import-time ``init_db()`` + ``seed_db()`` in
app.py populate the throwaway database — never the real expense_tracker.db at
the repo root. Because of that, no test module may ``import app`` at module
level: collection imports run before fixtures and would touch the dev DB.
"""

import pytest


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Flask app backed by a throwaway seeded database (one per test run)."""
    import db.db as db_module

    db_module._DATABASE_PATH = (
        tmp_path_factory.mktemp("spendly-tests") / "expense_tracker.db"
    )
    import app as app_module

    return app_module.app


@pytest.fixture()
def client(app):
    """Fresh test client; sessions persist across requests within one client."""
    return app.test_client()


@pytest.fixture()
def app_ctx(app):
    """App context so DB helpers can run outside a request."""
    with app.app_context():
        yield


@pytest.fixture()
def demo_user_id(app_ctx):
    """Id of the seeded demo user — looked up by email, never assumed to be 1."""
    from db.db import get_user_by_email

    return get_user_by_email("demo@spendly.com")["id"]


@pytest.fixture(scope="session")
def empty_user_id(app):
    """Id of an extra user with no expenses, created once per run (additive
    to the shared seed DB, which is why tests must never assert global row
    counts)."""
    from werkzeug.security import generate_password_hash

    from db.db import create_user

    with app.app_context():
        return create_user(
            "Empty User", "empty@example.com", generate_password_hash("empty123")
        )
