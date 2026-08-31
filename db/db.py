"""SQLite helpers for Spendly: get_db(), close_db(), init_db(), seed_db(),
get_user_by_email(), create_user(), insert_expense(), update_expense()."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

from flask import g
from werkzeug.security import generate_password_hash

DATABASE_NAME = "expense_tracker.db"
_DATABASE_PATH = Path(__file__).resolve().parent.parent / DATABASE_NAME

SCHEMA_SQL = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT NOT NULL,
        email         TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at    TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS expenses (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(id),
        amount      REAL NOT NULL,
        category    TEXT NOT NULL,
        date        TEXT NOT NULL,
        description TEXT,
        created_at  TEXT DEFAULT (datetime('now'))
    )
    """,
)


def get_db():
    """Return this context's SQLite connection, creating it on first use."""
    if "db" not in g:
        conn = sqlite3.connect(_DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(e=None):
    """Close this context's DB connection (registered via teardown_appcontext)."""
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    """Create both tables if they do not exist. Safe to call repeatedly."""
    db = get_db()
    for stmt in SCHEMA_SQL:
        db.execute(stmt)
    db.commit()


def seed_db():
    """Insert demo user + 8 sample expenses once. No-op if any user exists."""
    db = get_db()
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return

    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    today = date.today()
    first_of_month = today.replace(day=1)
    # (day offset from month start, category, amount, description)
    sample_expenses = (
        (0, "Food", 54.20, "Weekly groceries"),
        (2, "Transport", 32.00, "Bus pass top-up"),
        (4, "Bills", 96.40, "Electricity bill"),
        (6, "Food", 18.75, "Lunch with friends"),
        (9, "Health", 23.10, "Pharmacy - cold medicine"),
        (12, "Entertainment", 15.00, "Movie tickets"),
        (15, "Shopping", 49.99, None),
        (18, "Other", 25.00, "Birthday gift"),
    )
    rows = [
        (
            user_id,
            amount,
            category,
            min(first_of_month + timedelta(days=offset), today).isoformat(),
            description,
        )
        for offset, category, amount, description in sample_expenses
    ]
    db.executemany(
        "INSERT INTO expenses "
        "(user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    db.commit()


def get_user_by_email(email):
    """Return the user row with this email address, or None."""
    db = get_db()
    return db.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,),
    ).fetchone()


def create_user(name, email, password_hash):
    """Insert a new user and return the new row's id."""
    db = get_db()
    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    db.commit()
    return cursor.lastrowid


def insert_expense(user_id, amount, category, date, description):
    """Insert a new expense row and return the new row's id.

    ``amount`` is a float, ``category`` and ``date`` are strings, and
    ``description`` is either a string or None (which is stored as NULL).
    """
    db = get_db()
    cursor = db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    db.commit()
    return cursor.lastrowid


def update_expense(expense_id, user_id, amount, category, date, description):
    """Update an existing expense row scoped to ``user_id`` and return the
    number of rows affected (0 if the row does not exist for this user).

    ``amount`` is a float, ``category`` and ``date`` are strings, and
    ``description`` is either a string or None (which is stored as NULL).
    """
    db = get_db()
    cursor = db.execute(
        "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
        "WHERE id = ? AND user_id = ?",
        (amount, category, date, description, expense_id, user_id),
    )
    db.commit()
    return cursor.rowcount
