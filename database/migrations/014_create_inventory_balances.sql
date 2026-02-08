-- Migration 014: Create inventory_balances table
-- This table stores manual inventory adjustments for Beginning and Ending Inventory

CREATE TABLE IF NOT EXISTS inventory_balances (
    id VARCHAR(36) PRIMARY KEY,
    company_id VARCHAR(36) NOT NULL,
    year INT NOT NULL,
    beginning_inventory_amount DECIMAL(15,2) DEFAULT 0.00,
    beginning_inventory_qty DECIMAL(15,2) DEFAULT 0.00,
    ending_inventory_amount DECIMAL(15,2) DEFAULT 0.00,
    ending_inventory_qty DECIMAL(15,2) DEFAULT 0.00,
    is_manual BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
