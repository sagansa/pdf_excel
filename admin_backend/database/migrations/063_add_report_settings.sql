-- Migration 063: Add report_settings table for director and location details
-- Supports period-based (year) configuration as requested

CREATE TABLE IF NOT EXISTS report_settings (
    id CHAR(36) PRIMARY KEY,
    company_id CHAR(36) NOT NULL,
    year INT NOT NULL,
    director_name VARCHAR(255),
    director_title VARCHAR(255) DEFAULT 'Direktur Utama',
    location VARCHAR(255) DEFAULT 'Jakarta',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_company_year (company_id, year),
    CONSTRAINT fk_report_settings_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);
