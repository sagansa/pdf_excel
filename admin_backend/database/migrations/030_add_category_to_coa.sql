-- Migration 030: Ensure category/subcategory columns exist in chart_of_accounts
SET @dbname = DATABASE();
SET @tablename = 'chart_of_accounts';

-- Add category column if not exists
SET @columnname = 'category';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*)
   FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TEXT')
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add subcategory column if not exists
SET @columnname = 'subcategory';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*)
   FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TEXT')
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Populate category from legacy account_type only if column exists
SET @legacy_col = 'account_type';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*)
   FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @legacy_col
  ) > 0,
  'UPDATE chart_of_accounts SET category = account_type WHERE category IS NULL AND account_type IS NOT NULL',
  'SELECT 1'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Populate subcategory from legacy account_subtype only if column exists
SET @legacy_col = 'account_subtype';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*)
   FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @legacy_col
  ) > 0,
  'UPDATE chart_of_accounts SET subcategory = account_subtype WHERE subcategory IS NULL AND account_subtype IS NOT NULL',
  'SELECT 1'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Fallback category defaults from account code prefixes
UPDATE chart_of_accounts
SET category = 'EXPENSE'
WHERE category IS NULL
  AND code LIKE '5%';

UPDATE chart_of_accounts
SET category = 'REVENUE'
WHERE category IS NULL
  AND code LIKE '4%';

UPDATE chart_of_accounts
SET category = 'ASSET'
WHERE category IS NULL
  AND code LIKE '1%';

UPDATE chart_of_accounts
SET category = 'LIABILITY'
WHERE category IS NULL
  AND code LIKE '2%';

UPDATE chart_of_accounts
SET category = 'EQUITY'
WHERE category IS NULL
  AND code LIKE '3%';
