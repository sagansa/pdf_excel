-- Migration: Change Amortization System from COA-based to Mark-based
-- This migration adds support for identifying amortizable assets through marks instead of COA codes

-- 1. Add new columns to marks table to support asset identification
ALTER TABLE marks 
ADD COLUMN is_asset BOOLEAN DEFAULT FALSE,
ADD COLUMN asset_type ENUM('Tangible', 'Intangible', 'Building') NULL,
ADD COLUMN useful_life_years INT NULL,
ADD COLUMN amortization_rate DECIMAL(5, 2) NULL;

-- 2. Add new setting for mark-based amortization configuration
INSERT IGNORE INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description) VALUES
(UUID(), NULL, 'amortization_asset_marks', '["pembelian aset perusahaan - berwujud", "pembelian aset perusahaan - tidak berwujud", "pembelian bangunan"]', 'json', 'Mark descriptions that identify amortizable assets'),
(UUID(), NULL, 'use_mark_based_amortization', 'true', 'boolean', 'Enable mark-based amortization detection instead of COA codes'),
(UUID(), NULL, 'default_asset_useful_life', '5', 'number', 'Default useful life in years for assets when not specified'),
(UUID(), NULL, 'default_amortization_rate', '20.00', 'number', 'Default amortization rate in percentage when not specified');

-- 3. Create a new table for mark-to-asset-type mappings (alternative to storing in marks table)
CREATE TABLE IF NOT EXISTS mark_asset_mapping (
    id CHAR(36) PRIMARY KEY,
    mark_id CHAR(36) NOT NULL,
    asset_type ENUM('Tangible', 'Intangible', 'Building') NOT NULL,
    useful_life_years INT NOT NULL DEFAULT 5,
    amortization_rate DECIMAL(5, 2) NOT NULL DEFAULT 20.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (mark_id) REFERENCES marks(id) ON DELETE CASCADE,
    INDEX idx_mark (mark_id),
    INDEX idx_asset_type (asset_type),
    UNIQUE KEY unique_mark_asset (mark_id)
);

-- 4. Create index for better performance on mark-based queries
CREATE INDEX idx_transactions_mark_date ON transactions(mark_id, txn_date);

-- Comments:
-- This migration provides two approaches for mark-based amortization:
-- 1. Direct approach: Store asset properties directly in the marks table
-- 2. Mapping approach: Use mark_asset_mapping table for more flexible configuration
-- The system can use either approach based on the 'use_mark_based_amortization' setting
