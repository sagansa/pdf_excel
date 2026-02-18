-- Migration for Advanced Amortization System with Asset Groups and Calculation Rules
SET FOREIGN_KEY_CHECKS = 0;
-- Drop old tables if exist
DROP TABLE IF EXISTS amortization_items;
DROP TABLE IF EXISTS amortization_assets;
DROP TABLE IF EXISTS amortization_asset_groups;
DROP TABLE IF EXISTS amortization_settings;
DROP TABLE IF EXISTS amortization_calculations;
SET FOREIGN_KEY_CHECKS = 1;

-- Create amortization_asset_groups table
-- Defines asset groups with their tarif and useful life based on CoreTax regulations
CREATE TABLE IF NOT EXISTS amortization_asset_groups (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36),
    group_number INT NOT NULL, -- 1, 2, 3, 4, etc.
    group_name VARCHAR(100) NOT NULL, -- e.g., "Kelompok 1", "Kelompok 2"
    asset_type ENUM('Tangible', 'Intangible', 'Building') NOT NULL,
    useful_life_years INT NOT NULL, -- e.g., 4, 8, 16, 20
    tarif_rate DECIMAL(5, 2) NOT NULL, -- e.g., 25.00 for 25%
    tarif_half_rate DECIMAL(5, 2) NOT NULL, -- e.g., 12.50 for 12.5%
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_group (company_id, group_number, asset_type),
    INDEX idx_company_type (company_id, asset_type)
);

-- Create amortization_assets table
-- Tracks individual assets and their amortization calculations
CREATE TABLE IF NOT EXISTS amortization_assets (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36) NOT NULL,
    asset_group_id CHAR(36) NOT NULL,
    asset_code VARCHAR(50), -- Internal asset code
    asset_name VARCHAR(255) NOT NULL,
    asset_description TEXT,
    acquisition_date DATE NOT NULL,
    acquisition_cost DECIMAL(15, 2) NOT NULL,
    residual_value DECIMAL(15, 2) DEFAULT 0.00,
    use_half_rate BOOLEAN DEFAULT FALSE, -- Use 50% rate (e.g., for partial year)
    calculation_method ENUM('Straight Line', 'Declining Balance') DEFAULT 'Straight Line',
    
    -- Calculated fields (updated periodically)
    accumulated_amortization DECIMAL(15, 2) DEFAULT 0.00,
    book_value DECIMAL(15, 2) NOT NULL,
    amortization_start_date DATE,
    amortization_end_date DATE,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_fully_amortized BOOLEAN DEFAULT FALSE,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (asset_group_id) REFERENCES amortization_asset_groups(id) ON DELETE RESTRICT,
    INDEX idx_company_active (company_id, is_active),
    INDEX idx_acquisition_date (acquisition_date)
);

-- Create amortization_calculations table
-- Stores yearly/monthly amortization calculations
CREATE TABLE IF NOT EXISTS amortization_calculations (
    id CHAR(36) PRIMARY KEY,
    asset_id CHAR(36) NOT NULL,
    year INT NOT NULL,
    month INT,
    calculated_amount DECIMAL(15, 2) NOT NULL,
    applied_rate DECIMAL(5, 2) NOT NULL, -- The rate used (25%, 12.5%, etc.)
    base_amount DECIMAL(15, 2) NOT NULL, -- Book value at start of period
    notes TEXT,
    is_manual_adjustment BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES amortization_assets(id) ON DELETE CASCADE,
    UNIQUE KEY unique_period (asset_id, year, month),
    INDEX idx_year (year)
);

-- Create amortization_settings table for configuration
CREATE TABLE IF NOT EXISTS amortization_settings (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36),
    setting_name VARCHAR(100) NOT NULL,
    setting_value TEXT NOT NULL,
    setting_type ENUM('json', 'text', 'number', 'boolean') DEFAULT 'text',
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_setting (company_id, setting_name),
    INDEX idx_company (company_id)
);

-- Insert Default Asset Groups (Based on CoreTax Indonesian Tax Regulations)
-- Tangible Assets (Harta Berwujud)
INSERT IGNORE INTO amortization_asset_groups (id, group_number, group_name, asset_type, useful_life_years, tarif_rate, tarif_half_rate) VALUES
(UUID(), 1, 'Kelompok 1 - Harta Berwujud', 'Tangible', 4, 25.00, 12.50),
(UUID(), 2, 'Kelompok 2 - Harta Berwujud', 'Tangible', 8, 12.50, 6.25),
(UUID(), 3, 'Kelompok 3 - Harta Berwujud', 'Tangible', 16, 6.25, 3.125),
(UUID(), 4, 'Kelompok 4 - Harta Berwujud', 'Tangible', 20, 5.00, 2.50);

-- Intangible Assets (Harta Tidak Berwujud)
INSERT IGNORE INTO amortization_asset_groups (id, group_number, group_name, asset_type, useful_life_years, tarif_rate, tarif_half_rate) VALUES
(UUID(), 1, 'Kelompok 1 - Harta Tidak Berwujud', 'Intangible', 4, 25.00, 12.50),
(UUID(), 2, 'Kelompok 2 - Harta Tidak Berwujud', 'Intangible', 8, 12.50, 6.25),
(UUID(), 3, 'Kelompok 3 - Harta Tidak Berwujud', 'Intangible', 16, 6.25, 3.125),
(UUID(), 4, 'Kelompok 4 - Harta Tidak Berwujud', 'Intangible', 20, 5.00, 2.50);

-- Buildings (Bangunan)
INSERT IGNORE INTO amortization_asset_groups (id, group_number, group_name, asset_type, useful_life_years, tarif_rate, tarif_half_rate) VALUES
(UUID(), 1, 'Bangunan Permanen', 'Building', 20, 5.00, 2.50),
(UUID(), 2, 'Bangunan Non-Permanen', 'Building', 10, 10.00, 5.00);

-- Insert default settings
INSERT IGNORE INTO amortization_settings (id, setting_name, setting_value, setting_type, description) VALUES
(UUID(), 'amortization_coa_mapping', '{"5314": {"name": "Amortisasi Aktiva Tidak Berwujud", "type": "Intangible"}, "5315": {"name": "Penyusutan Bangunan", "type": "Building"}, "5316": {"name": "Penyusutan Peralatan", "type": "Tangible"}}', 'json', 'Mapping COA codes to asset types for automatic detection'),
(UUID(), 'default_calculation_method', 'Straight Line', 'text', 'Default amortization calculation method'),
(UUID(), 'allow_partial_year', 'true', 'boolean', 'Allow 50% rate for assets acquired mid-year'),
(UUID(), 'auto_calculate_monthly', 'false', 'boolean', 'Automatically calculate monthly amortization');

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
