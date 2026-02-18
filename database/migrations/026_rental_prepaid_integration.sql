-- Migration 026: Rental Contracts - Prepaid Rent Integration
-- Adds bidirectional foreign keys and enhances prepaid expenses to auto-link with rental contracts

SET @dbname = DATABASE();

-- 1. Add prepaid_expense_id to rental_contracts table (bidirectional link)
SET @tablename = 'rental_contracts';
SET @columnname = 'prepaid_expense_id';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE (table_name = @tablename)
   AND (table_schema = @dbname)
   AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' CHAR(36)')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Add foreign key constraint if it doesn't exist
SET @constraint_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE CONSTRAINT_NAME = 'fk_rental_prepaid_expense' AND TABLE_NAME = 'rental_contracts' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@constraint_check > 0,
    'SELECT 1',
    'ALTER TABLE rental_contracts ADD CONSTRAINT fk_rental_prepaid_expense FOREIGN KEY (prepaid_expense_id) REFERENCES prepaid_expenses(id) ON DELETE SET NULL'
);
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Add index if it doesn't exist
SET @index_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE INDEX_NAME = 'idx_rental_prepaid' AND TABLE_NAME = 'rental_contracts' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@index_check > 0,
    'SELECT 1',
    'CREATE INDEX idx_rental_prepaid ON rental_contracts(prepaid_expense_id)'
);
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 2. Ensure contract_id exists in prepaid_expenses (should already exist from migration 025)
SET @tablename = 'prepaid_expenses';
SET @columnname = 'contract_id';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE (table_name = @tablename)
   AND (table_schema = @dbname)
   AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' CHAR(36)')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 3. Add indexes for better query performance on prepaid_expenses
SET @index_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE INDEX_NAME = 'idx_prepaid_contract' AND TABLE_NAME = 'prepaid_expenses' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@index_check > 0,
    'SELECT 1',
    'CREATE INDEX idx_prepaid_contract ON prepaid_expenses(contract_id)'
);
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 4. Add index for company_id in prepaid_expenses for faster lookups
SET @index_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE INDEX_NAME = 'idx_prepaid_company_contract' AND TABLE_NAME = 'prepaid_expenses' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@index_check > 0,
    'SELECT 1',
    'CREATE INDEX idx_prepaid_company_contract ON prepaid_expenses(company_id, contract_id)'
);
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

