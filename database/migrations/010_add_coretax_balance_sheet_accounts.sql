-- Add CoreTax 2025 Balance Sheet accounts based on user requirements

-- ASSETS (ASET)

-- Current Assets (Aset Lancar)
INSERT INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
(UUID(), '1101', 'Kas dan Setara Kas', 'ASSET', 'Current Assets', 'Cash and Cash Equivalents', TRUE, NULL, NOW(), NOW()),
(UUID(), '1122', 'Piutang Usaha - Pihak Ketiga', 'ASSET', 'Current Assets', 'Trade Receivables - Third Parties', TRUE, NULL, NOW(), NOW()),
(UUID(), '1123', 'Piutang Usaha - Hubungan Istimewa', 'ASSET', 'Current Assets', 'Trade Receivables - Related Parties', TRUE, NULL, NOW(), NOW()),
(UUID(), '1124', 'Piutang Lainnya - Pihak Ketiga', 'ASSET', 'Current Assets', 'Other Receivables - Third Parties', TRUE, NULL, NOW(), NOW()),
(UUID(), '1125', 'Piutang Lainnya - Hubungan Istimewa', 'ASSET', 'Current Assets', 'Other Receivables - Related Parties', TRUE, NULL, NOW(), NOW()),
(UUID(), '1131', 'Cadangan Kerugian Penurunan Nilai - Aset Tidak Lancar', 'ASSET', 'Current Assets', 'Impairment Allowance', TRUE, NULL, NOW(), NOW()),
(UUID(), '1181', 'Aset Kontrak', 'ASSET', 'Current Assets', 'Contract Assets', TRUE, NULL, NOW(), NOW()),
(UUID(), '1200', 'Investasi', 'ASSET', 'Current Assets', 'Investments', TRUE, NULL, NOW(), NOW()),
(UUID(), '1401', 'Persediaan', 'ASSET', 'Current Assets', 'Inventories', TRUE, NULL, NOW(), NOW()),
(UUID(), '1421', 'Biaya Dibayar di Muka', 'ASSET', 'Current Assets', 'Prepaid Expenses', TRUE, NULL, NOW(), NOW()),
(UUID(), '1423', 'Pajak Dibayar di Muka', 'ASSET', 'Current Assets', 'Prepaid Taxes', TRUE, NULL, NOW(), NOW()),
(UUID(), '1405', 'Aset yang Dimiliki Untuk Dijual', 'ASSET', 'Current Assets', 'Assets Held for Sale', TRUE, NULL, NOW(), NOW()),
(UUID(), '1422', 'Pendapatan Diterima di Muka (Aset)', 'ASSET', 'Current Assets', 'Accrued Revenue / Unearned Revenue (Asset side per CoreTax)', TRUE, NULL, NOW(), NOW()),
(UUID(), '1499', 'Aset lancar lainnya', 'ASSET', 'Current Assets', 'Other Current Assets', TRUE, NULL, NOW(), NOW());

-- Non-Current Assets (Aset Tidak Lancar)
INSERT INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
(UUID(), '1501', 'Piutang Jangka Panjang', 'ASSET', 'Non-Current Assets', 'Long-term Receivables', TRUE, NULL, NOW(), NOW()),
(UUID(), '1520', 'Properti Investasi', 'ASSET', 'Non-Current Assets', 'Investment Properties', TRUE, NULL, NOW(), NOW()),
(UUID(), '1523', 'Tanah dan Bangunan', 'ASSET', 'Non-Current Assets', 'Land and Buildings', TRUE, NULL, NOW(), NOW()),
(UUID(), '1524', 'Akumulasi Penyusutan - Tanah dan Bangunan', 'ASSET', 'Non-Current Assets', 'Accumulated Depreciation - Land and Building (Contra Asset)', TRUE, NULL, NOW(), NOW()),
(UUID(), '1529', 'Aset Tetap Lainnya', 'ASSET', 'Non-Current Assets', 'Other Fixed Assets', TRUE, NULL, NOW(), NOW()),
(UUID(), '1530', 'Akumulasi Penyusutan - Aset Tetap Lainnya', 'ASSET', 'Non-Current Assets', 'Accumulated Depreciation - Other Fixed Assets (Contra Asset)', TRUE, NULL, NOW(), NOW()),
(UUID(), '1531', 'Aset Biologis', 'ASSET', 'Non-Current Assets', 'Biological Assets', TRUE, NULL, NOW(), NOW()),
(UUID(), '1533', 'Aset Hak Guna', 'ASSET', 'Non-Current Assets', 'Right of Use Assets', TRUE, NULL, NOW(), NOW()),
(UUID(), '1534', 'Akumulasi Penyusutan - Aset Hak Guna', 'ASSET', 'Non-Current Assets', 'Accumulated Depreciation - Right of Use Assets', TRUE, NULL, NOW(), NOW()),
(UUID(), '1551', 'Investasi pada Perusahaan Asosiasi', 'ASSET', 'Non-Current Assets', 'Investment in Associates', TRUE, NULL, NOW(), NOW()),
(UUID(), '1599', 'Investasi Jangka Panjang Lainnya', 'ASSET', 'Non-Current Assets', 'Other Long-term Investments', TRUE, NULL, NOW(), NOW()),
(UUID(), '1600', 'Aset Tak Berwujud', 'ASSET', 'Non-Current Assets', 'Intangible Assets', TRUE, NULL, NOW(), NOW()),
(UUID(), '1601', 'Akumulasi Amortisasi - Aset Tak Berwujud', 'ASSET', 'Non-Current Assets', 'Accumulated Amortization', TRUE, NULL, NOW(), NOW()),
(UUID(), '1611', 'Aktiva Pajak Tangguhan', 'ASSET', 'Non-Current Assets', 'Deferred Tax Assets', TRUE, NULL, NOW(), NOW()),
(UUID(), '1651', 'Klaim atas pengembalian pajak', 'ASSET', 'Non-Current Assets', 'Tax Refund Claims', TRUE, NULL, NOW(), NOW()),
(UUID(), '1658', 'Cadangan Kerugian Penurunan Nilai - Aset Tidak Lancar', 'ASSET', 'Non-Current Assets', 'Impairment Allowance - Non Current', TRUE, NULL, NOW(), NOW()),
(UUID(), '1698', 'Aset Tidak Lancar Lainnya', 'ASSET', 'Non-Current Assets', 'Other Non-Current Assets', TRUE, NULL, NOW(), NOW());


-- LIABILITIES (KEWAJIBAN)

-- Current Liabilities (Liabilitas Jangka Pendek)
INSERT INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
(UUID(), '2102', 'Utang Usaha - Pihak Ketiga', 'LIABILITY', 'Current Liabilities', 'Trade Payables - Third Parties', TRUE, NULL, NOW(), NOW()),
(UUID(), '2103', 'Utang Usaha - Hubungan Istimewa', 'LIABILITY', 'Current Liabilities', 'Trade Payables - Related Parties', TRUE, NULL, NOW(), NOW()),
(UUID(), '2111', 'Utang Bunga', 'LIABILITY', 'Current Liabilities', 'Interest Payable', TRUE, NULL, NOW(), NOW()),
(UUID(), '2186', 'Liabilitas Kontrak', 'LIABILITY', 'Current Liabilities', 'Contract Liabilities', TRUE, NULL, NOW(), NOW()),
(UUID(), '2187', 'Liabilitas Sewa Jangka Pendek', 'LIABILITY', 'Current Liabilities', 'Short-term Lease Liabilities', TRUE, NULL, NOW(), NOW()),
(UUID(), '2191', 'Utang Pajak', 'LIABILITY', 'Current Liabilities', 'Tax Payable', TRUE, NULL, NOW(), NOW()),
(UUID(), '2192', 'Utang Dividen', 'LIABILITY', 'Current Liabilities', 'Dividends Payable', TRUE, NULL, NOW(), NOW()),
(UUID(), '2195', 'Beban yang Masih Harus Dibayar', 'LIABILITY', 'Current Liabilities', 'Accrued Expenses', TRUE, NULL, NOW(), NOW()),
(UUID(), '2201', 'Utang Bank Jangka Pendek', 'LIABILITY', 'Current Liabilities', 'Short-term Bank Loans', TRUE, NULL, NOW(), NOW()),
(UUID(), '2202', 'Utang Jangka Panjang Jatuh Tempo Setahun', 'LIABILITY', 'Current Liabilities', 'Current Maturities of Long-term Debt', TRUE, NULL, NOW(), NOW()),
(UUID(), '2203', 'Pendapatan Diterima di Muka', 'LIABILITY', 'Current Liabilities', 'Unearned Revenue', TRUE, NULL, NOW(), NOW()),
(UUID(), '2228', 'Liabilitas Jangka Pendek Lainnya', 'LIABILITY', 'Current Liabilities', 'Other Current Liabilities', TRUE, NULL, NOW(), NOW());

-- Non-Current Liabilities (Liabilitas Jangka Panjang)
INSERT INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
(UUID(), '2301', 'Utang Bank Jangka Panjang', 'LIABILITY', 'Non-Current Liabilities', 'Long-term Bank Loans', TRUE, NULL, NOW(), NOW()),
(UUID(), '2303', 'Utang Jangka Panjang - Pihak Ketiga', 'LIABILITY', 'Non-Current Liabilities', 'Long-term Debt - Third Parties', TRUE, NULL, NOW(), NOW()),
(UUID(), '2304', 'Utang Jangka Panjang - Hubungan Istimewa', 'LIABILITY', 'Non-Current Liabilities', 'Long-term Debt - Related Parties', TRUE, NULL, NOW(), NOW()),
(UUID(), '2312', 'Liabilitas Sewa', 'LIABILITY', 'Non-Current Liabilities', 'Lease Liabilities', TRUE, NULL, NOW(), NOW()),
(UUID(), '2322', 'Liabilitas Imbalan Kerja', 'LIABILITY', 'Non-Current Liabilities', 'Employee Benefit Obligations', TRUE, NULL, NOW(), NOW()),
(UUID(), '2321', 'Liabilitas Pajak Tangguhan', 'LIABILITY', 'Non-Current Liabilities', 'Deferred Tax Liabilities', TRUE, NULL, NOW(), NOW()),
(UUID(), '2998', 'Liabilitas Jangka Panjang Lainnya', 'LIABILITY', 'Non-Current Liabilities', 'Other Long-term Liabilities', TRUE, NULL, NOW(), NOW());


-- EQUITY (EKUITAS)
INSERT INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
(UUID(), '3102', 'Modal Saham', 'EQUITY', 'Equity', 'Share Capital', TRUE, NULL, NOW(), NOW()),
(UUID(), '3120', 'Tambahan Modal Disetor', 'EQUITY', 'Equity', 'Additional Paid-in Capital', TRUE, NULL, NOW(), NOW()),
(UUID(), '3200', 'Laba Ditahan', 'EQUITY', 'Equity', 'Retained Earnings', TRUE, NULL, NOW(), NOW()),
(UUID(), '3297', 'Pendapatan Komprehensif Lainnya', 'EQUITY', 'Equity', 'Other Comprehensive Income', TRUE, NULL, NOW(), NOW()),
(UUID(), '3298', 'Ekuitas Lainnya', 'EQUITY', 'Equity', 'Other Equity', TRUE, NULL, NOW(), NOW());
