-- Create amortization_balances table to store manual amortization amounts
CREATE TABLE IF NOT EXISTS amortization_balances (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36) NOT NULL,
    year INT NOT NULL,
    amortization_amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_company_year (company_id, year)
);

-- Create index for faster lookups
CREATE INDEX idx_amortization_company_year ON amortization_balances(company_id, year);

-- Add comments for documentation
-- This table stores manual amortization adjustments per company and year
-- The amount is used in Income Statement calculations alongside transactions
-- categorized to amortization accounts (e.g., 5314)
