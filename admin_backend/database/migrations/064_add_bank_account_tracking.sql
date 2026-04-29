-- Migration 064: Track bank account numbers on transactions and define named bank accounts.

SET @txn_account_column_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'bank_account_number'
);

SET @add_txn_account_column_sql := IF(
    @txn_account_column_exists = 0,
    'ALTER TABLE transactions ADD COLUMN bank_account_number VARCHAR(100) NULL AFTER bank_code',
    'SELECT 1'
);
PREPARE add_txn_account_column_stmt FROM @add_txn_account_column_sql;
EXECUTE add_txn_account_column_stmt;
DEALLOCATE PREPARE add_txn_account_column_stmt;

SET @txn_account_index_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND INDEX_NAME = 'idx_transactions_bank_account'
);

SET @add_txn_account_index_sql := IF(
    @txn_account_index_exists = 0,
    'ALTER TABLE transactions ADD INDEX idx_transactions_bank_account (bank_code, bank_account_number)',
    'SELECT 1'
);
PREPARE add_txn_account_index_stmt FROM @add_txn_account_index_sql;
EXECUTE add_txn_account_index_stmt;
DEALLOCATE PREPARE add_txn_account_index_stmt;

CREATE TABLE IF NOT EXISTS bank_account_definitions (
    id CHAR(36) PRIMARY KEY,
    bank_code VARCHAR(50) NOT NULL,
    account_number VARCHAR(100) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_bank_account_definition (bank_code, account_number)
);
