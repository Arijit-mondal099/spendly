import re
import secrets
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db.db import (
    close_db,
    create_user,
    get_db,
    get_user_by_email,
    init_db,
    seed_db,
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
        return redirect(url_for("landing"))

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
    return redirect(url_for("landing"))


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


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
