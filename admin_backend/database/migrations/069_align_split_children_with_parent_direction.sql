-- Migration 069: Ensure split child transactions follow the same cash direction as their parent.
--
-- Root cause:
-- - Historical split child rows were stored without bank_code/source_file.
-- - Migration 068 flipped bank/import rows and manual parents, but those split children were skipped.
-- - Result: parent and child rows could use different DB/CR conventions, which is especially confusing
--   in COA detail screens after split allocation.
--
-- Rule:
-- - Split children of non-manual parent transactions represent the same cash movement as the parent.
-- - Therefore their db_cr must always match the parent transaction's db_cr.

UPDATE transactions child
JOIN transactions parent ON parent.id = child.parent_id
SET child.db_cr = parent.db_cr
WHERE COALESCE(TRIM(child.parent_id), '') <> ''
  AND COALESCE(TRIM(parent.bank_code), '') <> ''
  AND UPPER(TRIM(parent.bank_code)) <> 'MANUAL'
  AND COALESCE(TRIM(child.db_cr), '') <> COALESCE(TRIM(parent.db_cr), '');
