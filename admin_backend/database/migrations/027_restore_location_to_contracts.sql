-- Migration 027: Restore location_id to rental_contracts table
-- This migration restores the location relationship between contracts and locations

-- 1. Re-add location_id column to rental_contracts table
SET @dbname = DATABASE();
SET @tablename = 'rental_contracts';
SET @columnname = 'location_id';

-- Check if column exists before adding
SET @preparedStatement = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE (table_name = @tablename)
   AND (table_schema = @dbname)
   AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE rental_contracts ADD COLUMN location_id CHAR(36)')
);

PREPARE addColumnIfNeeded FROM @preparedStatement;
EXECUTE addColumnIfNeeded;
DEALLOCATE PREPARE addColumnIfNeeded;

-- 2. Add foreign key constraint for location_id
SET @constraint_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE CONSTRAINT_NAME = 'fk_rental_contracts_location' AND TABLE_NAME = 'rental_contracts' AND TABLE_SCHEMA = DATABASE());

SET @add_constraint = IF(@constraint_exists > 0,
    'SELECT 1',
    'ALTER TABLE rental_contracts ADD CONSTRAINT fk_rental_contracts_location FOREIGN KEY (location_id) REFERENCES rental_locations(id) ON DELETE SET NULL'
);
PREPARE addConstraintIfNeeded FROM @add_constraint;
EXECUTE addConstraintIfNeeded;
DEALLOCATE PREPARE addConstraintIfNeeded;

-- 3. Add index for location_id if it doesn't exist
SET @index_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE INDEX_NAME = 'idx_rental_contracts_location' AND TABLE_NAME = 'rental_contracts' AND TABLE_SCHEMA = DATABASE());

SET @add_index = IF(@index_exists > 0,
    'SELECT 1',
    'CREATE INDEX idx_rental_contracts_location ON rental_contracts(location_id)'
);
PREPARE addIndexIfNeeded FROM @add_index;
EXECUTE addIndexIfNeeded;
DEALLOCATE PREPARE addIndexIfNeeded;

-- 4. Migrate data back from location_name to location_id if needed
-- Only migrate if location_name column exists and has data
SET @has_location_name = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE table_name = 'rental_contracts' AND table_schema = DATABASE() AND column_name = 'location_name');

SET @migrate_back = IF(@has_location_name > 0,
    CONCAT(
        'UPDATE rental_contracts rc ',
        'LEFT JOIN rental_locations rl ON rc.location_name = rl.location_name ',
        'SET rc.location_id = rl.id ',
        'WHERE rc.location_id IS NULL AND rc.location_name IS NOT NULL AND rl.id IS NOT NULL'
    ),
    'SELECT 1'
);

PREPARE migrateBackData FROM @migrate_back;
EXECUTE migrateBackData;
DEALLOCATE PREPARE migrateBackData;

-- 5. Remove location_name column if it exists
SET @columnname = 'location_name';
SET @drop_column = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE (table_name = @tablename)
   AND (table_schema = @dbname)
   AND (column_name = @columnname)
  ) > 0,
  'ALTER TABLE rental_contracts DROP COLUMN location_name',
  'SELECT 1'
);

PREPARE dropColumnIfExists FROM @drop_column;
EXECUTE dropColumnIfExists;
DEALLOCATE PREPARE dropColumnIfExists;

-- 6. Restore current_location_id to rental_stores if needed
SET @tablename = 'rental_stores';
SET @columnname = 'current_location_id';

-- Check if column exists before adding
SET @preparedStatement = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE (table_name = @tablename)
   AND (table_schema = @dbname)
   AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE rental_stores ADD COLUMN current_location_id CHAR(36)')
);

PREPARE addStoreColumnIfNeeded FROM @preparedStatement;
EXECUTE addStoreColumnIfNeeded;
DEALLOCATE PREPARE addStoreColumnIfNeeded;

-- 7. Add foreign key constraint for current_location_id
SET @constraint_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE CONSTRAINT_NAME = 'fk_rental_stores_location' AND TABLE_NAME = 'rental_stores' AND TABLE_SCHEMA = DATABASE());

SET @add_constraint = IF(@constraint_exists > 0,
    'SELECT 1',
    'ALTER TABLE rental_stores ADD CONSTRAINT fk_rental_stores_location FOREIGN KEY (current_location_id) REFERENCES rental_locations(id) ON DELETE SET NULL'
);
PREPARE addStoreConstraintIfNeeded FROM @add_constraint;
EXECUTE addStoreConstraintIfNeeded;
DEALLOCATE PREPARE addStoreConstraintIfNeeded;

-- 8. Add index for current_location_id if it doesn't exist
SET @index_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE INDEX_NAME = 'idx_rental_stores_current_location' AND TABLE_NAME = 'rental_stores' AND TABLE_SCHEMA = DATABASE());

SET @add_index = IF(@index_exists > 0,
    'SELECT 1',
    'CREATE INDEX idx_rental_stores_current_location ON rental_stores(current_location_id)'
);
PREPARE addStoreIndexIfNeeded FROM @add_index;
EXECUTE addStoreIndexIfNeeded;
DEALLOCATE PREPARE addStoreIndexIfNeeded;
