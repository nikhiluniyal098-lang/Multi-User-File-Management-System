from contextlib import ExitStack
from pathlib import Path
from services.file_lock import locked_file

def ordered_file_locks(file_items, exclusive=True, timeout=None):
    """Acquire (file_id, path) locks in ascending ID order to prevent circular wait."""
    ordered = sorted(file_items, key=lambda item: int(item[0]))
    ids = [int(item[0]) for item in ordered]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate file IDs are not allowed in a lock request")
    with ExitStack() as stack:
        handles = []
        for file_id, path in ordered:
            handle = stack.enter_context(
                locked_file(Path(path), mode="rb", exclusive=exclusive, timeout=timeout)
            )
            handles.append((int(file_id), handle))
        yield_locks = handles
        # ExitStack releases in reverse order, including on exceptions.
        yield yield_locks

from contextlib import contextmanager
@contextmanager
def ordered_file_locks(file_items, exclusive=True, timeout=None):
    ordered = sorted(file_items, key=lambda item: int(item[0]))
    ids = [int(item[0]) for item in ordered]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate file IDs are not allowed")
    with ExitStack() as stack:
        acquired = []
        for file_id, path in ordered:
            handle = stack.enter_context(locked_file(path, "rb", exclusive, timeout))
            acquired.append((int(file_id), handle))
        yield acquired
