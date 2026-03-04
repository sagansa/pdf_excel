-- Migration 045: Support separate COA mappings for Real vs Coretax reports.
-- Adds mark_coa_mapping.report_type and updates uniqueness scope.

SET @dbname = DATABASE();
SET @tablename = 'mark_coa_mapping';
SET @columnname = 'report_type';

-- 1) Add report_type column if missing
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND COLUMN_NAME = @columnname
    ) > 0,
    'SELECT 1',
    CONCAT(
      'ALTER TABLE ', @tablename,
      ' ADD COLUMN ', @columnname, " VARCHAR(20) NOT NULL DEFAULT 'real' AFTER mapping_type"
    )
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2) Normalize existing values
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND COLUMN_NAME = @columnname
    ) > 0,
    "UPDATE mark_coa_mapping
     SET report_type = CASE
       WHEN report_type IS NULL OR TRIM(report_type) = '' THEN 'real'
       WHEN LOWER(TRIM(report_type)) = 'coretax' THEN 'coretax'
       ELSE 'real'
     END",
    'SELECT 1'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3) Drop old unique key if exists
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND INDEX_NAME = 'unique_mark_coa'
    ) > 0,
    'ALTER TABLE mark_coa_mapping DROP INDEX unique_mark_coa',
    'SELECT 1'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 4) Add new unique key (mark + coa + side + report_type) if missing
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND INDEX_NAME = 'unique_mark_coa_scope'
    ) > 0,
    'SELECT 1',
    'ALTER TABLE mark_coa_mapping ADD UNIQUE KEY unique_mark_coa_scope (mark_id, coa_id, mapping_type, report_type)'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 5) Add supporting index if missing
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND INDEX_NAME = 'idx_mark_report_type'
    ) > 0,
    'SELECT 1',
    'CREATE INDEX idx_mark_report_type ON mark_coa_mapping (mark_id, report_type)'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
