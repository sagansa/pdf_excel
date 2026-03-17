-- Migration 061: Create manual_journal_links table
-- Links a manual journal entry (parent transaction) to one or more existing transactions
-- for audit traceability and cross-referencing

CREATE TABLE IF NOT EXISTS manual_journal_links (
    id CHAR(36) NOT NULL PRIMARY KEY,
    manual_txn_id CHAR(36) NOT NULL COMMENT 'Parent transaction ID of the manual journal',
    linked_txn_id CHAR(36) NOT NULL COMMENT 'Existing transaction being linked to',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_manual_linked (manual_txn_id, linked_txn_id),
    KEY idx_mjl_manual (manual_txn_id),
    KEY idx_mjl_linked (linked_txn_id)
);
