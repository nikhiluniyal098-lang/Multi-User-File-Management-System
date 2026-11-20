# CloudVault — Multi-User File Management System

A Windows-compatible academic mini Google Drive built with Python, Flask, MySQL/InnoDB, HTML, CSS and Bootstrap. It demonstrates OS file management, synchronization, inter-process locking, resource ordering, atomic replacement and DBMS transactions/concurrency concepts.

## Features
- User registration/login with Werkzeug password hashing and session authentication.
- Admin role, user activation/deactivation, system file overview.
- Upload/download, search, folder creation and nesting, rename, move, delete.
- Sharing with VIEW, DOWNLOAD and EDIT permissions, plus revocation.
- Activity history and file audit records.
- Upload extension/size limits, generated storage names, path containment checks.
- `threading.RLock` for in-process critical sections and `portalocker` for cross-process file locks.
- Multi-file lock acquisition in ascending file-ID order (circular-wait prevention).
- Temporary upload then `os.replace()` to avoid exposing partially uploaded files.
- MySQL InnoDB tables, foreign keys, unique constraints, views and indexes.

## Windows setup (PowerShell)
1. Install Python 3.11+ and MySQL 8.0. Create a schema:
   ```sql
   CREATE DATABASE file_mgmt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
2. Open this folder in VS Code / PowerShell:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   Copy-Item .env.example .env
   ```
3. Edit `.env`; set a strong `SECRET_KEY` and your MySQL `DATABASE_URL`, for example:
   `mysql+pymysql://root:YOUR_PASSWORD@localhost/file_mgmt?charset=utf8mb4`
4. Install packages and initialize:
   ```powershell
   pip install -r requirements.txt
   python init_db.py
   ```
5. Optional initial admin account (set before initialization):
   ```powershell
   $env:ADMIN_EMAIL="admin@example.com"
   $env:ADMIN_PASSWORD="ChangeThisPassword!"
   $env:ADMIN_USERNAME="admin"
   python init_db.py
   ```
6. Start:
   ```powershell
   python app.py
   ```
   Open http://127.0.0.1:5000

## Database notes
`init_db.py` creates tables from SQLAlchemy models. `database/views.sql` adds the storage and shared-file views. Run it in MySQL Workbench after initialization. `database/triggers.sql` documents why a duplicate trigger is not installed: the application writes `files_audit`. Do not enable both audit mechanisms unless one is removed.

The app defaults to MySQL. Automated tests use temporary SQLite databases to keep tests isolated and runnable without a MySQL server. SQLite tests validate application behavior, not MySQL row-lock semantics. For the MySQL concurrency demonstration, use InnoDB and inspect queries with `EXPLAIN`.

## OS concepts implemented
- File I/O and metadata: `services/file_service.py` uses `pathlib`, `os.replace`, `stat`, file reads/writes and dedicated storage.
- Mutual exclusion: `services/synchronization.py` uses `threading.RLock` to serialize threads in one Python process.
- Inter-process synchronization: `services/file_lock.py` uses `portalocker`; OS-managed locks coordinate separate Windows processes.
- Critical section/race prevention: write operations acquire the thread lock and exclusive file lock before replacing content.
- Atomic upload: write to a temporary file, flush + `os.fsync`, then `os.replace` on the same volume.
- Deadlock prevention: `services/deadlock_prevention.py` sorts all requested file IDs ascending before acquiring locks. This removes circular wait for cooperating code paths that follow the same rule.
- Timeout is not deadlock prevention: a timeout bounds waiting and reports failure; resource ordering prevents circular wait.

## DBMS concepts
- ACID: database changes are grouped and committed or rolled back; InnoDB provides transactional durability and consistency enforcement.
- Constraints: PK/FK, unique username/email, unique stored filename, unique (file,user) share and NOT NULL columns.
- Isolation/concurrency: InnoDB transactions and row-level locks. For critical inventory-like changes, use `SELECT ... FOR UPDATE` inside a transaction; this starter application keeps file data in separate physical storage.
- Deadlock handling: MySQL error 1213 (deadlock) and 1205 (lock wait timeout) should be rolled back and selected idempotent transactions retried with bounded retries. `services/transaction_service.py` provides the retry wrapper.
- Indexes: user_id, folder_id, file_id and shared_with_user_id indexes support common filters. Use `EXPLAIN SELECT ...` in MySQL Workbench.
- Views: `user_storage_usage` and `shared_file_listing`.
- Audit: app-level audit records are used to avoid duplicate trigger + application rows.

## Architecture
```mermaid
flowchart TD
 Browser[Browser: HTML/CSS/Bootstrap] --> Routes[Flask routes]
 Routes --> Auth[Authentication and RBAC]
 Routes --> Services[File and synchronization services]
 Routes --> ORM[SQLAlchemy ORM]
 Services --> Disk[(Windows file storage)]
 Services --> Locks[threading + portalocker]
 ORM --> DB[(MySQL 8 / InnoDB)]
 DB --> Audit[Activity and audit tables]
```

## ER diagram
```mermaid
erDiagram
 USERS ||--o{ FILES : owns
 USERS ||--o{ FOLDERS : creates
 FOLDERS ||--o{ FOLDERS : contains
 FOLDERS ||--o{ FILES : stores
 FILES ||--o{ FILE_PERMISSIONS : shared_by
 USERS ||--o{ FILE_PERMISSIONS : receives
 USERS ||--o{ ACTIVITY_LOGS : performs
 FILES ||--o{ ACTIVITY_LOGS : concerns
```

## Team responsibilities
1. **Member 1 — File protection/access control:** safe paths, ownership, authorization, password hashing, PK/FK and constraints.
2. **Member 2 — Synchronization/deadlock:** mutex, critical sections, race conditions, portalocker, ascending resource ordering, lock timeouts, DB concurrency and bounded retry policy.
3. **Member 3 — File I/O/transactions:** upload/read/write/delete/move, temporary files, atomic replacement, ACID, commit/rollback, normalization and relationships.
4. **Member 4 — Metadata/concurrency/audit:** stat metadata, directory and storage usage, indexes, EXPLAIN, views, audit logs and connection pooling configuration.

## Tests and demonstrations
```powershell
python -m pytest
python demos\synchronization_demo.py
python demos\deadlock_order_demo.py
```
The multiprocessing demos must be run as scripts on Windows (not from an interactive interpreter) due to the spawn start method.

## Project demonstration script
1. Register two accounts in separate browser sessions.
2. Log in as user A; upload a document and create a folder.
3. Open file details; share with user B using VIEW.
4. Log in as B; open Shared with me. Verify download is not allowed for VIEW.
5. Change permission to DOWNLOAD; verify B can download. Revoke access and verify B receives 403.
6. Upload a second file and move it into a folder.
7. Run the synchronization demo; observe Process B waits for Process A's exclusive lock.
8. Run the deadlock-order demo; both processes print lock IDs in ascending order.
9. Show commits/rollbacks in `tests/test_transactions.py`.
10. Show the activity page and `files_audit` table.

## Viva quick notes
- **Mutex:** mutual exclusion primitive; only one thread enters a protected critical section at a time.
- **Critical section:** code that accesses shared mutable state/resource.
- **Race condition:** result depends on timing/interleaving of concurrent operations.
- **File lock:** OS-mediated coordination for processes accessing the same file.
- **Deadlock:** processes wait forever for resources held by one another.
- **Resource ordering:** impose a total order on resources and acquire only in that order; circular wait cannot form.
- **Timeout:** limits waiting duration; it does not itself prevent deadlock.
- **Atomic replacement:** a completed temporary file replaces the destination in one filesystem operation.
- **ACID:** Atomicity, Consistency, Isolation, Durability.
- **COMMIT/ROLLBACK:** make a transaction permanent / undo its uncommitted changes.
- **Normalization:** organize relations to reduce redundancy and update anomalies.
- **Index:** auxiliary structure that speeds lookups at the cost of storage and write overhead.
- **View:** saved query presented as a virtual table.
- **Trigger:** database code invoked automatically by an event.
- **Row-level locking:** locks selected records rather than the entire table.

## Limitations and future scope
- File preview/edit-in-browser, version history, recycle bin, password reset, email notifications, CSRF tokens, malware scanning, quota enforcement and resumable uploads are future enhancements.
- This is an academic starter, not a hardened public cloud service. Deploy behind HTTPS, set a strong secret, add CSRF protection, rate limiting, malware scanning and operational backups before production use.
