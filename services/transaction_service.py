import time
from sqlalchemy.exc import OperationalError
from models import db

def run_with_deadlock_retry(operation, attempts=3, delay=0.15):
    """Retry only MySQL deadlock/lock-wait failures; every failed attempt rolls back."""
    for attempt in range(attempts):
        try:
            result = operation()
            db.session.commit()
            return result
        except OperationalError as exc:
            db.session.rollback()
            code = getattr(getattr(exc, "orig", None), "args", [None])[0]
            if code not in (1205, 1213) or attempt == attempts - 1:
                raise
            time.sleep(delay * (attempt + 1))
        except Exception:
            db.session.rollback()
            raise
