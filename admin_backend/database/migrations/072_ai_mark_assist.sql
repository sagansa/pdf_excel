-- Migration 072: AI mark assist.
-- 1) Kolom audit saran mark (LLM lokal) di transactions — saran TIDAK mengisi mark_id
--    langsung: mark_id baru terisi setelah user menerima saran (ai_status accepted).
-- 2) Tabel app_settings untuk konfigurasi aplikasi (provider AI lokal, base URL, model).

SET @ai_suggested_mark_id_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'ai_suggested_mark_id'
);
SET @add_ai_suggested_mark_id_sql := IF(
    @ai_suggested_mark_id_exists = 0,
    'ALTER TABLE transactions ADD COLUMN ai_suggested_mark_id CHAR(36) NULL',
    'SELECT 1'
);
PREPARE add_ai_suggested_mark_id_stmt FROM @add_ai_suggested_mark_id_sql;
EXECUTE add_ai_suggested_mark_id_stmt;
DEALLOCATE PREPARE add_ai_suggested_mark_id_stmt;

SET @ai_confidence_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'ai_confidence'
);
SET @add_ai_confidence_sql := IF(
    @ai_confidence_exists = 0,
    'ALTER TABLE transactions ADD COLUMN ai_confidence DECIMAL(4,3) NULL',
    'SELECT 1'
);
PREPARE add_ai_confidence_stmt FROM @add_ai_confidence_sql;
EXECUTE add_ai_confidence_stmt;
DEALLOCATE PREPARE add_ai_confidence_stmt;

SET @ai_source_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'ai_source'
);
SET @add_ai_source_sql := IF(
    @ai_source_exists = 0,
    'ALTER TABLE transactions ADD COLUMN ai_source VARCHAR(20) NULL',
    'SELECT 1'
);
PREPARE add_ai_source_stmt FROM @add_ai_source_sql;
EXECUTE add_ai_source_stmt;
DEALLOCATE PREPARE add_ai_source_stmt;

SET @ai_reason_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'ai_reason'
);
SET @add_ai_reason_sql := IF(
    @ai_reason_exists = 0,
    'ALTER TABLE transactions ADD COLUMN ai_reason TEXT NULL',
    'SELECT 1'
);
PREPARE add_ai_reason_stmt FROM @add_ai_reason_sql;
EXECUTE add_ai_reason_stmt;
DEALLOCATE PREPARE add_ai_reason_stmt;

SET @ai_status_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'ai_status'
);
SET @add_ai_status_sql := IF(
    @ai_status_exists = 0,
    'ALTER TABLE transactions ADD COLUMN ai_status VARCHAR(20) NULL',
    'SELECT 1'
);
PREPARE add_ai_status_stmt FROM @add_ai_status_sql;
EXECUTE add_ai_status_stmt;
DEALLOCATE PREPARE add_ai_status_stmt;

SET @ai_suggested_at_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'ai_suggested_at'
);
SET @add_ai_suggested_at_sql := IF(
    @ai_suggested_at_exists = 0,
    'ALTER TABLE transactions ADD COLUMN ai_suggested_at DATETIME NULL',
    'SELECT 1'
);
PREPARE add_ai_suggested_at_stmt FROM @add_ai_suggested_at_sql;
EXECUTE add_ai_suggested_at_stmt;
DEALLOCATE PREPARE add_ai_suggested_at_stmt;

SET @ai_decided_at_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'ai_decided_at'
);
SET @add_ai_decided_at_sql := IF(
    @ai_decided_at_exists = 0,
    'ALTER TABLE transactions ADD COLUMN ai_decided_at DATETIME NULL',
    'SELECT 1'
);
PREPARE add_ai_decided_at_stmt FROM @add_ai_decided_at_sql;
EXECUTE add_ai_decided_at_stmt;
DEALLOCATE PREPARE add_ai_decided_at_stmt;

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key VARCHAR(64) PRIMARY KEY,
    setting_value TEXT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
