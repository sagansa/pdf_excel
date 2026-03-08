-- Migration 045 (SQLite): Support separate COA mappings for Real vs Coretax reports.

ALTER TABLE mark_coa_mapping ADD COLUMN report_type TEXT DEFAULT 'real';

UPDATE mark_coa_mapping
SET report_type = CASE
  WHEN report_type IS NULL OR TRIM(report_type) = '' THEN 'real'
  WHEN LOWER(TRIM(report_type)) = 'coretax' THEN 'coretax'
  ELSE 'real'
END;

DROP INDEX IF EXISTS unique_mark_coa;
CREATE UNIQUE INDEX IF NOT EXISTS unique_mark_coa_scope
  ON mark_coa_mapping (mark_id, coa_id, mapping_type, report_type);

CREATE INDEX IF NOT EXISTS idx_mark_report_type
  ON mark_coa_mapping (mark_id, report_type);
