import sqlite3
from functools import wraps

from flask import current_app, g, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash


STATUSES = ["Pending", "Under Review", "In Progress", "Resolved", "Rejected"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
CATEGORIES = [
    "Potholes",
    "Garbage accumulation",
    "Water leakage",
    "Broken streetlights",
    "Drainage problems",
    "Other civic complaints",
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        db = get_db()
        schema_path = app.root_path + "/database/schema.sql"
        existing = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        if existing:
            return
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            db.executescript(schema_file.read())
        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (
                "System Administrator",
                "admin@fixmyarea.local",
                generate_password_hash("Admin@123"),
                "admin",
            ),
        )
        db.commit()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            flash("Admin access is required.", "danger")
            return redirect(url_for("main.dashboard"))
        return view(**kwargs)

    return wrapped_view


def current_user():
    if "user_id" not in session:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()


def unread_notification_count(user_id):
    return get_db().execute(
        "SELECT COUNT(*) AS total FROM notifications WHERE user_id = ? AND is_read = 0",
        (user_id,),
    ).fetchone()["total"]
