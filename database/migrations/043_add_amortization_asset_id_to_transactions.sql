-- Migration 043: Add amortization_asset_id to transactions table
-- Link transactions explicitly to amortization assets

SET @dbname = DATABASE();
SET @tablename = 'transactions';
SET @columnname = 'amortization_asset_id';

-- Check if column exists before adding
SET @preparedStatement = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE (table_name = @tablename)
   AND (table_schema = @dbname)
   AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE transactions ADD COLUMN amortization_asset_id CHAR(36) NULL AFTER mark_id')
);

PREPARE addColumnIfNeeded FROM @preparedStatement;
EXECUTE addColumnIfNeeded;
DEALLOCATE PREPARE addColumnIfNeeded;

-- Add foreign key constraint
SET @constraint_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE CONSTRAINT_NAME = 'fk_transactions_amortization_asset' AND TABLE_NAME = 'transactions' AND TABLE_SCHEMA = DATABASE());

SET @add_constraint = IF(@constraint_exists > 0,
    'SELECT 1',
    'ALTER TABLE transactions ADD CONSTRAINT fk_transactions_amortization_asset FOREIGN KEY (amortization_asset_id) REFERENCES amortization_assets(id) ON DELETE SET NULL'
);
PREPARE addConstraintIfNeeded FROM @add_constraint;
EXECUTE addConstraintIfNeeded;
DEALLOCATE PREPARE addConstraintIfNeeded;

-- Add index
SET @index_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE INDEX_NAME = 'idx_txns_amortization_asset' AND TABLE_NAME = 'transactions' AND TABLE_SCHEMA = DATABASE());

SET @add_index = IF(@index_exists > 0,
    'SELECT 1',
    'CREATE INDEX idx_txns_amortization_asset ON transactions(amortization_asset_id)'
);
PREPARE addIndexIfNeeded FROM @add_index;
EXECUTE addIndexIfNeeded;
DEALLOCATE PREPARE addIndexIfNeeded;
