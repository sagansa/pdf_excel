-- Migration for Prepaid Expenses (Rent Amortization)
-- Creates table to store prepaid items and seeds default settings

CREATE TABLE IF NOT EXISTS prepaid_expenses (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36) NOT NULL,
    description VARCHAR(255) NOT NULL,
    prepaid_coa_id CHAR(36) NOT NULL, -- Account 1421 by default
    expense_coa_id CHAR(36) NOT NULL, -- Account 5315 by default
    tax_payable_coa_id CHAR(36),      -- Account 2191 by default
    start_date DATE NOT NULL,
    duration_months INT NOT NULL,     -- e.g., 24
    amount_net DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    amount_bruto DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    tax_rate DECIMAL(5, 2) NOT NULL DEFAULT 10.00, -- e.g., 10%
    is_gross_up BOOLEAN DEFAULT FALSE,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (prepaid_coa_id) REFERENCES chart_of_accounts(id),
    FOREIGN KEY (expense_coa_id) REFERENCES chart_of_accounts(id),
    FOREIGN KEY (tax_payable_coa_id) REFERENCES chart_of_accounts(id),
    INDEX idx_company_start (company_id, start_date)
);

-- Seed default settings for Prepaid Expenses if they don't exist
-- We use a subquery to find relevant COA IDs by code to avoid hardcoding UUIDs

-- 1. Default Prepaid Asset COA (1421 - Biaya Dibayar di Muka)
INSERT INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description)
SELECT UUID(), NULL, 'prepaid_prepaid_asset_coa', id, 'text', 'Default COA for Prepaid Assets (1421)'
FROM chart_of_accounts WHERE code = '1421' LIMIT 1
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- 2. Default Rent Expense COA (5315 - Beban Sewa)
INSERT INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description)
SELECT UUID(), NULL, 'prepaid_rent_expense_coa', id, 'text', 'Default COA for Rent Expenses (5315)'
FROM chart_of_accounts WHERE code = '5315' LIMIT 1
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- 3. Default Tax Payable COA (2191 - Utang Pajak)
INSERT INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description)
SELECT UUID(), NULL, 'prepaid_tax_payable_coa', id, 'text', 'Default COA for Tax Payables (2191)'
FROM chart_of_accounts WHERE code = '2191' LIMIT 1
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- 4. Default PPh 4(2) Tax Rate
INSERT INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description)
VALUES (UUID(), NULL, 'prepaid_default_tax_rate', '10', 'number', 'Default PPh 4(2) Tax Rate for Rent')
ON DUPLICATE KEY UPDATE updated_at = NOW();
