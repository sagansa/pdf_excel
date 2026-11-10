-- Migration 076: Kolom clean_description di transactions (Fase 3, PRD AI Fitur 1).
-- Deskripsi asli tidak pernah diubah — hasil enrichment disimpan terpisah
-- supaya audit trail utuh dan enrich bisa dijalankan ulang.

SET @clean_description_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'clean_description'
);
SET @add_clean_description_sql := IF(
    @clean_description_exists = 0,
    'ALTER TABLE transactions ADD COLUMN clean_description VARCHAR(500) NULL',
    'SELECT 1'
);
PREPARE add_clean_description_stmt FROM @add_clean_description_sql;
EXECUTE add_clean_description_stmt;
DEALLOCATE PREPARE add_clean_description_stmt;
