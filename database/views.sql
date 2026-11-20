USE file_mgmt;
CREATE OR REPLACE VIEW user_storage_usage AS
SELECT u.id AS user_id, u.username, COALESCE(SUM(f.file_size),0) AS bytes_used,
       COUNT(f.id) AS file_count
FROM users u LEFT JOIN files f ON f.user_id=u.id GROUP BY u.id,u.username;

CREATE OR REPLACE VIEW shared_file_listing AS
SELECT p.id AS permission_id, p.permission_type, p.shared_with_user_id,
       f.id AS file_id, f.original_filename, f.file_size, f.user_id AS owner_id
FROM file_permissions p INNER JOIN files f ON f.id=p.file_id;
