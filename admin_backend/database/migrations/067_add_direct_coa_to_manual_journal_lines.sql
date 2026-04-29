-- Migration 067: Store manual journal line COA directly on transactions.
-- This removes the need to create synthetic marks for manual journal child lines.

SET @txn_coa_real_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'coa_id'
);

SET @add_txn_coa_real_sql := IF(
    @txn_coa_real_exists = 0,
    'ALTER TABLE transactions ADD COLUMN coa_id CHAR(36) NULL AFTER mark_id',
    'SELECT 1'
);
PREPARE add_txn_coa_real_stmt FROM @add_txn_coa_real_sql;
EXECUTE add_txn_coa_real_stmt;
DEALLOCATE PREPARE add_txn_coa_real_stmt;

SET @txn_coa_coretax_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND COLUMN_NAME = 'coa_id_coretax'
);

SET @add_txn_coa_coretax_sql := IF(
    @txn_coa_coretax_exists = 0,
    'ALTER TABLE transactions ADD COLUMN coa_id_coretax CHAR(36) NULL AFTER coa_id',
    'SELECT 1'
);
PREPARE add_txn_coa_coretax_stmt FROM @add_txn_coa_coretax_sql;
EXECUTE add_txn_coa_coretax_stmt;
DEALLOCATE PREPARE add_txn_coa_coretax_stmt;

SET @txn_coa_real_index_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND INDEX_NAME = 'idx_transactions_coa_id'
);

SET @add_txn_coa_real_index_sql := IF(
    @txn_coa_real_index_exists = 0,
    'ALTER TABLE transactions ADD INDEX idx_transactions_coa_id (coa_id)',
    'SELECT 1'
);
PREPARE add_txn_coa_real_index_stmt FROM @add_txn_coa_real_index_sql;
EXECUTE add_txn_coa_real_index_stmt;
DEALLOCATE PREPARE add_txn_coa_real_index_stmt;

SET @txn_coa_coretax_index_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'transactions'
      AND INDEX_NAME = 'idx_transactions_coa_id_coretax'
);

SET @add_txn_coa_coretax_index_sql := IF(
    @txn_coa_coretax_index_exists = 0,
    'ALTER TABLE transactions ADD INDEX idx_transactions_coa_id_coretax (coa_id_coretax)',
    'SELECT 1'
);
PREPARE add_txn_coa_coretax_index_stmt FROM @add_txn_coa_coretax_index_sql;
EXECUTE add_txn_coa_coretax_index_stmt;
DEALLOCATE PREPARE add_txn_coa_coretax_index_stmt;

UPDATE transactions t
LEFT JOIN mark_coa_mapping mcm_real
    ON mcm_real.mark_id = t.mark_id
   AND LOWER(COALESCE(NULLIF(TRIM(mcm_real.report_type), ''), 'real')) = 'real'
LEFT JOIN mark_coa_mapping mcm_coretax
    ON mcm_coretax.mark_id = t.mark_id
   AND LOWER(COALESCE(NULLIF(TRIM(mcm_coretax.report_type), ''), 'real')) = 'coretax'
SET
    t.coa_id = COALESCE(t.coa_id, mcm_real.coa_id),
    t.coa_id_coretax = COALESCE(t.coa_id_coretax, mcm_coretax.coa_id)
WHERE t.bank_code = 'MANUAL'
  AND COALESCE(t.parent_id, '') != ''
  AND (t.coa_id IS NULL OR t.coa_id_coretax IS NULL);

UPDATE transactions child
JOIN transactions parent ON parent.id = child.parent_id
JOIN marks m ON m.id = child.mark_id
SET child.mark_id = parent.mark_id
WHERE child.bank_code = 'MANUAL'
  AND COALESCE(child.parent_id, '') != ''
  AND parent.mark_id IS NOT NULL
  AND COALESCE(m.is_system_generated, 0) = 1;

DELETE mcm
FROM mark_coa_mapping mcm
LEFT JOIN transactions t ON t.mark_id = mcm.mark_id
LEFT JOIN marks m ON m.id = mcm.mark_id
WHERE COALESCE(m.is_system_generated, 0) = 1
  AND t.id IS NULL;

DELETE m
FROM marks m
LEFT JOIN transactions t ON t.mark_id = m.id
WHERE COALESCE(m.is_system_generated, 0) = 1
  AND t.id IS NULL;
