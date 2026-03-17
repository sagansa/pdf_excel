-- Migration 060: Add report_type to initial_capital_settings
-- Allows distinct initial capital settings for 'real' vs 'coretax'

-- 1. Add report_type column
ALTER TABLE initial_capital_settings 
ADD COLUMN report_type ENUM('real', 'coretax') NOT NULL DEFAULT 'real';

-- 2. Drop the old unique key on company_id
ALTER TABLE initial_capital_settings 
DROP INDEX unique_company;

-- 3. Add new unique key on (company_id, report_type)
ALTER TABLE initial_capital_settings 
ADD UNIQUE KEY unique_company_report_type (company_id, report_type);

-- Existing data defaults to 'real' due to the column definition DEFAULT 'real'.
