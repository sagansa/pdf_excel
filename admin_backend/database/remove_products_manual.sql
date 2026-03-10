-- Manual SQL script to remove products-related tables
-- Run this ONLY if you want to remove products feature from the database
-- IMPORTANT: Backup your database first!

-- Drop only products-related tables (NOT hpp_batch_products)
DROP TABLE IF EXISTS product_request_stock;
DROP TABLE IF EXISTS product_transfer_stock;
DROP TABLE IF EXISTS product_remaining_stock;
DROP TABLE IF EXISTS product_storage_stock;
DROP TABLE IF EXISTS transaction_products;
DROP TABLE IF EXISTS products;

-- Remove product_id column from hpp_batch_products (if exists)
-- ALTER TABLE hpp_batch_products DROP COLUMN product_id;

-- Verify tables are dropped
SHOW TABLES LIKE '%product%';
