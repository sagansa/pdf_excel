-- Migration 035: Prevent double counting on split transactions
-- If a parent transaction has child splits, parent mark must be NULL.

SET @dbname = DATABASE();
SET @has_parent_col = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = @dbname
    AND TABLE_NAME = 'transactions'
    AND COLUMN_NAME = 'parent_id'
);
SET @has_mark_col = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = @dbname
    AND TABLE_NAME = 'transactions'
    AND COLUMN_NAME = 'mark_id'
);

SET @preparedStatement = (
  SELECT IF(
    @has_parent_col > 0 AND @has_mark_col > 0,
    'UPDATE transactions p
     INNER JOIN (
       SELECT DISTINCT parent_id
       FROM transactions
       WHERE parent_id IS NOT NULL
     ) c ON c.parent_id = p.id
     SET p.mark_id = NULL
     WHERE p.mark_id IS NOT NULL',
    'SELECT 1'
  )
);
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
