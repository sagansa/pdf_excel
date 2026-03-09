-- Allow hpp_batch_products.product_id to store stock_monitorings IDs as HPP item references.
-- This drops the old FK to products while keeping the existing column name for backward compatibility.

SET @fk_name := (
    SELECT kcu.CONSTRAINT_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
    WHERE kcu.TABLE_SCHEMA = DATABASE()
      AND kcu.TABLE_NAME = 'hpp_batch_products'
      AND kcu.COLUMN_NAME = 'product_id'
      AND kcu.REFERENCED_TABLE_NAME = 'products'
    LIMIT 1
);

SET @drop_fk_sql := IF(
    @fk_name IS NOT NULL,
    CONCAT('ALTER TABLE hpp_batch_products DROP FOREIGN KEY `', @fk_name, '`'),
    'SELECT 1'
);
PREPARE drop_fk_stmt FROM @drop_fk_sql;
EXECUTE drop_fk_stmt;
DEALLOCATE PREPARE drop_fk_stmt;

