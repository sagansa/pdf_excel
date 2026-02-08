CREATE TABLE IF NOT EXISTS chart_of_accounts (
    id CHAR(36) PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    category ENUM('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE') NOT NULL,
    subcategory VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    parent_id CHAR(36),
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (parent_id) REFERENCES chart_of_accounts(id) ON DELETE SET NULL,
    INDEX idx_code (code),
    INDEX idx_category (category),
    INDEX idx_parent (parent_id)
);
