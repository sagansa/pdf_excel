-- Migration 044: Add marks.is_coretax as the explicit Coretax selector
-- This simplifies Coretax inclusion to a single checkbox on Mark.

SET @dbname = DATABASE();
SET @tablename = 'marks';
SET @columnname = 'is_coretax';

-- 1) Add marks.is_coretax when missing
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND COLUMN_NAME = @columnname
    ) > 0,
    'SELECT 1',
    CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' BOOLEAN DEFAULT FALSE')
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2) Normalize NULL values to FALSE
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = 'marks'
       AND COLUMN_NAME = 'is_coretax'
    ) > 0,
    'UPDATE marks SET is_coretax = FALSE WHERE is_coretax IS NULL',
    'SELECT 1'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3) Backfill from legacy rule:
--    if tax_report has value, mark as Coretax.
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = 'marks'
       AND COLUMN_NAME = 'is_coretax'
    ) > 0,
    "UPDATE marks SET is_coretax = TRUE WHERE COALESCE(is_coretax, 0) = 0 AND tax_report IS NOT NULL AND TRIM(tax_report) != ''",
    'SELECT 1'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
