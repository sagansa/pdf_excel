-- Migration for Advanced Amortization System with Asset Groups and Calculation Rules
-- SQLite compatible version

-- Create amortization_asset_groups table
-- Defines asset groups with their tarif and useful life based on CoreTax regulations
CREATE TABLE IF NOT EXISTS amortization_asset_groups (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    group_number INTEGER NOT NULL, -- 1, 2, 3, 4, etc.
    group_name TEXT NOT NULL, -- e.g., "Kelompok 1", "Kelompok 2"
    asset_type TEXT NOT NULL, -- 'Tangible', 'Intangible', 'Building'
    useful_life_years INTEGER NOT NULL, -- e.g., 4, 8, 16, 20
    tarif_rate REAL NOT NULL, -- e.g., 25.00 for 25%
    tarif_half_rate REAL NOT NULL, -- e.g., 12.50 for 12.5%
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create unique index for group
CREATE UNIQUE INDEX IF NOT EXISTS unique_amortization_group ON amortization_asset_groups(company_id, group_number, asset_type);

-- Create amortization_assets table
-- Tracks individual assets and their amortization calculations
CREATE TABLE IF NOT EXISTS amortization_assets (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    asset_group_id TEXT NOT NULL,
    asset_code TEXT, -- Internal asset code
    asset_name TEXT NOT NULL,
    asset_description TEXT,
    acquisition_date DATE NOT NULL,
    acquisition_cost REAL NOT NULL,
    residual_value REAL DEFAULT 0.00,
    use_half_rate BOOLEAN DEFAULT FALSE, -- Use 50% rate (e.g., for partial year)
    calculation_method TEXT DEFAULT 'Straight Line',
    
    -- Calculated fields (updated periodically)
    accumulated_amortization REAL DEFAULT 0.00,
    book_value REAL NOT NULL,
    amortization_start_date DATE,
    amortization_end_date DATE,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_fully_amortized BOOLEAN DEFAULT FALSE,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (asset_group_id) REFERENCES amortization_asset_groups(id) ON DELETE RESTRICT
);

-- Create amortization_calculations table
-- Stores yearly/monthly amortization calculations
CREATE TABLE IF NOT EXISTS amortization_calculations (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER,
    calculated_amount REAL NOT NULL,
    applied_rate REAL NOT NULL, -- The rate used (25%, 12.5%, etc.)
    base_amount REAL NOT NULL, -- Book value at start of period
    notes TEXT,
    is_manual_adjustment BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES amortization_assets(id) ON DELETE CASCADE
);

-- Create unique index for period
CREATE UNIQUE INDEX IF NOT EXISTS unique_amortization_period ON amortization_calculations(asset_id, year, month);

-- Create amortization_settings table for configuration
CREATE TABLE IF NOT EXISTS amortization_settings (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    setting_name TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    setting_type TEXT DEFAULT 'text',
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create unique index for setting
CREATE UNIQUE INDEX IF NOT EXISTS unique_amortization_setting ON amortization_settings(company_id, setting_name);

-- Insert Default Asset Groups (Based on CoreTax Indonesian Tax Regulations)
-- Tangible Assets (Harta Berwujud)
INSERT INTO amortization_asset_groups (id, group_number, group_name, asset_type, useful_life_years, tarif_rate, tarif_half_rate) VALUES
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), 1, 'Kelompok 1 - Harta Berwujud', 'Tangible', 4, 25.00, 12.50),
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), 2, 'Kelompok 2 - Harta Berwujud', 'Tangible', 8, 12.50, 6.25),
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), 3, 'Kelompok 3 - Harta Berwujud', 'Tangible', 16, 6.25, 3.125),
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), 4, 'Kelompok 4 - Harta Berwujud', 'Tangible', 20, 5.00, 2.50);

-- Intangible Assets (Harta Tidak Berwujud)
INSERT INTO amortization_asset_groups (id, group_number, group_name, asset_type, useful_life_years, tarif_rate, tarif_half_rate) VALUES
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), 1, 'Kelompok 1 - Harta Tidak Berwujud', 'Intangible', 4, 25.00, 12.50),
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), 2, 'Kelompok 2 - Harta Tidak Berwujud', 'Intangible', 8, 12.50, 6.25),
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), 3, 'Kelompok 3 - Harta Tidak Berwujud', 'Intangible', 16, 6.25, 3.125),
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), 4, 'Kelompok 4 - Harta Tidak Berwujud', 'Intangible', 20, 5.00, 2.50);

-- Buildings (Bangunan)
INSERT INTO amortization_asset_groups (id, group_number, group_name, asset_type, useful_life_years, tarif_rate, tarif_half_rate) VALUES
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), 1, 'Bangunan Permanen', 'Building', 20, 5.00, 2.50),
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), 2, 'Bangunan Non-Permanen', 'Building', 10, 10.00, 5.00);

-- Insert default settings
INSERT INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description) VALUES
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), NULL, 'amortization_coa_mapping', '{"5314": {"name": "Amortisasi Aktiva Tidak Berwujud", "type": "Intangible"}, "5315": {"name": "Penyusutan Bangunan", "type": "Building"}, "5316": {"name": "Penyusutan Peralatan", "type": "Tangible"}}', 'text', 'Mapping COA codes to asset types for automatic detection'),
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), NULL, 'default_calculation_method', 'Straight Line', 'text', 'Default amortization calculation method'),
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), NULL, 'allow_partial_year', 'true', 'text', 'Allow 50% rate for assets acquired mid-year'),
(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))), NULL, 'auto_calculate_monthly', 'false', 'text', 'Automatically calculate monthly amortization');

-- Comments
-- amortization_asset_groups: Defines asset groups based on tax regulations
--   - Tangible: Harta berwujud (mesin, peralatan, kendaraan)
--   - Intangible: Harta tidak berwujud (hak paten, lisensi, goodwill)
--   - Building: Bangunan (permanen dan non-permanen)
--   
-- Kelompok 1: 4 tahun (25% tarif, 12.5% half)
-- Kelompok 2: 8 tahun (12.5% tarif, 6.25% half)
-- Kelompok 3: 16 tahun (6.25% tarif, 3.125% half)
-- Kelompok 4: 20 tahun (5% tarif, 2.5% half)
-- Bangunan: 20 tahun (5% tarif, 2.5% half)
-- Bangunan Non-Permanen: 10 tahun (10% tarif, 5% half)
