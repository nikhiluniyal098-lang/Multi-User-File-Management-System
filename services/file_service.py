import os, uuid, mimetypes
from pathlib import Path
from werkzeug.utils import secure_filename
from services.synchronization import get_thread_lock
from services.file_lock import locked_file
from config import Config

ALLOWED_EXTENSIONS = {
    "txt", "pdf", "png", "jpg", "jpeg", "gif", "csv", "doc", "docx",
    "xls", "xlsx", "ppt", "pptx", "zip", "py", "cpp", "c", "java", "md"
}

def ensure_storage():
    (Config.STORAGE_ROOT / "uploads").mkdir(parents=True, exist_ok=True)
    (Config.STORAGE_ROOT / "temp").mkdir(parents=True, exist_ok=True)

def save_upload(upload):
    ensure_storage()
    original = secure_filename(upload.filename or "")
    if not original or "." not in original:
        raise ValueError("Choose a file with a valid filename.")
    ext = original.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("This file type is not allowed.")
    stored = f"{uuid.uuid4().hex}.{ext}"
    target = Config.STORAGE_ROOT / "uploads" / stored
    temp = Config.STORAGE_ROOT / "temp" / f"{stored}.part"
    with open(temp, "wb") as out:
        upload.save(out)
        out.flush()
        os.fsync(out.fileno())
    os.replace(temp, target)
    return original, stored, str(target), target.stat().st_size, mimetypes.guess_type(original)[0]

def safe_existing_path(raw_path):
    root = (Config.STORAGE_ROOT / "uploads").resolve()
    candidate = Path(raw_path).resolve()
    if root not in candidate.parents:
        raise PermissionError("Invalid storage path.")
    if not candidate.is_file():
        raise FileNotFoundError("The stored file is missing.")
    return candidate

def replace_contents(file_record, incoming_stream):
    path = safe_existing_path(file_record.file_path)
    lock = get_thread_lock(file_record.id)
    with lock:
        temp = path.with_name(path.name + ".tmp")
        try:
            with locked_file(path, "rb", exclusive=True):
                with open(temp, "wb") as out:
                    while True:
                        chunk = incoming_stream.read(1024 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(temp, path)
        finally:
            if temp.exists():
                temp.unlink(missing_ok=True)
    return path.stat().st_size
