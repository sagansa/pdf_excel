-- Add category and subcategory columns to chart_of_accounts table
-- This migration adds the columns that are used by server.py but missing in the database

-- Add category column (ENUM for main categories)
-- SQLite doesn't support ENUM, so we'll use TEXT with CHECK constraint
ALTER TABLE chart_of_accounts ADD COLUMN category TEXT;

-- Add subcategory column
ALTER TABLE chart_of_accounts ADD COLUMN subcategory TEXT;

-- Add CHECK constraint for valid categories (SQLite syntax)
-- Note: In SQLite, CHECK constraints are added to the table, not individual columns
-- We'll handle category validation in application logic

-- Populate category based on existing account_type
UPDATE chart_of_accounts SET category = account_type
WHERE category IS NULL AND account_type IS NOT NULL;

-- Populate subcategory based on existing account_subtype  
UPDATE chart_of_accounts SET subcategory = account_subtype
WHERE subcategory IS NULL AND account_subtype IS NOT NULL;

-- Set default values for NULLs
UPDATE chart_of_accounts SET category = 'EXPENSE' 
WHERE category IS NULL AND code LIKE '5%';

UPDATE chart_of_accounts SET category = 'REVENUE'
WHERE category IS NULL AND code LIKE '4%';

UPDATE chart_of_accounts SET category = 'ASSET'
WHERE category IS NULL AND code LIKE '1%';

UPDATE chart_of_accounts SET category = 'LIABILITY'
WHERE category IS NULL AND code LIKE '2%';

UPDATE chart_of_accounts SET category = 'EQUITY'
WHERE category IS NULL AND code LIKE '3%';
