"""MySQL/InnoDB row-lock example for viva and integration use."""
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from models import db
import time

def lock_file_row(file_id):
    """Lock one file row until the surrounding transaction commits/rolls back."""
    return db.session.execute(
        text("SELECT id, user_id FROM files WHERE id=:file_id FOR UPDATE"),
        {"file_id": file_id}
    ).first()

def update_file_metadata_with_retry(file_id, new_name, attempts=3):
    """Example bounded retry for MySQL deadlock (1213) / lock wait timeout (1205)."""
    for attempt in range(attempts):
        try:
            row = lock_file_row(file_id)
            if row is None:
                raise LookupError("File does not exist")
            db.session.execute(
                text("UPDATE files SET original_filename=:name, updated_at=UTC_TIMESTAMP() WHERE id=:id"),
                {"name": new_name, "id": file_id}
            )
            db.session.commit()
            return
        except OperationalError as exc:
            db.session.rollback()
            code = getattr(getattr(exc, "orig", None), "args", [None])[0]
            if code not in (1205, 1213) or attempt == attempts - 1:
                raise
            time.sleep(0.1 * (attempt + 1))
        except Exception:
            db.session.rollback()
            raise
