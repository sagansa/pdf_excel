-- Migration 033: Remove retired Prepaid Rent & Amortization feature
-- This removes prepaid table/data and reference columns tied to the feature.

SET @dbname = DATABASE();

-- 1) Drop FK rental_contracts -> prepaid_expenses if exists
SET @tablename = 'rental_contracts';
SET @constraintname = 'fk_rental_prepaid_expense';
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND CONSTRAINT_NAME = @constraintname
    ) > 0,
    CONCAT('ALTER TABLE ', @tablename, ' DROP FOREIGN KEY ', @constraintname),
    'SELECT 1'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2) Drop index on rental_contracts.prepaid_expense_id if exists
SET @indexname = 'idx_rental_prepaid';
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND INDEX_NAME = @indexname
    ) > 0,
    CONCAT('DROP INDEX ', @indexname, ' ON ', @tablename),
    'SELECT 1'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3) Drop rental_contracts.prepaid_expense_id column if exists
SET @columnname = 'prepaid_expense_id';
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND COLUMN_NAME = @columnname
    ) > 0,
    CONCAT('ALTER TABLE ', @tablename, ' DROP COLUMN ', @columnname),
    'SELECT 1'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 4) Drop transactions.prepaid_expense_id column if exists
SET @tablename = 'transactions';
SET @columnname = 'prepaid_expense_id';
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND COLUMN_NAME = @columnname
    ) > 0,
    CONCAT('ALTER TABLE ', @tablename, ' DROP COLUMN ', @columnname),
    'SELECT 1'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 5) Remove prepaid settings data
DELETE FROM amortization_settings
WHERE setting_name LIKE 'prepaid\_%';

-- 6) Drop prepaid_expenses table (includes all historical data)
DROP TABLE IF EXISTS prepaid_expenses;
