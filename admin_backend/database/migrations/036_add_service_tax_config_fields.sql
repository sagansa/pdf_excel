-- Migration 036: Add service tax configuration fields per transaction
-- Adds:
-- 1) transactions.service_calculation_method (BRUTO/NETTO)
-- 2) transactions.service_tax_payment_timing (same_period/next_period/next_year)
-- 3) transactions.service_tax_payment_date (DATE)

SET @dbname = DATABASE();
SET @tablename = 'transactions';

-- 1) service_calculation_method
SET @columnname = 'service_calculation_method';
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND COLUMN_NAME = @columnname
    ) > 0,
    'SELECT 1',
    CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(10) DEFAULT ''BRUTO''')
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2) service_tax_payment_timing
SET @columnname = 'service_tax_payment_timing';
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND COLUMN_NAME = @columnname
    ) > 0,
    'SELECT 1',
    CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(20) DEFAULT ''same_period''')
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3) service_tax_payment_date
SET @columnname = 'service_tax_payment_date';
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND COLUMN_NAME = @columnname
    ) > 0,
    'SELECT 1',
    CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DATE NULL')
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Normalize existing rows for deterministic default values
SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND COLUMN_NAME = 'service_calculation_method'
    ) > 0,
    CONCAT('UPDATE ', @tablename, ' SET service_calculation_method = ''BRUTO'' WHERE service_calculation_method IS NULL OR service_calculation_method = '''''),
    'SELECT 1'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @preparedStatement = (
  SELECT IF(
    (SELECT COUNT(*)
     FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = @dbname
       AND TABLE_NAME = @tablename
       AND COLUMN_NAME = 'service_tax_payment_timing'
    ) > 0,
    CONCAT('UPDATE ', @tablename, ' SET service_tax_payment_timing = ''same_period'' WHERE service_tax_payment_timing IS NULL OR service_tax_payment_timing = '''''),
    'SELECT 1'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
