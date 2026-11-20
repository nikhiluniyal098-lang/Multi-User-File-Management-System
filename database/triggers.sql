USE file_mgmt;
-- Application code writes files_audit to avoid duplicate audit rows.
-- This optional trigger is intentionally not installed alongside app-level auditing.
-- If you choose database-side auditing instead, implement the trigger and remove
-- log_file_audit() calls from the application before enabling it.
