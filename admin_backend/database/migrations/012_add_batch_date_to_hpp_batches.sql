-- Add batch_date column to hpp_batches table
-- This stores the date of the COGS batch (typically the date of the earliest transaction in the batch)

ALTER TABLE hpp_batches 
ADD COLUMN batch_date DATE NULL AFTER memo;

-- Update existing batches with a default date (created_at date)
UPDATE hpp_batches 
SET batch_date = DATE(created_at) 
WHERE batch_date IS NULL;
