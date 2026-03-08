-- Add natural_direction to marks table
-- This field defines the expected transaction direction for the mark.
-- DB = mark is designed for debit/outflow transactions (e.g. purchases, expenses)
-- CR = mark is designed for credit/inflow transactions (e.g. sales, revenue)
-- When a transaction's db_cr opposes the mark's natural_direction, the sign is reversed.

ALTER TABLE marks ADD COLUMN natural_direction VARCHAR(2) DEFAULT NULL;

-- Auto-populate based on majority direction of existing transactions per mark
UPDATE marks m
SET m.natural_direction = (
    SELECT CASE
        WHEN SUM(CASE WHEN UPPER(TRIM(t.db_cr)) IN ('DB', 'DEBIT', 'D', 'DE') THEN 1 ELSE 0 END) >=
             SUM(CASE WHEN UPPER(TRIM(t.db_cr)) IN ('CR', 'CREDIT', 'K', 'KREDIT') THEN 1 ELSE 0 END)
        THEN 'DB'
        ELSE 'CR'
    END
    FROM transactions t
    WHERE t.mark_id = m.id
    AND t.mark_id IS NOT NULL
)
WHERE EXISTS (SELECT 1 FROM transactions t WHERE t.mark_id = m.id);
