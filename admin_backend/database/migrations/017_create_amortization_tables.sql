-- Drop old amortization_balances table if exists
DROP TABLE IF EXISTS amortization_balances;

-- Create amortization_items table for detailed amortization entries
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
    INDEX idx_company_year (company_id, year),
    INDEX idx_coa (coa_id)
);

-- Create amortization_settings table for default COA codes and configuration
CREATE TABLE IF NOT EXISTS amortization_settings (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36),
    setting_name VARCHAR(100) NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_setting (company_id, setting_name),
    INDEX idx_company (company_id)
);

-- Insert default amortization COA codes (can be customized per company)
-- These are the default CoreTax amortization account codes
INSERT INTO amortization_settings (id, setting_name, setting_value, description) VALUES
(UUID(), 'amortization_coa_codes', '["5314"]', 'Default COA codes for amortization accounts. JSON array of COA codes.'),
(UUID(), 'amortization_default_amount', '0', 'Default amount for new manual amortization entries'),
(UUID(), 'amortization_formula', 'coretax_standard', 'Formula type for amortization calculation: coretax_standard, straight_line, or custom');

-- Add comments for documentation
-- amortization_items: Stores individual amortization entries per company/year
-- Each entry must have a COA, description, and amount
-- is_manual flag distinguishes user-entered from system-generated entries
-- 
-- amortization_settings: Stores configuration for amortization behavior
-- amortization_coa_codes: JSON array of COA codes considered as amortization accounts
-- amortization_default_amount: Default value for new manual entries
-- amortization_formula: Calculation method (coretax_standard, straight_line, etc.)
