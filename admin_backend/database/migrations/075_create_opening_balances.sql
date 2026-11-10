-- Migration 075: Tabel opening_balances — saldo awal per COA per company
-- per tahun, dipakai laporan trial balance (opening + mutasi = closing).
-- Divalidasi debit = kredit di layer aplikasi saat disimpan.

CREATE TABLE IF NOT EXISTS opening_balances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id CHAR(36) NULL,
    coa_id CHAR(36) NOT NULL,
    period_year INT NOT NULL,
    opening_debit DECIMAL(18,2) NOT NULL DEFAULT 0,
    opening_credit DECIMAL(18,2) NOT NULL DEFAULT 0,
    updated_at DATETIME NULL,
    UNIQUE KEY uq_opening_balance (company_id, coa_id, period_year),
    KEY idx_opening_balances_year (period_year),
    KEY idx_opening_balances_coa (coa_id)
);
