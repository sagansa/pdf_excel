-- Migration 041: Add base_value to inventory_balances
-- This column is required for the new inventory carrying logic

ALTER TABLE inventory_balances 
ADD COLUMN base_value DECIMAL(15, 2) NOT NULL DEFAULT 0.00;
