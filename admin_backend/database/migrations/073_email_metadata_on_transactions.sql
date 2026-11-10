-- Migration 073: Metadata email sumber e-statement pada transactions.
-- Dipakai endpoint integrasi n8n: email_message_id menjadi lapis idempotensi
-- pertama (sebelum file_hash) supaya bank yang me-regenerate PDF dengan byte
-- berbeda untuk email yang sama tidak ter-import dua kali.

SET @email_from_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'email_from'
);
SET @add_email_from_sql := IF(
    @email_from_exists = 0,
    'ALTER TABLE transactions ADD COLUMN email_from VARCHAR(300) NULL',
    'SELECT 1'
);
PREPARE add_email_from_stmt FROM @add_email_from_sql;
EXECUTE add_email_from_stmt;
DEALLOCATE PREPARE add_email_from_stmt;

SET @email_subject_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'email_subject'
);
SET @add_email_subject_sql := IF(
    @email_subject_exists = 0,
    'ALTER TABLE transactions ADD COLUMN email_subject VARCHAR(300) NULL',
    'SELECT 1'
);
PREPARE add_email_subject_stmt FROM @add_email_subject_sql;
EXECUTE add_email_subject_stmt;
DEALLOCATE PREPARE add_email_subject_stmt;

SET @email_date_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'email_date'
);
SET @add_email_date_sql := IF(
    @email_date_exists = 0,
    'ALTER TABLE transactions ADD COLUMN email_date VARCHAR(60) NULL',
    'SELECT 1'
);
PREPARE add_email_date_stmt FROM @add_email_date_sql;
EXECUTE add_email_date_stmt;
DEALLOCATE PREPARE add_email_date_stmt;

SET @email_message_id_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'email_message_id'
);
SET @add_email_message_id_sql := IF(
    @email_message_id_exists = 0,
    'ALTER TABLE transactions ADD COLUMN email_message_id VARCHAR(300) NULL',
    'SELECT 1'
);
PREPARE add_email_message_id_stmt FROM @add_email_message_id_sql;
EXECUTE add_email_message_id_stmt;
DEALLOCATE PREPARE add_email_message_id_stmt;

SET @email_message_id_index_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND INDEX_NAME = 'idx_transactions_email_message_id'
);
SET @add_email_message_id_index_sql := IF(
    @email_message_id_index_exists = 0,
    'CREATE INDEX idx_transactions_email_message_id ON transactions (email_message_id)',
    'SELECT 1'
);
PREPARE add_email_message_id_index_stmt FROM @add_email_message_id_index_sql;
EXECUTE add_email_message_id_index_stmt;
DEALLOCATE PREPARE add_email_message_id_index_stmt;
