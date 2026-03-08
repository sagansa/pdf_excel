-- Migration 039: Add payroll period month override to transactions
-- Default behavior remains based on txn_date month when value is NULL.

SET @dbname = DATABASE();
SET @tablename = 'transactions';
SET @columnname = 'payroll_period_month';

SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND COLUMN_NAME = @columnname
    ) > 0,
    'SELECT 1',
    CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DATE NULL')
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @indexname = 'idx_transactions_payroll_period_month';
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND INDEX_NAME = @indexname
    ) > 0,
    'SELECT 1',
    'CREATE INDEX idx_transactions_payroll_period_month ON transactions(payroll_period_month)'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
