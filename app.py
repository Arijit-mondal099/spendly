import math
import re
import secrets
import sqlite3
from datetime import date, datetime

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db.db import (
    close_db,
    create_user,
    get_db,
    get_user_by_email,
    init_db,
    insert_expense,
    seed_db,
)
from db.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

app = Flask(__name__)

# Random per-process key: sessions are properly signed, but every server
# restart signs everyone out. Fine for development at this stage.
app.secret_key = secrets.token_hex()

# ------------------------------------------------------------------ #
# Database setup                                                      #
# ------------------------------------------------------------------ #

app.teardown_appcontext(close_db)

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Constants                                                           #
# ------------------------------------------------------------------ #

MIN_PASSWORD_LENGTH = 8
# Pragmatic email check: something@something.tld, no whitespace, single '@'.
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
DUPLICATE_EMAIL_ERROR = "This email is already registered. Try signing in instead."
LOGIN_ERROR = "Invalid email or password."
VALID_CATEGORIES = (
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other",
)
MAX_DESCRIPTION_LENGTH = 200
# Upper bound to reject `inf` / `nan` and absurdly large values that would
# break aggregates (e.g. total_spent) and the formatted display.
MAX_AMOUNT = 1_000_000_000


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Bounce signed-in users; otherwise show the signup form or create an account."""
    if "user_id" in session:
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html", error=None, name="", email="")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = None
    if not name:
        error = "Please enter your full name."
    elif not EMAIL_PATTERN.fullmatch(email):
        error = "Please enter a valid email address."
    elif len(password) < MIN_PASSWORD_LENGTH:
        error = "Password must be at least 8 characters."
    elif get_user_by_email(email) is not None:
        error = DUPLICATE_EMAIL_ERROR

    if error is None:
        try:
            create_user(name, email, generate_password_hash(password))
        except sqlite3.IntegrityError:
            error = DUPLICATE_EMAIL_ERROR

    if error is not None:
        return render_template("register.html", error=error, name=name, email=email)

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Bounce signed-in users; otherwise show the sign-in form or authenticate."""
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html", error=None, email="")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    error = None
    if user is None or not check_password_hash(user["password_hash"], password):
        error = LOGIN_ERROR

    if error is not None:
        return render_template("login.html", error=error, email=email)

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    """Clear the session and return to the sign-in page."""
    session.clear()
    return redirect(url_for("login"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/profile")
def profile():
    """Show the signed-in user's profile with live data from the database."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user_info = get_user_by_id(user_id)
    if user_info is None:
        # Stale session pointing at a user row that no longer exists.
        session.clear()
        return redirect(url_for("login"))

    # ---- Parse the optional date-range filter from the query string ----
    def _parse_iso(raw):
        try:
            return date.fromisoformat(raw).isoformat() if raw else None
        except ValueError:
            return None

    start_iso = _parse_iso(request.args.get("start", "").strip())
    end_iso = _parse_iso(request.args.get("end", "").strip())
    filter_active = (start_iso is not None) or (end_iso is not None)

    # Unfiltered count is the "Y" in the "Showing X of Y" hint. Cheap aggregate.
    total_count_for_user = get_summary_stats(user_id)["transaction_count"]

    stats_raw = get_summary_stats(user_id, start=start_iso, end=end_iso)
    tx_rows = get_recent_transactions(user_id, start=start_iso, end=end_iso)
    cat_rows = get_category_breakdown(user_id)  # all-time, per spec

    parts = user_info["name"].split()
    initials = "".join(p[0] for p in parts[:2]).upper()

    has_filtered_data = stats_raw["transaction_count"] > 0

    if not filter_active:
        spent_note = (
            f"across {len(cat_rows)} categories" if cat_rows else "no expenses yet"
        )
        count_note = "all time"
        top_amount = cat_rows[0]["amount"] if cat_rows else 0
        top_note = (
            f"₹{top_amount:,.2f} spent" if cat_rows else "no expenses yet"
        )
    elif has_filtered_data:
        spent_note = "in this date range"
        count_note = "in this date range"
        top_note = "in this date range"
    else:
        spent_note = "no expenses in this date range"
        count_note = "no transactions in this date range"
        top_note = "no expenses in this date range"

    stats = [
        {
            "label": "Total spent",
            "value": f"₹{stats_raw['total_spent']:,.2f}",
            "note": spent_note,
        },
        {
            "label": "Transactions",
            "value": str(stats_raw["transaction_count"]),
            "note": count_note,
        },
        {
            "label": "Top category",
            "value": stats_raw["top_category"],
            "note": top_note,
        },
    ]

    transactions = [
        {
            "date": datetime.strptime(t["date"], "%Y-%m-%d").strftime("%b %d, %Y"),
            "description": t["description"] if t["description"] is not None else "—",
            "category": t["category"],
            "amount": f"₹{t['amount']:,.2f}",
        }
        for t in tx_rows
    ]

    categories = [
        {"name": c["name"], "total": f"₹{c['amount']:,.2f}", "percent": c["pct"]}
        for c in cat_rows
    ]

    return render_template(
        "profile.html",
        user={**user_info, "initials": initials},
        stats=stats,
        transactions=transactions,
        categories=categories,
        filter_start=start_iso or "",
        filter_end=end_iso or "",
        filter_active=filter_active,
        filtered_count=stats_raw["transaction_count"],
        total_count=total_count_for_user,
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            today=date.today().isoformat(),
            error=None,
            amount="", category="", date="", description="",
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description_raw = request.form.get("description", "")

    error = None
    amount = None
    if not amount_raw:
        error = "Amount is required."
    else:
        try:
            amount = float(amount_raw)
        except ValueError:
            error = "Amount must be a number."
        else:
            if not math.isfinite(amount) or amount <= 0 or amount > MAX_AMOUNT:
                error = "Amount must be a positive number."
                amount = None

    if error is None and category not in VALID_CATEGORIES:
        error = "Please choose a valid category."

    parsed_date = None
    if error is None:
        if not date_raw:
            error = "Date is required."
        else:
            try:
                parsed_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
            except ValueError:
                error = "Please enter a valid date."

    description = description_raw.strip() if description_raw else ""
    if error is None and len(description) > MAX_DESCRIPTION_LENGTH:
        error = f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer."
    if error is None and not description:
        description = None

    if error is not None:
        return render_template(
            "add_expense.html",
            today=date.today().isoformat(),
            error=error,
            amount=amount_raw, category=category, date=date_raw,
            description=description_raw,
        )

    insert_expense(
        user_id=user_id,
        amount=amount,
        category=category,
        date=parsed_date.isoformat(),
        description=description,
    )
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
