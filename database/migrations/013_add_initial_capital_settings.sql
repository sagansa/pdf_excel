-- Add initial_capital_settings table
-- Stores the initial capital (modal setor di awal) configuration per company
-- Allows setting the starting year when initial capital should be recognized

CREATE TABLE IF NOT EXISTS initial_capital_settings (
    id VARCHAR(36) PRIMARY KEY,
    company_id VARCHAR(36) NOT NULL,
    amount DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    start_year INT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE KEY unique_company (company_id)
);

-- Add index for faster lookups
CREATE INDEX idx_initial_capital_company ON initial_capital_settings(company_id);
