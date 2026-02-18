CREATE TABLE IF NOT EXISTS transaction_splits (
    id CHAR(36) PRIMARY KEY,
    transaction_id CHAR(36) NOT NULL,
    mark_id CHAR(36) NOT NULL,
    amount DECIMAL(20,2) NOT NULL,
    notes TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (mark_id) REFERENCES marks(id) ON DELETE CASCADE,
    INDEX idx_transaction (transaction_id),
    INDEX idx_mark (mark_id)
);
