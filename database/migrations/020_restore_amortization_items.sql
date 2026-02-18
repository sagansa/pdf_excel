-- Migration to restore amortization_items table
-- This table was accidentally dropped in migration 018

CREATE TABLE IF NOT EXISTS amortization_items (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36) NOT NULL,
    year INT NOT NULL,
    coa_id CHAR(36) NOT NULL,
    description VARCHAR(255) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    notes TEXT,
    is_manual BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (coa_id) REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
    INDEX idx_company_year (company_id, year),
    INDEX idx_coa (coa_id)
);
