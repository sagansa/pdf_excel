-- Migration: Add short_name to companies table
ALTER TABLE companies ADD COLUMN short_name VARCHAR(50) AFTER name;
