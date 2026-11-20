from models.entities import ActivityLog, FileAudit
from models import db

def log_activity(user_id, action, description, file_id=None):
    db.session.add(ActivityLog(user_id=user_id, file_id=file_id, action=action, description=description))

def log_file_audit(user_id, file_id, operation, old_name=None, new_name=None):
    db.session.add(FileAudit(user_id=user_id, file_id=file_id, operation=operation,
                             old_filename=old_name, new_filename=new_name))
