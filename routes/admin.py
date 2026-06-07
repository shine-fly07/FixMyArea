import csv
import io

from flask import Blueprint, Response, flash, redirect, render_template, request, session, url_for

from models.database import CATEGORIES, PRIORITIES, STATUSES, admin_required, get_db


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def chart_rows(rows):
    return [{"label": row["label"], "value": row["value"]} for row in rows]


def build_filters(args):
    clauses = ["1 = 1"]
    params = []
    for field in ("status", "category", "priority", "location"):
        value = args.get(field, "").strip()
        if value:
            if field == "location":
                clauses.append("c.location LIKE ?")
                params.append(f"%{value}%")
            else:
                clauses.append(f"c.{field} = ?")
                params.append(value)
    date_from = args.get("date_from", "").strip()
    date_to = args.get("date_to", "").strip()
    search = args.get("search", "").strip()
    if date_from:
        clauses.append("date(c.created_at) >= date(?)")
        params.append(date_from)
    if date_to:
        clauses.append("date(c.created_at) <= date(?)")
        params.append(date_to)
    if search:
        clauses.append("(c.title LIKE ? OR c.description LIKE ? OR c.complaint_id LIKE ? OR u.name LIKE ?)")
        params.extend([f"%{search}%"] * 4)
    return " AND ".join(clauses), params


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    db = get_db()
    cards = {
        "total": db.execute("SELECT COUNT(*) total FROM complaints").fetchone()["total"],
        "pending": db.execute("SELECT COUNT(*) total FROM complaints WHERE status = 'Pending'").fetchone()["total"],
        "progress": db.execute("SELECT COUNT(*) total FROM complaints WHERE status = 'In Progress'").fetchone()["total"],
        "resolved": db.execute("SELECT COUNT(*) total FROM complaints WHERE status = 'Resolved'").fetchone()["total"],
        "users": db.execute("SELECT COUNT(*) total FROM users WHERE role = 'citizen'").fetchone()["total"],
        "critical": db.execute("SELECT COUNT(*) total FROM complaints WHERE priority = 'Critical'").fetchone()["total"],
    }
    charts = {
        "categories": chart_rows(db.execute("SELECT category label, COUNT(*) value FROM complaints GROUP BY category").fetchall()),
        "statuses": chart_rows(db.execute("SELECT status label, COUNT(*) value FROM complaints GROUP BY status").fetchall()),
        "reported": chart_rows(db.execute(
            "SELECT date(created_at) label, COUNT(*) value FROM complaints GROUP BY date(created_at) ORDER BY date(created_at)"
        ).fetchall()),
        "priorities": chart_rows(db.execute("SELECT priority label, COUNT(*) value FROM complaints GROUP BY priority").fetchall()),
        "resolution": chart_rows(db.execute(
            """
            SELECT 'Resolved' label, COUNT(*) value FROM complaints WHERE status = 'Resolved'
            UNION ALL
            SELECT 'Open' label, COUNT(*) value FROM complaints WHERE status != 'Resolved'
            """
        ).fetchall()),
    }
    recent = db.execute(
        """
        SELECT c.*, u.name AS user_name
        FROM complaints c JOIN users u ON u.id = c.user_id
        ORDER BY c.created_at DESC LIMIT 6
        """
    ).fetchall()
    return render_template("admin/dashboard.html", cards=cards, charts=charts, recent=recent)


@admin_bp.route("/complaints")
@admin_required
def complaints():
    db = get_db()
    where, params = build_filters(request.args)
    sort = request.args.get("sort", "created_at")
    allowed_sort = {"created_at", "status", "priority", "category", "location"}
    sort_column = sort if sort in allowed_sort else "created_at"
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 10
    total = db.execute(
        f"SELECT COUNT(*) total FROM complaints c JOIN users u ON u.id = c.user_id WHERE {where}",
        params,
    ).fetchone()["total"]
    complaints_list = db.execute(
        f"""
        SELECT c.*, u.name AS user_name, u.email AS user_email
        FROM complaints c JOIN users u ON u.id = c.user_id
        WHERE {where}
        ORDER BY c.{sort_column} DESC LIMIT ? OFFSET ?
        """,
        [*params, per_page, (page - 1) * per_page],
    ).fetchall()
    pages = (total + per_page - 1) // per_page
    return render_template(
        "admin/complaints.html",
        complaints=complaints_list,
        categories=CATEGORIES,
        statuses=STATUSES,
        priorities=PRIORITIES,
        page=page,
        pages=pages,
    )


@admin_bp.route("/complaints/<int:complaint_id>/update", methods=["POST"])
@admin_required
def update_complaint(complaint_id):
    db = get_db()
    complaint = db.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if complaint is None:
        flash("Complaint not found.", "danger")
        return redirect(url_for("admin.complaints"))

    new_status = request.form.get("status", complaint["status"])
    priority = request.form.get("priority", complaint["priority"])
    remarks = request.form.get("remarks", "").strip() or "Status reviewed by administrator."
    if new_status not in STATUSES or priority not in PRIORITIES:
        flash("Invalid status or priority.", "danger")
        return redirect(url_for("complaints.detail", complaint_id=complaint_id))

    db.execute(
        "UPDATE complaints SET status = ?, priority = ? WHERE id = ?",
        (new_status, priority, complaint_id),
    )
    db.execute(
        "INSERT INTO complaint_history (complaint_id, old_status, new_status, remarks, updated_by) VALUES (?, ?, ?, ?, ?)",
        (complaint_id, complaint["status"], new_status, remarks, session["user_id"]),
    )
    db.execute(
        "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
        (complaint["user_id"], f"{complaint['complaint_id']} status changed to {new_status}."),
    )
    db.commit()
    flash("Complaint updated and citizen notified.", "success")
    return redirect(url_for("complaints.detail", complaint_id=complaint_id))


@admin_bp.route("/complaints/<int:complaint_id>/delete", methods=["POST"])
@admin_required
def delete_complaint(complaint_id):
    db = get_db()
    db.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
    db.commit()
    flash("Complaint deleted.", "info")
    return redirect(url_for("admin.complaints"))


@admin_bp.route("/users")
@admin_required
def users():
    db = get_db()
    users_list = db.execute(
        """
        SELECT u.*, COUNT(c.id) AS complaint_count
        FROM users u LEFT JOIN complaints c ON c.user_id = u.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
        """
    ).fetchall()
    return render_template("admin/users.html", users=users_list)


@admin_bp.route("/statistics")
@admin_required
def statistics():
    db = get_db()
    by_location = db.execute(
        "SELECT location, COUNT(*) total FROM complaints GROUP BY location ORDER BY total DESC LIMIT 10"
    ).fetchall()
    by_month = db.execute(
        "SELECT strftime('%Y-%m', created_at) month, COUNT(*) total FROM complaints GROUP BY month ORDER BY month"
    ).fetchall()
    rejected = db.execute("SELECT COUNT(*) total FROM complaints WHERE status = 'Rejected'").fetchone()["total"]
    return render_template("admin/statistics.html", by_location=by_location, by_month=by_month, rejected=rejected)


@admin_bp.route("/export.csv")
@admin_required
def export_csv():
    db = get_db()
    where, params = build_filters(request.args)
    rows = db.execute(
        f"""
        SELECT c.complaint_id, c.title, c.category, c.location, c.status, c.priority,
               c.created_at, u.name, u.email
        FROM complaints c JOIN users u ON u.id = c.user_id
        WHERE {where}
        ORDER BY c.created_at DESC
        """,
        params,
    ).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Complaint ID", "Title", "Category", "Location", "Status", "Priority", "Created At", "Citizen", "Email"])
    for row in rows:
        writer.writerow(list(row))
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=fixmyarea-complaints.csv"},
    )
