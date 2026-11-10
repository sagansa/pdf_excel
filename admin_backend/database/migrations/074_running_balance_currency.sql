-- Migration 074: Simpan saldo berjalan (hasil parse statement) di transactions.
-- Kolom balance sudah lama diparse semua parser tapi dibuang saat insert;
-- mulai sekarang dipertahankan untuk laporan cek kontinuitas saldo antar
-- statement. Data lama tetap NULL — checker menanganinya secara jujur.

SET @running_balance_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'running_balance'
);
SET @add_running_balance_sql := IF(
    @running_balance_exists = 0,
    'ALTER TABLE transactions ADD COLUMN running_balance DECIMAL(18,2) NULL',
    'SELECT 1'
);
PREPARE add_running_balance_stmt FROM @add_running_balance_sql;
EXECUTE add_running_balance_stmt;
DEALLOCATE PREPARE add_running_balance_stmt;

SET @currency_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'currency'
);
SET @add_currency_sql := IF(
    @currency_exists = 0,
    'ALTER TABLE transactions ADD COLUMN currency VARCHAR(8) NULL',
    'SELECT 1'
);
PREPARE add_currency_stmt FROM @add_currency_sql;
EXECUTE add_currency_stmt;
DEALLOCATE PREPARE add_currency_stmt;
