-- Migration 025: Rental Location Management System
-- Creates tables for managing rental locations, stores, and contracts

-- 1. Rental Stores Table
CREATE TABLE IF NOT EXISTS rental_stores (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 2. Rental Locations Table
CREATE TABLE IF NOT EXISTS rental_locations (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36) NOT NULL,
    location_name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    province VARCHAR(100),
    postal_code VARCHAR(20),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    area_sqm DECIMAL(10, 2),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Rental Contracts Table
CREATE TABLE IF NOT EXISTS rental_contracts (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36) NOT NULL,
    store_id CHAR(36) NOT NULL,
    location_id CHAR(36) NOT NULL,
    contract_number VARCHAR(100),
    landlord_name VARCHAR(255),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_amount DECIMAL(15, 2),
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (store_id) REFERENCES rental_stores(id),
    FOREIGN KEY (location_id) REFERENCES rental_locations(id) ON DELETE CASCADE,
    INDEX idx_company_contract (company_id, status),
    INDEX idx_contract_dates (start_date, end_date)
);

-- 4. Update transactions table to link to rental contracts (safe add column)
SET @dbname = DATABASE();
SET @tablename = 'transactions';
SET @columnname = 'rental_contract_id';
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
    WHERE CONSTRAINT_NAME = 'fk_transaction_contract' AND TABLE_NAME = 'transactions' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@constraint_check > 0,
    'SELECT 1',
    'ALTER TABLE transactions ADD CONSTRAINT fk_transaction_contract FOREIGN KEY (rental_contract_id) REFERENCES rental_contracts(id) ON DELETE SET NULL'
);
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Add index if it doesn't exist
SET @index_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE INDEX_NAME = 'idx_transactions_contract' AND TABLE_NAME = 'transactions' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@index_check > 0,
    'SELECT 1',
    'CREATE INDEX idx_transactions_contract ON transactions(rental_contract_id)'
);
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 5. Update prepaid_expenses table to link to contracts
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

-- Add foreign key constraint if it doesn't exist
SET @constraint_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE CONSTRAINT_NAME = 'fk_prepaid_contract' AND TABLE_NAME = 'prepaid_expenses' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@constraint_check > 0,
    'SELECT 1',
    'ALTER TABLE prepaid_expenses ADD CONSTRAINT fk_prepaid_contract FOREIGN KEY (contract_id) REFERENCES rental_contracts(id) ON DELETE SET NULL'
);
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Add index if it doesn't exist
SET @index_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE INDEX_NAME = 'idx_prepaid_contract' AND TABLE_NAME = 'prepaid_expenses' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@index_check > 0,
    'SELECT 1',
    'CREATE INDEX idx_prepaid_contract ON prepaid_expenses(contract_id)'
);
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;
