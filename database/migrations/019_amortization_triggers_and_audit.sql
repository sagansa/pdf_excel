-- Migration to add amortization settings view tracking
-- This tracks which settings views have been configured by user

CREATE TABLE IF NOT EXISTS amortization_config_history (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36) NOT NULL,
    config_type VARCHAR(50) NOT NULL, -- 'asset_groups', 'coa_mapping', 'calculation_method'
    action VARCHAR(50) NOT NULL, -- 'created', 'updated', 'deleted'
    config_value JSON NOT NULL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_company_type (company_id, config_type),
    INDEX idx_performed_at (created_at)
);

-- Insert default asset types reference
CREATE TABLE IF NOT EXISTS amortization_asset_types (
    id INT PRIMARY KEY AUTO_INCREMENT,
    type_code VARCHAR(20) NOT NULL UNIQUE,
    type_name VARCHAR(50) NOT NULL,
    type_name_en VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO amortization_asset_types (type_code, type_name, type_name_en, description) VALUES
('Tangible', 'Harta Berwujud', 'Tangible Assets', 'Aset fisik seperti mesin, peralatan, kendaraan, dan furniture'),
('Intangible', 'Harta Tidak Berwujud', 'Intangible Assets', 'Aset non-fisik seperti hak paten, lisensi, goodwill, dan software'),
('Building', 'Bangunan', 'Buildings', 'Bangunan permanen dan non-permanen');

-- Add trigger to automatically calculate amortization_end_date
DELIMITER //

CREATE TRIGGER IF NOT EXISTS trg_calc_amortization_dates
BEFORE INSERT ON amortization_assets
FOR EACH ROW
BEGIN
    DECLARE v_useful_life INT;
    DECLARE v_start_date DATE;
    
    -- Get useful life from asset group
    SELECT useful_life_years INTO v_useful_life
    FROM amortization_asset_groups
    WHERE id = NEW.asset_group_id;
    
    -- Set dates
    SET v_start_date = COALESCE(NEW.amortization_start_date, NEW.acquisition_date);
    SET NEW.amortization_start_date = v_start_date;
    SET NEW.amortization_end_date = DATE_ADD(v_start_date, INTERVAL v_useful_life YEAR);
    SET NEW.book_value = NEW.acquisition_cost - NEW.residual_value;
END//

CREATE TRIGGER IF NOT EXISTS trg_calc_amortization_dates_update
BEFORE UPDATE ON amortization_assets
FOR EACH ROW
BEGIN
    DECLARE v_useful_life INT;
    
    -- Only recalculate if acquisition_date or asset_group_id changed
    IF NEW.acquisition_date != OLD.acquisition_date OR NEW.asset_group_id != OLD.asset_group_id THEN
        SELECT useful_life_years INTO v_useful_life
        FROM amortization_asset_groups
        WHERE id = NEW.asset_group_id;
        
        SET NEW.amortization_end_date = DATE_ADD(NEW.acquisition_date, INTERVAL v_useful_life YEAR);
    END IF;
    
    -- Update book value if cost or residual changed
    IF NEW.acquisition_cost != OLD.acquisition_cost OR NEW.residual_value != OLD.residual_value THEN
        SET NEW.book_value = NEW.acquisition_cost - NEW.residual_value;
    END IF;
END//

DELIMITER ;

-- Comments
-- This migration adds:
-- 1. Audit trail for configuration changes
-- 2. Reference table for asset types
-- 3. Triggers to auto-calculate amortization dates
