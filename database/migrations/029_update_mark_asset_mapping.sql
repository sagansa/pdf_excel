-- Migration: Update mark_asset_mapping to link to amortization_asset_groups
-- This ensures mark-based assets can be linked to specific asset groups

-- Add asset_group_id column to mark_asset_mapping if not exists
SET @dbname = DATABASE();
SET @tablename = "mark_asset_mapping";

SET @columnname = "asset_group_id";
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_NAME = @tablename AND TABLE_SCHEMA = @dbname AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " CHAR(36) AFTER asset_type")
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Add is_deductible_50_percent column to mark_asset_mapping if not exists
SET @columnname = "is_deductible_50_percent";
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_NAME = @tablename AND TABLE_SCHEMA = @dbname AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " BOOLEAN DEFAULT FALSE AFTER amortization_rate")
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Add foreign key constraint if not exists
SET @constraint_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE CONSTRAINT_NAME = 'fk_mark_asset_mapping_group' AND TABLE_NAME = 'mark_asset_mapping' AND TABLE_SCHEMA = DATABASE());
SET @preparedStatement = IF(@constraint_check > 0,
    'SELECT 1',
    'ALTER TABLE mark_asset_mapping ADD CONSTRAINT fk_mark_asset_mapping_group FOREIGN KEY (asset_group_id) REFERENCES amortization_asset_groups(id) ON DELETE SET NULL'
);
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;
