-- Migration 026: Remove location dependency from rental_stores table
-- This migration removes the current_location_id column and cleans up location references

-- 1. Remove the current_location_id column from rental_stores table
SET @dbname = DATABASE();
SET @tablename = 'rental_stores';
SET @columnname = 'current_location_id';

-- Check if column exists before removing
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE (table_name = @tablename)
   AND (table_schema = @dbname)
   AND (column_name = @columnname)
  ) > 0,
  'ALTER TABLE rental_stores DROP COLUMN current_location_id',
  'SELECT 1'
));

PREPARE alterIfExists FROM @preparedStatement;
EXECUTE alterIfExists;
DEALLOCATE PREPARE alterIfExists;

-- 2. Update rental_contracts table to remove location dependency
-- Convert location_id to a text field for simple location name storage instead of foreign key
SET @columnname = 'location_id';
SET @newcolumnname = 'location_name';

-- Check if location_id column exists
SET @column_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE (table_name = 'rental_contracts')
   AND (table_schema = @dbname)
   AND (column_name = @columnname));

-- Add location_name column if it doesn't exist
SET @add_column = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE (table_name = 'rental_contracts')
   AND (table_schema = @dbname)
   AND (column_name = @newcolumnname)
  ) = 0,
  'ALTER TABLE rental_contracts ADD COLUMN location_name VARCHAR(255)',
  'SELECT 1'
));

PREPARE addColumnIfExists FROM @add_column;
EXECUTE addColumnIfExists;
DEALLOCATE PREPARE addColumnIfExists;

-- If location_id column exists, migrate data to location_name and then drop it
SET @migrate_data = IF(@column_exists > 0, CONCAT(
  'UPDATE rental_contracts rc LEFT JOIN rental_locations rl ON rc.location_id = rl.id ',
  'SET rc.location_name = rl.location_name WHERE rc.location_id IS NOT NULL'
), 'SELECT 1');

PREPARE migrateData FROM @migrate_data;
EXECUTE migrateData;
DEALLOCATE PREPARE migrateData;

-- Drop the foreign key constraint if it exists
SET @constraint_check = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE CONSTRAINT_NAME = 'fk_rental_contracts_location' AND TABLE_NAME = 'rental_contracts' AND TABLE_SCHEMA = DATABASE());
SET @drop_constraint = IF(@constraint_check > 0,
    'ALTER TABLE rental_contracts DROP FOREIGN KEY fk_rental_contracts_location',
    'SELECT 1'
);
PREPARE dropConstraintIfExists FROM @drop_constraint;
EXECUTE dropConstraintIfExists;
DEALLOCATE PREPARE dropConstraintIfExists;

-- Drop the location_id column if it exists
SET @drop_column = IF(@column_exists > 0,
    'ALTER TABLE rental_contracts DROP COLUMN location_id',
    'SELECT 1'
);
PREPARE dropColumnIfExists FROM @drop_column;
EXECUTE dropColumnIfExists;
DEALLOCATE PREPARE dropColumnIfExists;

-- 3. Update rental_locations table - mark as deprecated but don't remove yet
-- This allows for data migration if needed in the future
-- CREATE TABLE rental_locations_deprecated AS SELECT * FROM rental_locations;
