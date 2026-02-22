-- Migration 040: Simplify amortization settings to global-only essentials
-- Keep only settings that are still used by current logic.

-- 1) Ensure essential global settings exist (or are updated from latest available values)

-- default_asset_useful_life
SET @s_name := 'default_asset_useful_life';
SET @s_val := COALESCE(
  (SELECT setting_value
   FROM amortization_settings
   WHERE setting_name = @s_name AND company_id IS NULL
   ORDER BY updated_at DESC, created_at DESC
   LIMIT 1),
  (SELECT setting_value
   FROM amortization_settings
   WHERE setting_name = @s_name
   ORDER BY updated_at DESC, created_at DESC
   LIMIT 1),
  '5'
);
UPDATE amortization_settings
SET setting_value = @s_val, setting_type = 'number', updated_at = CURRENT_TIMESTAMP
WHERE setting_name = @s_name AND company_id IS NULL;
INSERT INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description, created_at, updated_at)
SELECT UUID(), NULL, @s_name, @s_val, 'number', 'Global amortization setting', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (
  SELECT 1 FROM amortization_settings WHERE setting_name = @s_name AND company_id IS NULL
);

-- default_amortization_rate
SET @s_name := 'default_amortization_rate';
SET @s_val := COALESCE(
  (SELECT setting_value
   FROM amortization_settings
   WHERE setting_name = @s_name AND company_id IS NULL
   ORDER BY updated_at DESC, created_at DESC
   LIMIT 1),
  (SELECT setting_value
   FROM amortization_settings
   WHERE setting_name = @s_name
   ORDER BY updated_at DESC, created_at DESC
   LIMIT 1),
  '20.0'
);
UPDATE amortization_settings
SET setting_value = @s_val, setting_type = 'number', updated_at = CURRENT_TIMESTAMP
WHERE setting_name = @s_name AND company_id IS NULL;
INSERT INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description, created_at, updated_at)
SELECT UUID(), NULL, @s_name, @s_val, 'number', 'Global amortization setting', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (
  SELECT 1 FROM amortization_settings WHERE setting_name = @s_name AND company_id IS NULL
);

-- allow_partial_year
SET @s_name := 'allow_partial_year';
SET @s_val := COALESCE(
  (SELECT setting_value
   FROM amortization_settings
   WHERE setting_name = @s_name AND company_id IS NULL
   ORDER BY updated_at DESC, created_at DESC
   LIMIT 1),
  (SELECT setting_value
   FROM amortization_settings
   WHERE setting_name = @s_name
   ORDER BY updated_at DESC, created_at DESC
   LIMIT 1),
  'true'
);
UPDATE amortization_settings
SET setting_value = @s_val, setting_type = 'boolean', updated_at = CURRENT_TIMESTAMP
WHERE setting_name = @s_name AND company_id IS NULL;
INSERT INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description, created_at, updated_at)
SELECT UUID(), NULL, @s_name, @s_val, 'boolean', 'Global amortization setting', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (
  SELECT 1 FROM amortization_settings WHERE setting_name = @s_name AND company_id IS NULL
);

-- accumulated_depreciation_coa_codes
SET @s_name := 'accumulated_depreciation_coa_codes';
SET @s_val := COALESCE(
  (SELECT setting_value
   FROM amortization_settings
   WHERE setting_name = @s_name AND company_id IS NULL
   ORDER BY updated_at DESC, created_at DESC
   LIMIT 1),
  (SELECT setting_value
   FROM amortization_settings
   WHERE setting_name = @s_name
   ORDER BY updated_at DESC, created_at DESC
   LIMIT 1),
  '{"Building":"1524","Tangible":"1530","LandRights":"1534","Intangible":"1601"}'
);
UPDATE amortization_settings
SET setting_value = @s_val, setting_type = 'json', updated_at = CURRENT_TIMESTAMP
WHERE setting_name = @s_name AND company_id IS NULL;
INSERT INTO amortization_settings (id, company_id, setting_name, setting_value, setting_type, description, created_at, updated_at)
SELECT UUID(), NULL, @s_name, @s_val, 'json', 'Global amortization setting', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (
  SELECT 1 FROM amortization_settings WHERE setting_name = @s_name AND company_id IS NULL
);

-- 2) Remove company-specific amortization settings (now global-only)
DELETE FROM amortization_settings
WHERE company_id IS NOT NULL;

-- 3) Remove obsolete global keys not used by current app logic.
DELETE FROM amortization_settings
WHERE company_id IS NULL
  AND setting_name NOT IN (
    'default_asset_useful_life',
    'default_amortization_rate',
    'allow_partial_year',
    'accumulated_depreciation_coa_codes',
    'prepaid_prepaid_asset_coa',
    'prepaid_rent_expense_coa',
    'prepaid_tax_payable_coa',
    'service_tax_payable_coa'
  );

-- 4) Deduplicate global rows by keeping the newest row per setting_name.
DELETE s_old
FROM amortization_settings s_old
JOIN amortization_settings s_new
  ON s_old.setting_name = s_new.setting_name
 AND s_old.company_id IS NULL
 AND s_new.company_id IS NULL
 AND (
      COALESCE(s_old.updated_at, s_old.created_at) < COALESCE(s_new.updated_at, s_new.created_at)
      OR (
        COALESCE(s_old.updated_at, s_old.created_at) = COALESCE(s_new.updated_at, s_new.created_at)
        AND s_old.id < s_new.id
      )
 );
