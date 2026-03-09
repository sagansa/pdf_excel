-- Persist HPP batch references using stock_monitoring_id.
-- Keep product_id temporarily for backward compatibility and historical reads.

SET @column_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'hpp_batch_products'
      AND COLUMN_NAME = 'stock_monitoring_id'
);

SET @add_column_sql := IF(
    @column_exists = 0,
    'ALTER TABLE hpp_batch_products ADD COLUMN stock_monitoring_id CHAR(36) NULL AFTER product_id',
    'SELECT 1'
);
PREPARE add_column_stmt FROM @add_column_sql;
EXECUTE add_column_stmt;
DEALLOCATE PREPARE add_column_stmt;

UPDATE hpp_batch_products
SET stock_monitoring_id = product_id
WHERE stock_monitoring_id IS NULL
  AND product_id IS NOT NULL;

SET @index_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'hpp_batch_products'
      AND INDEX_NAME = 'idx_hpp_batch_products_stock_monitoring_id'
);

SET @add_index_sql := IF(
    @index_exists = 0,
    'ALTER TABLE hpp_batch_products ADD INDEX idx_hpp_batch_products_stock_monitoring_id (stock_monitoring_id)',
    'SELECT 1'
);
PREPARE add_index_stmt FROM @add_index_sql;
EXECUTE add_index_stmt;
DEALLOCATE PREPARE add_index_stmt;
