CREATE TABLE IF NOT EXISTS marks (
    id CHAR(36) PRIMARY KEY,
    internal_report TEXT,
    personal_use TEXT,
    tax_report TEXT,
    created_at DATETIME,
    updated_at DATETIME
);
