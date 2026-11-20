from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("ADMIN", "USER"), nullable=False, default="USER")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    files = db.relationship("File", backref="owner", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Folder(db.Model):
    __tablename__ = "folders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    folder_name = db.Column(db.String(180), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    parent = db.relationship("Folder", remote_side=[id], backref="children")

class File(db.Model):
    __tablename__ = "files"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    folder_id = db.Column(db.Integer, db.ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False)
    file_path = db.Column(db.String(600), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False, default=0)
    mime_type = db.Column(db.String(160))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    folder = db.relationship("Folder", backref="files")

class FilePermission(db.Model):
    __tablename__ = "file_permissions"
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shared_with_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_type = db.Column(db.Enum("VIEW", "DOWNLOAD", "EDIT"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("file_id", "shared_with_user_id", name="uq_file_share"),)

class ActivityLog(db.Model):
    __tablename__ = "activity_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class FileAudit(db.Model):
    __tablename__ = "files_audit"
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, nullable=True, index=True)
    user_id = db.Column(db.Integer, nullable=True)
    old_filename = db.Column(db.String(255))
    new_filename = db.Column(db.String(255))
    operation = db.Column(db.String(80), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

FilePermission.file = db.relationship('File', backref=db.backref('permissions', lazy=True))
