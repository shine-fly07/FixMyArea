import os
from pathlib import Path

from flask import Flask, redirect, request, session, url_for

from models.database import init_db, unread_notification_count
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.complaints import complaints_bp
from routes.main import main_bp


BASE_DIR = Path(__file__).resolve().parent


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-this-secret-key-in-production"
    app.config["DATABASE"] = BASE_DIR / "database" / "fixmyarea.db"
    app.config["UPLOAD_FOLDER"] = BASE_DIR / "uploads"
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
    app.config["DATABASE"].parent.mkdir(parents=True, exist_ok=True)

    init_db(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        count = 0
        if session.get("user_id") and session.get("role") != "admin":
            count = unread_notification_count(session["user_id"])

        def page_url(page):
            args = request.args.to_dict(flat=True)
            args["page"] = page
            return url_for(request.endpoint, **(request.view_args or {}), **args)

        return {"unread_count": count, "page_url": page_url}

    @app.errorhandler(404)
    def not_found(_error):
        return redirect(url_for("main.index"))

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
