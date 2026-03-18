-- Migration 062: Add fiscal_category to chart_of_accounts
SET @dbname = DATABASE();
SET @tablename = 'chart_of_accounts';
SET @columnname = 'fiscal_category';

SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*)
   FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, " VARCHAR(50) DEFAULT 'DEDUCTIBLE' AFTER subcategory")
));

PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Optional: Initial auto-categorization based on keywords
UPDATE chart_of_accounts
SET fiscal_category = 'NON_DEDUCTIBLE_PERMANENT'
WHERE fiscal_category = 'DEDUCTIBLE'
  AND (
    name LIKE '%Sanksi%' OR 
    name LIKE '%Denda%' OR 
    name LIKE '%Pajak Penghasilan%' OR
    name LIKE '%Sumbangan%' OR
    name LIKE '%Donasi%' OR
    name LIKE '%Gratifikasi%'
  );
