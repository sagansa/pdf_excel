-- Add notes column to transactions table

ALTER TABLE transactions ADD COLUMN notes TEXT NULL AFTER file_hash;
