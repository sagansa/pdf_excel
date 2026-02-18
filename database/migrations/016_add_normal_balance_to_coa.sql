-- Add normal_balance column to chart_of_accounts if not exists
SET @dbname = DATABASE();
SET @tablename = "chart_of_accounts";
SET @columnname = "normal_balance";
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
   AND table_schema = @dbname
   AND column_name = @columnname
  ) > 0,
  "SELECT 1",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " VARCHAR(10) DEFAULT 'CREDIT'")
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update existing accounts based on category
UPDATE chart_of_accounts SET normal_balance = 'DEBIT' WHERE category IN ('ASSET', 'EXPENSE', 'COGS', 'OTHER_EXPENSE');
UPDATE chart_of_accounts SET normal_balance = 'CREDIT' WHERE category IN ('LIABILITY', 'EQUITY', 'REVENUE', 'OTHER_REVENUE');
UPDATE chart_of_accounts SET normal_balance = 'DEBIT' WHERE code IN ('4011', '4002');
