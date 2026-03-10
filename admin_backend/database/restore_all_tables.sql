-- COMPLETE DATABASE RECOVERY SCRIPT
-- This recreates ALL tables that were accidentally dropped
-- Run this to restore database structure before running migrations

-- ============================================
-- HPP BATCHES TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS hpp_batches (
    id CHAR(36) NOT NULL PRIMARY KEY,
    company_id CHAR(36) NOT NULL,
    memo TEXT,
    batch_date DATE,
    total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_company_id (company_id),
    INDEX idx_batch_date (batch_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hpp_batch_transactions (
    id CHAR(36) NOT NULL PRIMARY KEY,
    batch_id CHAR(36) NOT NULL,
    transaction_id CHAR(36) NOT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_batch_id (batch_id),
    INDEX idx_transaction_id (transaction_id),
    FOREIGN KEY (batch_id) REFERENCES hpp_batches(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hpp_batch_products (
    id CHAR(36) NOT NULL PRIMARY KEY,
    batch_id CHAR(36) NOT NULL,
    stock_monitoring_id CHAR(36) NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    foreign_currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    foreign_price DECIMAL(15,2) NOT NULL DEFAULT 0,
    calculated_total_idr DECIMAL(15,2) NOT NULL DEFAULT 0,
    calculated_unit_idr_hpp DECIMAL(15,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_batch_id (batch_id),
    INDEX idx_stock_monitoring_id (stock_monitoring_id),
    FOREIGN KEY (batch_id) REFERENCES hpp_batches(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- PRODUCTS TABLES (for backward compatibility)
-- ============================================

CREATE TABLE IF NOT EXISTS products (
    id CHAR(36) NOT NULL PRIMARY KEY,
    company_id CHAR(36),
    code VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    default_currency VARCHAR(10) DEFAULT 'USD',
    default_price DECIMAL(15,2) DEFAULT 0,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_company_id (company_id),
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS transaction_products (
    id CHAR(36) NOT NULL PRIMARY KEY,
    transaction_id CHAR(36) NOT NULL,
    product_id CHAR(36) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(15,2) NOT NULL,
    total DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_transaction_id (transaction_id),
    INDEX idx_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS product_storage_stock (
    product_id BIGINT UNSIGNED NOT NULL,
    storage_stock_id BIGINT UNSIGNED NOT NULL,
    quantity INT,
    PRIMARY KEY (product_id, storage_stock_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS product_remaining_stock (
    product_id BIGINT UNSIGNED NOT NULL,
    remaining_stock_id BIGINT UNSIGNED NOT NULL,
    quantity INT,
    PRIMARY KEY (product_id, remaining_stock_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS product_transfer_stock (
    product_id BIGINT UNSIGNED NOT NULL,
    transfer_stock_id BIGINT UNSIGNED NOT NULL,
    quantity INT,
    PRIMARY KEY (product_id, transfer_stock_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS product_request_stock (
    product_id BIGINT UNSIGNED NOT NULL,
    request_stock_id BIGINT UNSIGNED NOT NULL,
    quantity INT,
    PRIMARY KEY (product_id, request_stock_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- VERIFICATION
-- ============================================

SELECT 'Tables created successfully!' AS status;
SHOW TABLES LIKE 'hpp%';
SHOW TABLES LIKE 'product%';
