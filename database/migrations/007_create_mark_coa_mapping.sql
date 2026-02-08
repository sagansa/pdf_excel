CREATE TABLE IF NOT EXISTS mark_coa_mapping (
    id CHAR(36) PRIMARY KEY,
    mark_id CHAR(36) NOT NULL,
    coa_id CHAR(36) NOT NULL,
    mapping_type ENUM('DEBIT', 'CREDIT') NOT NULL,
    notes TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (mark_id) REFERENCES marks(id) ON DELETE CASCADE,
    FOREIGN KEY (coa_id) REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
    UNIQUE KEY unique_mark_coa (mark_id, coa_id, mapping_type),
    INDEX idx_mark (mark_id),
    INDEX idx_coa (coa_id)
);
