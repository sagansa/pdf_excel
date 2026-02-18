-- Migration: Change Amortization System from COA-based to Mark-based
-- This migration adds support for identifying amortizable assets through marks instead of COA codes

-- 1. Add new columns to marks table to support asset identification
ALTER TABLE marks ADD COLUMN is_asset BOOLEAN DEFAULT FALSE;
ALTER TABLE marks ADD COLUMN asset_type TEXT NULL;
ALTER TABLE marks ADD COLUMN useful_life_years INTEGER NULL;
ALTER TABLE marks ADD COLUMN amortization_rate REAL NULL;

-- 2. Add new setting for mark-based amortization configuration
-- SQLite version doesn't support INSERT IGNORE, so we use different approach
INSERT OR IGNORE INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description) VALUES
(LOWER(HEX(RANDOMBLOB(4))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(6))), NULL, 'amortization_asset_marks', '["pembelian aset perusahaan - berwujud", "pembelian aset perusahaan - tidak berwujud", "pembelian bangunan"]', 'json', 'Mark descriptions that identify amortizable assets');

INSERT OR IGNORE INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description) VALUES
(LOWER(HEX(RANDOMBLOB(4))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(6))), NULL, 'use_mark_based_amortization', 'true', 'boolean', 'Enable mark-based amortization detection instead of COA codes');

INSERT OR IGNORE INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description) VALUES
(LOWER(HEX(RANDOMBLOB(4))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(6))), NULL, 'default_asset_useful_life', '5', 'text', 'Default useful life in years for assets when not specified');

INSERT OR IGNORE INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description) VALUES
(LOWER(HEX(RANDOMBLOB(4))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(2))) || '-' || LOWER(HEX(RANDOMBLOB(6))), NULL, 'default_amortization_rate', '20.00', 'text', 'Default amortization rate in percentage when not specified');

-- 3. Create a new table for mark-to-asset-type mappings (alternative to storing in marks table)
CREATE TABLE IF NOT EXISTS mark_asset_mapping (
    id TEXT PRIMARY KEY,
    mark_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    useful_life_years INTEGER NOT NULL DEFAULT 5,
    amortization_rate REAL NOT NULL DEFAULT 20.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mark_id) REFERENCES marks(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_mark_asset_mapping_mark ON mark_asset_mapping(mark_id);
CREATE INDEX IF NOT EXISTS idx_mark_asset_mapping_type ON mark_asset_mapping(asset_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mark_asset_mapping_unique ON mark_asset_mapping(mark_id);

-- 4. Create index for better performance on mark-based queries
CREATE INDEX IF NOT EXISTS idx_transactions_mark_date ON transactions(mark_id, txn_date);

-- Comments:
-- This migration provides two approaches for mark-based amortization:
-- 1. Direct approach: Store asset properties directly in the marks table
-- 2. Mapping approach: Use mark_asset_mapping table for more flexible configuration
-- The system can use either approach based on the 'use_mark_based_amortization' setting
