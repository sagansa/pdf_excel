-- Migration 031: Add rental accounting fields for BRUTO/NETTO and PPh 4(2) timing
SET @dbname = DATABASE();

-- rental_contracts.calculation_method
SET @tablename = 'rental_contracts';
SET @columnname = 'calculation_method';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname
  ) > 0,
  'SELECT 1',
  'ALTER TABLE rental_contracts ADD COLUMN calculation_method VARCHAR(10) DEFAULT ''BRUTO'''
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- rental_contracts.pph42_rate
SET @columnname = 'pph42_rate';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname
  ) > 0,
  'SELECT 1',
  'ALTER TABLE rental_contracts ADD COLUMN pph42_rate DECIMAL(5,2) DEFAULT 10.00'
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- rental_contracts.pph42_payment_timing
SET @columnname = 'pph42_payment_timing';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname
  ) > 0,
  'SELECT 1',
  'ALTER TABLE rental_contracts ADD COLUMN pph42_payment_timing VARCHAR(20) DEFAULT ''same_period'''
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- rental_contracts.pph42_payment_date
SET @columnname = 'pph42_payment_date';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname
  ) > 0,
  'SELECT 1',
  'ALTER TABLE rental_contracts ADD COLUMN pph42_payment_date DATE NULL'
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- prepaid_expenses.amount_tax
SET @tablename = 'prepaid_expenses';
SET @columnname = 'amount_tax';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname
  ) > 0,
  'SELECT 1',
  'ALTER TABLE prepaid_expenses ADD COLUMN amount_tax DECIMAL(15,2) DEFAULT 0.00'
));
PREPARE stmt FROM @preparedStatement; EXECUTE stmt; DEALLOCATE PREPARE stmt;

