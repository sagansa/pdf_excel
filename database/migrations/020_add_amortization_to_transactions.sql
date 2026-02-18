-- Migration 020: Add amortization support to transactions table (Idempotent)
SET @dbname = DATABASE();
SET @tablename = "transactions";

-- Add amortization_asset_group_id
SET @columnname = "amortization_asset_group_id";
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename AND table_schema = @dbname AND column_name = @columnname
  ) > 0,
  "SELECT 1",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " CHAR(36) NULL")
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Add is_amortizable
SET @columnname = "is_amortizable";
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename AND table_schema = @dbname AND column_name = @columnname
  ) > 0,
  "SELECT 1",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " BOOLEAN DEFAULT FALSE")
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Add amortization_start_date
SET @columnname = "amortization_start_date";
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename AND table_schema = @dbname AND column_name = @columnname
  ) > 0,
  "SELECT 1",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " DATE NULL")
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Add use_half_rate
SET @columnname = "use_half_rate";
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename AND table_schema = @dbname AND column_name = @columnname
  ) > 0,
  "SELECT 1",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " BOOLEAN DEFAULT FALSE")
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Add amortization_notes
SET @columnname = "amortization_notes";
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename AND table_schema = @dbname AND column_name = @columnname
  ) > 0,
  "SELECT 1",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " TEXT NULL")
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Add foreign key constraint if not exists
SET @constraint_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE CONSTRAINT_NAME = 'fk_transaction_amortization_group' AND TABLE_NAME = 'transactions' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@constraint_check > 0,
    'SELECT 1',
    'ALTER TABLE transactions ADD CONSTRAINT fk_transaction_amortization_group FOREIGN KEY (amortization_asset_group_id) REFERENCES amortization_asset_groups(id) ON DELETE SET NULL'
);
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Indexes
SET @index_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE INDEX_NAME = 'idx_transactions_amortization' AND TABLE_NAME = 'transactions' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@index_check > 0, 'SELECT 1', 'CREATE INDEX idx_transactions_amortization ON transactions(amortization_asset_group_id, is_amortizable)');
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @index_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE INDEX_NAME = 'idx_transactions_company_date' AND TABLE_NAME = 'transactions' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@index_check > 0, 'SELECT 1', 'CREATE INDEX idx_transactions_company_date ON transactions(company_id, txn_date)');
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;
