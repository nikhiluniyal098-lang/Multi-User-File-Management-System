import os, uuid
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, abort
from sqlalchemy import func, text
from config import Config
from models import db
from models.entities import User, Folder, File, FilePermission, ActivityLog, FileAudit
from services.file_service import save_upload, safe_existing_path, ensure_storage
from services.permission_service import permission_for, can_view, can_download, can_edit
from services.audit_service import log_activity, log_file_audit

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    ensure_storage()

    def current_user():
        uid = session.get("user_id")
        return db.session.get(User, uid) if uid else None

    @app.context_processor
    def inject_user():
        return {"current_user": current_user()}

    def login_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not current_user():
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))
            return fn(*args, **kwargs)
        return wrapped

    def admin_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user or user.role != "ADMIN":
                abort(403)
            return fn(*args, **kwargs)
        return wrapped

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if len(username) < 3 or len(password) < 8 or "@" not in email:
                flash("Enter a valid username/email and password (at least 8 characters).", "danger")
            elif User.query.filter((User.username == username) | (User.email == email)).first():
                flash("Username or email already exists.", "danger")
            else:
                user = User(username=username, email=email, role="USER")
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            identity = request.form.get("identity", "").strip().lower()
            user = User.query.filter((func.lower(User.email) == identity) |
                                     (func.lower(User.username) == identity)).first()
            if user and user.is_active and user.check_password(request.form.get("password", "")):
                session.clear()
                session["user_id"] = user.id
                flash(f"Welcome, {user.username}.", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid credentials or inactive account.", "danger")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        user = current_user()
        files_count = File.query.filter_by(user_id=user.id).count()
        folders_count = Folder.query.filter_by(user_id=user.id).count()
        used = db.session.query(func.coalesce(func.sum(File.file_size), 0)).filter_by(user_id=user.id).scalar()
        shared_count = FilePermission.query.filter_by(shared_with_user_id=user.id).count()
        activities = ActivityLog.query.filter_by(user_id=user.id).order_by(ActivityLog.timestamp.desc()).limit(8).all()
        return render_template("dashboard.html", files_count=files_count, folders_count=folders_count,
                               used=used, shared_count=shared_count, activities=activities)

    @app.route("/files")
    @login_required
    def files():
        user = current_user()
        q = request.args.get("q", "").strip()
        query = File.query.filter_by(user_id=user.id)
        if q:
            query = query.filter(File.original_filename.ilike(f"%{q}%"))
        items = query.order_by(File.created_at.desc()).all()
        folders = Folder.query.filter_by(user_id=user.id).order_by(Folder.folder_name).all()
        return render_template("files.html", files=items, folders=folders, q=q)

    @app.route("/upload", methods=["POST"])
    @login_required
    def upload():
        user = current_user()
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            flash("Select a file to upload.", "danger")
            return redirect(url_for("files"))
        folder_id = request.form.get("folder_id") or None
        if folder_id:
            folder = Folder.query.filter_by(id=folder_id, user_id=user.id).first()
            if not folder:
                abort(403)
        try:
            original, stored, path, size, mime = save_upload(uploaded)
            record = File(user_id=user.id, folder_id=folder_id, original_filename=original,
                          stored_filename=stored, file_path=path, file_size=size, mime_type=mime)
            db.session.add(record)
            db.session.flush()
            log_activity(user.id, "UPLOAD", f"Uploaded {original}", record.id)
            log_file_audit(user.id, record.id, "UPLOAD", new_name=original)
            db.session.commit()
            flash("File uploaded successfully.", "success")
        except Exception as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        return redirect(url_for("files"))

    @app.route("/download/<int:file_id>")
    @login_required
    def download(file_id):
        record = db.session.get(File, file_id)
        if not record or not can_download(record, current_user()):
            abort(403)
        try:
            path = safe_existing_path(record.file_path)
            log_activity(current_user().id, "DOWNLOAD", f"Downloaded {record.original_filename}", record.id)
            db.session.commit()
            return send_file(path, as_attachment=True, download_name=record.original_filename)
        except FileNotFoundError:
            abort(404)

    @app.route("/file/<int:file_id>")
    @login_required
    def file_detail(file_id):
        record = db.session.get(File, file_id)
        if not record or not can_view(record, current_user()):
            abort(403)
        return render_template("file_detail.html", file=record, permission=permission_for(record, current_user()),
                              shares=FilePermission.query.filter_by(file_id=file_id).all())

    @app.route("/file/<int:file_id>/rename", methods=["POST"])
    @login_required
    def rename_file(file_id):
        record = db.session.get(File, file_id)
        if not record or not can_edit(record, current_user()):
            abort(403)
        new_name = request.form.get("new_name", "").strip()
        if not new_name or len(new_name) > 255 or "/" in new_name or "\\" in new_name:
            flash("Enter a valid filename.", "danger")
        else:
            old = record.original_filename
            record.original_filename = new_name
            record.updated_at = __import__("datetime").datetime.utcnow()
            log_activity(current_user().id, "RENAME", f"Renamed {old} to {new_name}", record.id)
            log_file_audit(current_user().id, record.id, "RENAME", old, new_name)
            db.session.commit()
            flash("File renamed.", "success")
        return redirect(url_for("file_detail", file_id=file_id))

    @app.route("/file/<int:file_id>/delete", methods=["POST"])
    @login_required
    def delete_file(file_id):
        record = db.session.get(File, file_id)
        if not record or not can_edit(record, current_user()):
            abort(403)
        path = Path(record.file_path)
        log_activity(current_user().id, "DELETE", f"Deleted {record.original_filename}", record.id)
        log_file_audit(current_user().id, record.id, "DELETE", old_name=record.original_filename)
        db.session.delete(record)
        db.session.commit()
        try:
            safe = safe_existing_path(str(path))
            safe.unlink(missing_ok=True)
        except (FileNotFoundError, PermissionError):
            pass
        flash("File deleted.", "success")
        return redirect(url_for("files"))

    @app.route("/folder/create", methods=["POST"])
    @login_required
    def create_folder():
        user = current_user()
        name = request.form.get("folder_name", "").strip()
        parent_id = request.form.get("parent_id") or None
        if not name or len(name) > 180 or "/" in name or "\\" in name:
            flash("Enter a valid folder name.", "danger")
        elif parent_id and not Folder.query.filter_by(id=parent_id, user_id=user.id).first():
            abort(403)
        else:
            db.session.add(Folder(user_id=user.id, folder_name=name, parent_id=parent_id))
            log_activity(user.id, "CREATE_FOLDER", f"Created folder {name}")
            db.session.commit()
            flash("Folder created.", "success")
        return redirect(request.referrer or url_for("files"))

    @app.route("/folder/<int:folder_id>")
    @login_required
    def folder_view(folder_id):
        folder = Folder.query.filter_by(id=folder_id, user_id=current_user().id).first_or_404()
        items = File.query.filter_by(user_id=current_user().id, folder_id=folder.id).all()
        children = Folder.query.filter_by(user_id=current_user().id, parent_id=folder.id).all()
        return render_template("folder.html", folder=folder, files=items, folders=children)

    @app.route("/file/<int:file_id>/move", methods=["POST"])
    @login_required
    def move_file(file_id):
        record = db.session.get(File, file_id)
        if not record or not can_edit(record, current_user()) or record.user_id != current_user().id:
            abort(403)
        folder_id = request.form.get("folder_id") or None
        if folder_id and not Folder.query.filter_by(id=folder_id, user_id=current_user().id).first():
            abort(403)
        record.folder_id = folder_id
        log_activity(current_user().id, "MOVE", f"Moved {record.original_filename}", record.id)
        db.session.commit()
        flash("File moved.", "success")
        return redirect(url_for("files"))

    @app.route("/share/<int:file_id>", methods=["POST"])
    @login_required
    def share_file(file_id):
        record = db.session.get(File, file_id)
        if not record or (record.user_id != current_user().id and current_user().role != "ADMIN"):
            abort(403)
        identity = request.form.get("recipient", "").strip().lower()
        permission = request.form.get("permission", "VIEW")
        recipient = User.query.filter((func.lower(User.email) == identity) |
                                      (func.lower(User.username) == identity)).first()
        if not recipient or recipient.id == record.user_id or permission not in ("VIEW", "DOWNLOAD", "EDIT"):
            flash("Recipient or permission is invalid.", "danger")
        else:
            share = FilePermission.query.filter_by(file_id=file_id, shared_with_user_id=recipient.id).first()
            if share:
                share.permission_type = permission
            else:
                db.session.add(FilePermission(file_id=file_id, owner_id=record.user_id,
                                              shared_with_user_id=recipient.id, permission_type=permission))
            log_activity(current_user().id, "SHARE", f"Shared {record.original_filename} with {recipient.username}", record.id)
            db.session.commit()
            flash("File shared.", "success")
        return redirect(url_for("file_detail", file_id=file_id))

    @app.route("/share/<int:share_id>/revoke", methods=["POST"])
    @login_required
    def revoke_share(share_id):
        share = db.session.get(FilePermission, share_id)
        if not share or (share.owner_id != current_user().id and current_user().role != "ADMIN"):
            abort(403)
        db.session.delete(share)
        log_activity(current_user().id, "REVOKE_SHARE", "Revoked shared file access", share.file_id)
        db.session.commit()
        flash("Access revoked.", "success")
        return redirect(url_for("file_detail", file_id=share.file_id))

    @app.route("/shared")
    @login_required
    def shared():
        shares = FilePermission.query.filter_by(shared_with_user_id=current_user().id).all()
        return render_template("shared.html", shares=shares)

    @app.route("/activity")
    @login_required
    def activity():
        logs = ActivityLog.query.filter_by(user_id=current_user().id).order_by(ActivityLog.timestamp.desc()).limit(200).all()
        return render_template("activity.html", logs=logs)

    @app.route("/admin")
    @login_required
    @admin_required
    def admin():
        users = User.query.order_by(User.created_at.desc()).all()
        all_files = File.query.order_by(File.created_at.desc()).limit(100).all()
        total_bytes = db.session.query(func.coalesce(func.sum(File.file_size), 0)).scalar()
        logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(30).all()
        return render_template("admin.html", users=users, files=all_files, total_bytes=total_bytes, logs=logs)

    @app.route("/admin/user/<int:user_id>/toggle", methods=["POST"])
    @login_required
    @admin_required
    def toggle_user(user_id):
        user = db.session.get(User, user_id)
        if not user or user.id == current_user().id:
            abort(400)
        user.is_active = not user.is_active
        db.session.commit()
        flash("User status updated.", "success")
        return redirect(url_for("admin"))

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("error.html", code=403, message="You do not have permission to perform this action."), 403

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", code=404, message="The requested item was not found."), 404

    return app

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        # Tables are created by `python init_db.py`; do not silently alter schema here.
        pass
    app.run(debug=True)
