from models.entities import FilePermission

def permission_for(file_record, user):
    if user.id == file_record.user_id or user.role == "ADMIN":
        return "OWNER"
    share = FilePermission.query.filter_by(file_id=file_record.id, shared_with_user_id=user.id).first()
    return share.permission_type if share else None

def can_view(file_record, user):
    return permission_for(file_record, user) in ("OWNER", "VIEW", "DOWNLOAD", "EDIT")

def can_download(file_record, user):
    return permission_for(file_record, user) in ("OWNER", "DOWNLOAD", "EDIT")

def can_edit(file_record, user):
    return permission_for(file_record, user) in ("OWNER", "EDIT")
