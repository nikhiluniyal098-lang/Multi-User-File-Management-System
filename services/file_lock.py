from contextlib import contextmanager
from pathlib import Path
import portalocker
from config import Config

@contextmanager
def locked_file(path, mode="rb", exclusive=False, timeout=None):
    """Windows-compatible OS file lock; the OS releases it when the handle closes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    timeout = Config.LOCK_TIMEOUT_SECONDS if timeout is None else timeout
    flags = portalocker.LOCK_EX if exclusive else portalocker.LOCK_SH
    handle = open(path, mode)
    try:
        portalocker.lock(handle, flags, timeout=timeout)
        yield handle
    except portalocker.exceptions.LockException as exc:
        raise TimeoutError(f"Could not acquire lock for {path.name}") from exc
    finally:
        try:
            portalocker.unlock(handle)
        except Exception:
            pass
        handle.close()
