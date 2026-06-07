from flask import Blueprint, redirect, render_template, session, url_for

from models.database import get_db, login_required


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))
    db = get_db()
    user_id = session["user_id"]
    stats = {
        "total": db.execute("SELECT COUNT(*) total FROM complaints WHERE user_id = ?", (user_id,)).fetchone()["total"],
        "pending": db.execute(
            "SELECT COUNT(*) total FROM complaints WHERE user_id = ? AND status = 'Pending'", (user_id,)
        ).fetchone()["total"],
        "progress": db.execute(
            "SELECT COUNT(*) total FROM complaints WHERE user_id = ? AND status = 'In Progress'", (user_id,)
        ).fetchone()["total"],
        "resolved": db.execute(
            "SELECT COUNT(*) total FROM complaints WHERE user_id = ? AND status = 'Resolved'", (user_id,)
        ).fetchone()["total"],
    }
    recent = db.execute(
        "SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (user_id,),
    ).fetchall()
    return render_template("dashboard.html", stats=stats, recent=recent)


@main_bp.route("/notifications")
@login_required
def notifications():
    db = get_db()
    notes = db.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],),
    ).fetchall()
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (session["user_id"],))
    db.commit()
    return render_template("notifications.html", notifications=notes)
