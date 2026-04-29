-- Migration 066: Hide system-generated manual journal marks from master marks screen

ALTER TABLE marks
  ADD COLUMN is_system_generated TINYINT(1) NOT NULL DEFAULT 0;

UPDATE marks m
JOIN transactions t ON t.mark_id = m.id
SET m.is_system_generated = 1
WHERE t.bank_code = 'MANUAL'
  AND COALESCE(t.parent_id, '') != '';

CREATE INDEX idx_marks_system_generated ON marks (is_system_generated);
