-- Create companies table
CREATE TABLE IF NOT EXISTS companies (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Add company_id to transactions table
ALTER TABLE transactions 
ADD COLUMN company_id CHAR(36) AFTER mark_id;

-- Add index for performance
CREATE INDEX idx_transactions_company_id ON transactions(company_id);

-- Optional: Add foreign key constraint (commented out for flexibility during migration)
-- ALTER TABLE transactions ADD CONSTRAINT fk_transactions_company FOREIGN KEY (company_id) REFERENCES companies(id);
