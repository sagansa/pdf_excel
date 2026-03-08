-- Migration 004: Add companies table and link to transactions

-- Create companies table if not exists
CREATE TABLE IF NOT EXISTS companies (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Add company_id to transactions table if not exists
SET @dbname = DATABASE();
SET @tablename = "transactions";
SET @columnname = "company_id";
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE (table_name = @tablename)
   AND (table_schema = @dbname)
   AND (column_name = @columnname)
  ) > 0,
  "SELECT 1",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " CHAR(36) AFTER mark_id")
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index for performance if not exists
SET @index_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE INDEX_NAME = 'idx_transactions_company_id' AND TABLE_NAME = 'transactions' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@index_check > 0,
    'SELECT 1',
    'CREATE INDEX idx_transactions_company_id ON transactions(company_id)'
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add foreign key constraint if it doesn't exist
SET @fk_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE CONSTRAINT_NAME = 'fk_transactions_company' AND TABLE_NAME = 'transactions' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@fk_check > 0,
    'SELECT 1',
    'ALTER TABLE transactions ADD CONSTRAINT fk_transactions_company FOREIGN KEY (company_id) REFERENCES companies(id)'
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
