-- Migration 065: Add active period to bank account definitions.

SET @active_from_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'bank_account_definitions'
      AND COLUMN_NAME = 'active_from'
);

SET @add_active_from_sql := IF(
    @active_from_exists = 0,
    'ALTER TABLE bank_account_definitions ADD COLUMN active_from DATE NULL AFTER display_name',
    'SELECT 1'
);
PREPARE add_active_from_stmt FROM @add_active_from_sql;
EXECUTE add_active_from_stmt;
DEALLOCATE PREPARE add_active_from_stmt;

SET @active_until_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'bank_account_definitions'
      AND COLUMN_NAME = 'active_until'
);

SET @add_active_until_sql := IF(
    @active_until_exists = 0,
    'ALTER TABLE bank_account_definitions ADD COLUMN active_until DATE NULL AFTER active_from',
    'SELECT 1'
);
PREPARE add_active_until_stmt FROM @add_active_until_sql;
EXECUTE add_active_until_stmt;
DEALLOCATE PREPARE add_active_until_stmt;

SET @active_from_index_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'bank_account_definitions'
      AND INDEX_NAME = 'idx_bank_account_definition_active_from'
);

SET @add_active_from_index_sql := IF(
    @active_from_index_exists = 0,
    'ALTER TABLE bank_account_definitions ADD INDEX idx_bank_account_definition_active_from (active_from)',
    'SELECT 1'
);
PREPARE add_active_from_index_stmt FROM @add_active_from_index_sql;
EXECUTE add_active_from_index_stmt;
DEALLOCATE PREPARE add_active_from_index_stmt;

SET @active_until_index_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'bank_account_definitions'
      AND INDEX_NAME = 'idx_bank_account_definition_active_until'
);

SET @add_active_until_index_sql := IF(
    @active_until_index_exists = 0,
    'ALTER TABLE bank_account_definitions ADD INDEX idx_bank_account_definition_active_until (active_until)',
    'SELECT 1'
);
PREPARE add_active_until_index_stmt FROM @add_active_until_index_sql;
EXECUTE add_active_until_index_stmt;
DEALLOCATE PREPARE add_active_until_index_stmt;
