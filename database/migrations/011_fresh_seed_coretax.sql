-- Fresh Seed for CoreTax 2025 (Overwrites existing COA)
-- Deletes all existing accounts and re-seeds with the complete consolidated list

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE chart_of_accounts;
SET FOREIGN_KEY_CHECKS = 1;

-- ==========================================
-- NERACA (BALANCE SHEET)
-- ==========================================

-- 1. ASSETS (ASET)

-- 1.1 Current Assets (Aset Lancar)
INSERT IGNORE INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, created_at, updated_at) VALUES
(UUID(), '1101', 'Kas dan Setara Kas', 'ASSET', 'Current Assets', 'Cash and Cash Equivalents', TRUE, NOW(), NOW()),
(UUID(), '1122', 'Piutang Usaha - Pihak Ketiga', 'ASSET', 'Current Assets', 'Trade Receivables - Third Parties', TRUE, NOW(), NOW()),
(UUID(), '1123', 'Piutang Usaha - Hubungan Istimewa', 'ASSET', 'Current Assets', 'Trade Receivables - Related Parties', TRUE, NOW(), NOW()),
(UUID(), '1124', 'Piutang Lainnya - Pihak Ketiga', 'ASSET', 'Current Assets', 'Other Receivables - Third Parties', TRUE, NOW(), NOW()),
(UUID(), '1125', 'Piutang Lainnya - Hubungan Istimewa', 'ASSET', 'Current Assets', 'Other Receivables - Related Parties', TRUE, NOW(), NOW()),
(UUID(), '1131', 'Cadangan Kerugian Penurunan Nilai - Aset Tidak Lancar', 'ASSET', 'Current Assets', 'Impairment Allowance', TRUE, NOW(), NOW()),
(UUID(), '1181', 'Aset Kontrak', 'ASSET', 'Current Assets', 'Contract Assets', TRUE, NOW(), NOW()),
(UUID(), '1200', 'Investasi', 'ASSET', 'Current Assets', 'Investments', TRUE, NOW(), NOW()),
(UUID(), '1401', 'Persediaan', 'ASSET', 'Current Assets', 'Inventories', TRUE, NOW(), NOW()),
(UUID(), '1421', 'Biaya Dibayar di Muka', 'ASSET', 'Current Assets', 'Prepaid Expenses', TRUE, NOW(), NOW()),
(UUID(), '1423', 'Pajak Dibayar di Muka', 'ASSET', 'Current Assets', 'Prepaid Taxes', TRUE, NOW(), NOW()),
(UUID(), '1405', 'Aset yang Dimiliki Untuk Dijual', 'ASSET', 'Current Assets', 'Assets Held for Sale', TRUE, NOW(), NOW()),
(UUID(), '1422', 'Pendapatan Diterima di Muka (Aset)', 'ASSET', 'Current Assets', 'Accrued Revenue / Unearned Revenue (Asset side)', TRUE, NOW(), NOW()),
(UUID(), '1499', 'Aset lancar lainnya', 'ASSET', 'Current Assets', 'Other Current Assets', TRUE, NOW(), NOW());

-- 1.2 Non-Current Assets (Aset Tidak Lancar)
INSERT IGNORE INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, created_at, updated_at) VALUES
(UUID(), '1501', 'Piutang Jangka Panjang', 'ASSET', 'Non-Current Assets', 'Long-term Receivables', TRUE, NOW(), NOW()),
(UUID(), '1520', 'Properti Investasi', 'ASSET', 'Non-Current Assets', 'Investment Properties', TRUE, NOW(), NOW()),
(UUID(), '1523', 'Tanah dan Bangunan', 'ASSET', 'Non-Current Assets', 'Land and Buildings', TRUE, NOW(), NOW()),
(UUID(), '1524', 'Akumulasi Penyusutan - Tanah dan Bangunan', 'ASSET', 'Non-Current Assets', 'Accumulated Depreciation - Land and Building', TRUE, NOW(), NOW()),
(UUID(), '1529', 'Aset Tetap Lainnya', 'ASSET', 'Non-Current Assets', 'Other Fixed Assets', TRUE, NOW(), NOW()),
(UUID(), '1530', 'Akumulasi Penyusutan - Aset Tetap Lainnya', 'ASSET', 'Non-Current Assets', 'Accumulated Depreciation - Other Fixed Assets', TRUE, NOW(), NOW()),
(UUID(), '1531', 'Aset Biologis', 'ASSET', 'Non-Current Assets', 'Biological Assets', TRUE, NOW(), NOW()),
(UUID(), '1533', 'Aset Hak Guna', 'ASSET', 'Non-Current Assets', 'Right of Use Assets', TRUE, NOW(), NOW()),
(UUID(), '1534', 'Akumulasi Penyusutan - Aset Hak Guna', 'ASSET', 'Non-Current Assets', 'Accumulated Depreciation - Right of Use Assets', TRUE, NOW(), NOW()),
(UUID(), '1551', 'Investasi pada Perusahaan Asosiasi', 'ASSET', 'Non-Current Assets', 'Investment in Associates', TRUE, NOW(), NOW()),
(UUID(), '1599', 'Investasi Jangka Panjang Lainnya', 'ASSET', 'Non-Current Assets', 'Other Long-term Investments', TRUE, NOW(), NOW()),
(UUID(), '1600', 'Aset Tak Berwujud', 'ASSET', 'Non-Current Assets', 'Intangible Assets', TRUE, NOW(), NOW()),
(UUID(), '1601', 'Akumulasi Amortisasi - Aset Tak Berwujud', 'ASSET', 'Non-Current Assets', 'Accumulated Amortization', TRUE, NOW(), NOW()),
(UUID(), '1611', 'Aktiva Pajak Tangguhan', 'ASSET', 'Non-Current Assets', 'Deferred Tax Assets', TRUE, NOW(), NOW()),
(UUID(), '1651', 'Klaim atas pengembalian pajak', 'ASSET', 'Non-Current Assets', 'Tax Refund Claims', TRUE, NOW(), NOW()),
(UUID(), '1658', 'Cadangan Kerugian Penurunan Nilai - Aset Tidak Lancar', 'ASSET', 'Non-Current Assets', 'Impairment Allowance - Non Current', TRUE, NOW(), NOW()),
(UUID(), '1698', 'Aset Tidak Lancar Lainnya', 'ASSET', 'Non-Current Assets', 'Other Non-Current Assets', TRUE, NOW(), NOW());

-- 2. LIABILITIES (KEWAJIBAN)

-- 2.1 Current Liabilities (Liabilitas Jangka Pendek)
INSERT IGNORE INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, created_at, updated_at) VALUES
(UUID(), '2102', 'Utang Usaha - Pihak Ketiga', 'LIABILITY', 'Current Liabilities', 'Trade Payables - Third Parties', TRUE, NOW(), NOW()),
(UUID(), '2103', 'Utang Usaha - Hubungan Istimewa', 'LIABILITY', 'Current Liabilities', 'Trade Payables - Related Parties', TRUE, NOW(), NOW()),
(UUID(), '2111', 'Utang Bunga', 'LIABILITY', 'Current Liabilities', 'Interest Payable', TRUE, NOW(), NOW()),
(UUID(), '2186', 'Liabilitas Kontrak', 'LIABILITY', 'Current Liabilities', 'Contract Liabilities', TRUE, NOW(), NOW()),
(UUID(), '2187', 'Liabilitas Sewa Jangka Pendek', 'LIABILITY', 'Current Liabilities', 'Short-term Lease Liabilities', TRUE, NOW(), NOW()),
(UUID(), '2191', 'Utang Pajak', 'LIABILITY', 'Current Liabilities', 'Tax Payable', TRUE, NOW(), NOW()),
(UUID(), '2192', 'Utang Dividen', 'LIABILITY', 'Current Liabilities', 'Dividends Payable', TRUE, NOW(), NOW()),
(UUID(), '2195', 'Beban yang Masih Harus Dibayar', 'LIABILITY', 'Current Liabilities', 'Accrued Expenses', TRUE, NOW(), NOW()),
(UUID(), '2201', 'Utang Bank Jangka Pendek', 'LIABILITY', 'Current Liabilities', 'Short-term Bank Loans', TRUE, NOW(), NOW()),
(UUID(), '2202', 'Utang Jangka Panjang Jatuh Tempo Setahun', 'LIABILITY', 'Current Liabilities', 'Current Maturities of Long-term Debt', TRUE, NOW(), NOW()),
(UUID(), '2203', 'Pendapatan Diterima di Muka', 'LIABILITY', 'Current Liabilities', 'Unearned Revenue', TRUE, NOW(), NOW()),
(UUID(), '2228', 'Liabilitas Jangka Pendek Lainnya', 'LIABILITY', 'Current Liabilities', 'Other Current Liabilities', TRUE, NOW(), NOW());

-- 2.2 Non-Current Liabilities (Liabilitas Jangka Panjang)
INSERT IGNORE INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, created_at, updated_at) VALUES
(UUID(), '2301', 'Utang Bank Jangka Panjang', 'LIABILITY', 'Non-Current Liabilities', 'Long-term Bank Loans', TRUE, NOW(), NOW()),
(UUID(), '2303', 'Utang Jangka Panjang - Pihak Ketiga', 'LIABILITY', 'Non-Current Liabilities', 'Long-term Debt - Third Parties', TRUE, NOW(), NOW()),
(UUID(), '2304', 'Utang Jangka Panjang - Hubungan Istimewa', 'LIABILITY', 'Non-Current Liabilities', 'Long-term Debt - Related Parties', TRUE, NOW(), NOW()),
(UUID(), '2312', 'Liabilitas Sewa', 'LIABILITY', 'Non-Current Liabilities', 'Lease Liabilities', TRUE, NOW(), NOW()),
(UUID(), '2321', 'Liabilitas Pajak Tangguhan', 'LIABILITY', 'Non-Current Liabilities', 'Deferred Tax Liabilities', TRUE, NOW(), NOW()),
(UUID(), '2322', 'Liabilitas Imbalan Kerja', 'LIABILITY', 'Non-Current Liabilities', 'Employee Benefit Obligations', TRUE, NOW(), NOW()),
(UUID(), '2998', 'Liabilitas Jangka Panjang Lainnya', 'LIABILITY', 'Non-Current Liabilities', 'Other Long-term Liabilities', TRUE, NOW(), NOW());

-- 3. EQUITY (EKUITAS)
INSERT IGNORE INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, created_at, updated_at) VALUES
(UUID(), '3102', 'Modal Saham', 'EQUITY', 'Equity', 'Share Capital', TRUE, NOW(), NOW()),
(UUID(), '3120', 'Tambahan Modal Disetor', 'EQUITY', 'Equity', 'Additional Paid-in Capital', TRUE, NOW(), NOW()),
(UUID(), '3200', 'Laba Ditahan', 'EQUITY', 'Equity', 'Retained Earnings', TRUE, NOW(), NOW()),
(UUID(), '3297', 'Pendapatan Komprehensif Lainnya', 'EQUITY', 'Equity', 'Other Comprehensive Income', TRUE, NOW(), NOW()),
(UUID(), '3298', 'Ekuitas Lainnya', 'EQUITY', 'Equity', 'Other Equity', TRUE, NOW(), NOW());

-- ==========================================
-- LABA RUGI (INCOME STATEMENT)
-- ==========================================

-- 4. REVENUE (PENDAPATAN)
INSERT IGNORE INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, created_at, updated_at) VALUES
(UUID(), '4002', 'Penjualan Domestik', 'REVENUE', 'Operating Revenue', 'Domestic Sales', TRUE, NOW(), NOW()),
(UUID(), '4003', 'Penjualan Ekspor', 'REVENUE', 'Operating Revenue', 'Export Sales', TRUE, NOW(), NOW()),
(UUID(), '4004', 'Penjualan Bruto', 'REVENUE', 'Operating Revenue', 'Gross Sales', TRUE, NOW(), NOW()),
-- Sales Deductions (Pengurang)
(UUID(), '4011', 'Retur Penjualan', 'REVENUE', 'Sales Deductions', 'Sales Returns', TRUE, NOW(), NOW()),
(UUID(), '4012', 'Potongan Penjualan', 'REVENUE', 'Sales Deductions', 'Sales Discounts', TRUE, NOW(), NOW()),
(UUID(), '4013', 'Penyesuaian Penjualan', 'REVENUE', 'Sales Deductions', 'Sales Adjustments', TRUE, NOW(), NOW()),
-- Other Revenue
(UUID(), '4501', 'Keuntungan Selisih Kurs', 'REVENUE', 'Non-Operating Revenue', 'Check CoreTax for category', TRUE, NOW(), NOW()),
(UUID(), '4503', 'Keuntungan Penjualan Aset selain Persediaan', 'REVENUE', 'Non-Operating Revenue', 'Gain on Sale of Non-Inventory Assets', TRUE, NOW(), NOW()),
(UUID(), '4511', 'Pendapatan Bunga', 'REVENUE', 'Non-Operating Revenue', 'Interest Income', TRUE, NOW(), NOW()),
(UUID(), '4599', 'Pendapatan Non Usaha Lainnya', 'REVENUE', 'Non-Operating Revenue', 'Other Income', TRUE, NOW(), NOW());

-- 5. EXPENSES (BEBAN)

-- 5.1 COGS (HPP)
INSERT IGNORE INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, created_at, updated_at) VALUES
(UUID(), '5001', 'Pembelian', 'EXPENSE', 'Cost of Goods Sold', 'Purchases', TRUE, NOW(), NOW()),
(UUID(), '5003', 'Beban Pengangkutan', 'EXPENSE', 'Cost of Goods Sold', 'Freight In', TRUE, NOW(), NOW()),
(UUID(), '5007', 'Beban Operasional Lainnya', 'EXPENSE', 'Cost of Goods Sold', 'Other COGS Expenses', TRUE, NOW(), NOW()),
(UUID(), '5008', 'Persediaan - Awal', 'EXPENSE', 'Cost of Goods Sold', 'Beginning Inventory', TRUE, NOW(), NOW()),
(UUID(), '5009', 'Persediaan - Akhir', 'EXPENSE', 'Cost of Goods Sold', 'Ending Inventory (Contra)', TRUE, NOW(), NOW());

-- 5.2 Operating Expenses (Beban Usaha)
INSERT IGNORE INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, created_at, updated_at) VALUES
(UUID(), '5311', 'Gaji, Tunjangan, Bonus, Honorarium, THR, dsb', 'EXPENSE', 'Operating Expenses', 'Salary, Allowances, Bonuses, Honorariums, THR, etc.', TRUE, NOW(), NOW()),
(UUID(), '5312', 'Beban Imbalan Kerja Lainnya', 'EXPENSE', 'Operating Expenses', 'Other Employee Benefits Expense', TRUE, NOW(), NOW()),
(UUID(), '5313', 'Beban Transportasi', 'EXPENSE', 'Operating Expenses', 'Transport Expense', TRUE, NOW(), NOW()),
(UUID(), '5314', 'Beban Penyusutan dan Amortisasi', 'EXPENSE', 'Operating Expenses', 'Depreciation & Amortization', TRUE, NOW(), NOW()),
(UUID(), '5315', 'Beban Sewa', 'EXPENSE', 'Operating Expenses', 'Rent Expense', TRUE, NOW(), NOW()),
(UUID(), '5316', 'Beban Bunga', 'EXPENSE', 'Operating Expenses', 'Interest Expense', TRUE, NOW(), NOW()),
(UUID(), '5317', 'Beban Sehubungan dengan Jasa', 'EXPENSE', 'Operating Expenses', 'Service Fees', TRUE, NOW(), NOW()),
(UUID(), '5318', 'Beban Penurunan Nilai', 'EXPENSE', 'Operating Expenses', 'Impairment Loss', TRUE, NOW(), NOW()),
(UUID(), '5319', 'Beban Royalti', 'EXPENSE', 'Operating Expenses', 'Royalty Expense', TRUE, NOW(), NOW()),
(UUID(), '5320', 'Beban Pemasaran atau Promosi', 'EXPENSE', 'Operating Expenses', 'Marketing Expense', TRUE, NOW(), NOW()),
(UUID(), '5321', 'Beban Entertainment', 'EXPENSE', 'Operating Expenses', 'Entertainment Expense', TRUE, NOW(), NOW()),
(UUID(), '5322', 'Beban Umum dan Administrasi', 'EXPENSE', 'Operating Expenses', 'G&A Expense', TRUE, NOW(), NOW()),
(UUID(), '5399', 'Beban usaha lainnya', 'EXPENSE', 'Operating Expenses', 'Other Operating Expenses', TRUE, NOW(), NOW()),
(UUID(), '5405', 'Kerugian Penjualan Aset selain Persediaan', 'EXPENSE', 'Operating Expenses', 'Loss on Sale of Non-Inventory Assets', TRUE, NOW(), NOW()),
(UUID(), '5409', 'Sumbangan', 'EXPENSE', 'Operating Expenses', 'Donation Expense', TRUE, NOW(), NOW()),
(UUID(), '5421', 'Kerugian Selisih Kurs', 'EXPENSE', 'Operating Expenses', 'Loss on Foreign Exchange', TRUE, NOW(), NOW()),
(UUID(), '5499', 'Beban Non Usaha Lainnya', 'EXPENSE', 'Operating Expenses', 'Other Non-Operating Expenses', TRUE, NOW(), NOW());
