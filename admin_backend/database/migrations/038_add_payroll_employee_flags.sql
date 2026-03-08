-- Migration 038: Store employee flags for Sagansa users in bank_converter DB
-- Purpose: keep payroll employee master local without altering Sagansa user table

CREATE TABLE IF NOT EXISTS payroll_employee_flags (
    sagansa_user_id VARCHAR(128) PRIMARY KEY,
    is_employee BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
