import secrets
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from models.database import CATEGORIES, get_db, login_required


complaints_bp = Blueprint("complaints", __name__, url_prefix="/complaints")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("Only PNG, JPG, JPEG, GIF, and WEBP images are allowed.")
    filename = secure_filename(file_storage.filename)
    suffix = Path(filename).suffix.lower()
    stored_name = f"{secrets.token_hex(12)}{suffix}"
    file_storage.save(current_app.config["UPLOAD_FOLDER"] / stored_name)
    return stored_name


def generate_complaint_code(db):
    next_id = db.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM complaints").fetchone()["next_id"]
    return f"FMA-{next_id:06d}"


@complaints_bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@complaints_bp.route("/")
@login_required
def list_complaints():
    db = get_db()
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "created_at")
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 8
    allowed_sort = {"created_at", "status", "priority", "category", "location"}
    sort_column = sort if sort in allowed_sort else "created_at"

    clauses = ["user_id = ?"]
    params = [session["user_id"]]
    if search:
        clauses.append("(title LIKE ? OR description LIKE ? OR location LIKE ? OR complaint_id LIKE ?)")
        params.extend([f"%{search}%"] * 4)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if category:
        clauses.append("category = ?")
        params.append(category)

    where = " AND ".join(clauses)
    total = db.execute(f"SELECT COUNT(*) total FROM complaints WHERE {where}", params).fetchone()["total"]
    complaints = db.execute(
        f"SELECT * FROM complaints WHERE {where} ORDER BY {sort_column} DESC LIMIT ? OFFSET ?",
        [*params, per_page, (page - 1) * per_page],
    ).fetchall()
    pages = (total + per_page - 1) // per_page
    return render_template(
        "complaints/list.html",
        complaints=complaints,
        categories=CATEGORIES,
        page=page,
        pages=pages,
    )


@complaints_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        location = request.form.get("location", "").strip()
        if not title or not description or not category or not location:
            flash("Title, description, category, and location are required.", "danger")
            return render_template("complaints/form.html", categories=CATEGORIES, complaint=None)
        if category not in CATEGORIES:
            flash("Please choose a valid category.", "danger")
            return render_template("complaints/form.html", categories=CATEGORIES, complaint=None)

        try:
            image_path = save_image(request.files.get("image"))
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("complaints/form.html", categories=CATEGORIES, complaint=None)

        db = get_db()
        code = generate_complaint_code(db)
        cursor = db.execute(
            """
            INSERT INTO complaints
            (complaint_id, title, description, category, location, image_path, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (code, title, description, category, location, image_path, session["user_id"]),
        )
        db.execute(
            "INSERT INTO complaint_history (complaint_id, old_status, new_status, remarks, updated_by) VALUES (?, ?, ?, ?, ?)",
            (cursor.lastrowid, None, "Pending", "Complaint submitted by citizen.", session["user_id"]),
        )
        db.commit()
        flash("Complaint submitted successfully.", "success")
        return redirect(url_for("complaints.detail", complaint_id=cursor.lastrowid))

    return render_template("complaints/form.html", categories=CATEGORIES, complaint=None)


@complaints_bp.route("/<int:complaint_id>")
@login_required
def detail(complaint_id):
    db = get_db()
    complaint = db.execute(
        "SELECT c.*, u.name AS user_name, u.email AS user_email FROM complaints c JOIN users u ON u.id = c.user_id WHERE c.id = ?",
        (complaint_id,),
    ).fetchone()
    if complaint is None or (session.get("role") != "admin" and complaint["user_id"] != session["user_id"]):
        flash("Complaint not found.", "danger")
        return redirect(url_for("complaints.list_complaints"))
    history = db.execute(
        "SELECT h.*, u.name AS updater FROM complaint_history h JOIN users u ON u.id = h.updated_by WHERE h.complaint_id = ? ORDER BY h.updated_at",
        (complaint_id,),
    ).fetchall()
    return render_template("complaints/detail.html", complaint=complaint, history=history)


@complaints_bp.route("/<int:complaint_id>/edit", methods=["GET", "POST"])
@login_required
def edit(complaint_id):
    db = get_db()
    complaint = db.execute("SELECT * FROM complaints WHERE id = ? AND user_id = ?", (complaint_id, session["user_id"])).fetchone()
    if complaint is None:
        flash("Complaint not found.", "danger")
        return redirect(url_for("complaints.list_complaints"))
    if complaint["status"] != "Pending":
        flash("Complaints can only be edited before they are assigned or reviewed.", "warning")
        return redirect(url_for("complaints.detail", complaint_id=complaint_id))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        location = request.form.get("location", "").strip()
        if not title or not description or not category or not location:
            flash("All complaint fields are required.", "danger")
            return render_template("complaints/form.html", categories=CATEGORIES, complaint=complaint)
        try:
            image_path = save_image(request.files.get("image")) or complaint["image_path"]
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("complaints/form.html", categories=CATEGORIES, complaint=complaint)
        db.execute(
            "UPDATE complaints SET title = ?, description = ?, category = ?, location = ?, image_path = ? WHERE id = ?",
            (title, description, category, location, image_path, complaint_id),
        )
        db.commit()
        flash("Complaint updated.", "success")
        return redirect(url_for("complaints.detail", complaint_id=complaint_id))

    return render_template("complaints/form.html", categories=CATEGORIES, complaint=complaint)
