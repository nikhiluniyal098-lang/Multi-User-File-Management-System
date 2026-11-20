# Architecture and member file ownership

## Main request flow
Browser -> Flask route -> authentication/permission checks -> service layer -> filesystem and/or SQLAlchemy -> MySQL InnoDB.

## Member 1 — Access control
- `models/entities.py` (User and ownership relationships)
- `services/permission_service.py`
- `services/file_service.py` (safe path validation)
- `routes/auth.py` is consolidated into `app.py` in this compact implementation.
- Relevant tests: `tests/test_auth.py`, `tests/test_permissions.py`

## Member 2 — Synchronization and deadlock prevention
- `services/synchronization.py`
- `services/file_lock.py`
- `services/deadlock_prevention.py`
- `services/transaction_service.py`
- `demos/synchronization_demo.py`
- `demos/deadlock_order_demo.py`
- `tests/test_synchronization.py`, `tests/test_deadlock_prevention.py`

## Member 3 — File I/O and transactions
- `services/file_service.py`
- `services/audit_service.py`
- `init_db.py`
- `tests/test_transactions.py`

## Member 4 — Metadata, concurrency and audit
- `models/entities.py` (metadata fields and indexes)
- `database/views.sql`
- `database/triggers.sql`
- `services/audit_service.py`
- `README.md` (EXPLAIN and metadata instructions)

Note: Routes are consolidated in `app.py` to make the first run simple. They can be split into Flask blueprints without changing the service/model responsibilities.
