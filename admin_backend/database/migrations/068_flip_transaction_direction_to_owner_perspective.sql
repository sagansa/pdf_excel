-- Migration 068: Align transaction direction with owner perspective.
-- Internal convention after this migration:
--   DB = Debit to cash/bank = money IN
--   CR = Credit to cash/bank = money OUT
--
-- Scope:
-- 1. Flip imported bank transactions (including split children that inherit bank_code)
-- 2. Flip manual journal parent rows only
-- 3. Flip marks.natural_direction to keep report sign logic consistent
--
-- Manual journal child lines and system-generated journal rows are intentionally excluded,
-- because they already store actual journal sides.

UPDATE transactions
SET db_cr = CASE
    WHEN UPPER(TRIM(COALESCE(db_cr, ''))) IN ('CR', 'CREDIT', 'K', 'KREDIT') THEN 'DB'
    WHEN UPPER(TRIM(COALESCE(db_cr, ''))) IN ('DB', 'DEBIT', 'D', 'DE') THEN 'CR'
    ELSE db_cr
END
WHERE COALESCE(TRIM(bank_code), '') <> ''
  AND UPPER(TRIM(bank_code)) <> 'MANUAL';

UPDATE transactions
SET db_cr = CASE
    WHEN UPPER(TRIM(COALESCE(db_cr, ''))) IN ('CR', 'CREDIT', 'K', 'KREDIT') THEN 'DB'
    WHEN UPPER(TRIM(COALESCE(db_cr, ''))) IN ('DB', 'DEBIT', 'D', 'DE') THEN 'CR'
    ELSE db_cr
END
WHERE UPPER(TRIM(COALESCE(bank_code, ''))) = 'MANUAL'
  AND COALESCE(TRIM(parent_id), '') = '';

UPDATE marks
SET natural_direction = CASE
    WHEN UPPER(TRIM(COALESCE(natural_direction, ''))) IN ('CR', 'CREDIT', 'K', 'KREDIT') THEN 'DB'
    WHEN UPPER(TRIM(COALESCE(natural_direction, ''))) IN ('DB', 'DEBIT', 'D', 'DE') THEN 'CR'
    ELSE natural_direction
END
WHERE COALESCE(TRIM(natural_direction), '') <> '';
