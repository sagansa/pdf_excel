-- Seed Chart of Accounts with standard Indonesian accounts
-- This follows basic Indonesian accounting standards (PSAK)

-- ASSETS (1-xxxx)
INSERT INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
-- Current Assets
(UUID(), '1-0000', 'ASET LANCAR', 'ASSET', 'Current Assets', 'Aset yang dapat dikonversi menjadi kas dalam waktu 1 tahun', TRUE, NULL, NOW(), NOW()),
(UUID(), '1-1000', 'Kas', 'ASSET', 'Current Assets', 'Uang tunai di tangan', TRUE, NULL, NOW(), NOW()),
(UUID(), '1-1100', 'Bank', 'ASSET', 'Current Assets', 'Rekening bank perusahaan', TRUE, NULL, NOW(), NOW()),
(UUID(), '1-1200', 'Piutang Usaha', 'ASSET', 'Current Assets', 'Tagihan kepada pelanggan', TRUE, NULL, NOW(), NOW()),
(UUID(), '1-1300', 'Persediaan', 'ASSET', 'Current Assets', 'Barang dagangan atau bahan baku', TRUE, NULL, NOW(), NOW()),
(UUID(), '1-1400', 'Biaya Dibayar Dimuka', 'ASSET', 'Current Assets', 'Pembayaran di muka untuk periode mendatang', TRUE, NULL, NOW(), NOW()),

-- Fixed Assets
(UUID(), '1-2000', 'ASET TETAP', 'ASSET', 'Fixed Assets', 'Aset jangka panjang untuk operasional', TRUE, NULL, NOW(), NOW()),
(UUID(), '1-2100', 'Tanah', 'ASSET', 'Fixed Assets', 'Tanah milik perusahaan', TRUE, NULL, NOW(), NOW()),
(UUID(), '1-2200', 'Bangunan', 'ASSET', 'Fixed Assets', 'Gedung dan bangunan', TRUE, NULL, NOW(), NOW()),
(UUID(), '1-2300', 'Kendaraan', 'ASSET', 'Fixed Assets', 'Kendaraan operasional', TRUE, NULL, NOW(), NOW()),
(UUID(), '1-2400', 'Peralatan', 'ASSET', 'Fixed Assets', 'Peralatan dan mesin', TRUE, NULL, NOW(), NOW()),
(UUID(), '1-2500', 'Akumulasi Penyusutan', 'ASSET', 'Fixed Assets', 'Akumulasi penyusutan aset tetap', TRUE, NULL, NOW(), NOW());

-- LIABILITIES (2-xxxx)
INSERT INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
-- Current Liabilities
(UUID(), '2-0000', 'KEWAJIBAN LANCAR', 'LIABILITY', 'Current Liabilities', 'Kewajiban jangka pendek (< 1 tahun)', TRUE, NULL, NOW(), NOW()),
(UUID(), '2-1000', 'Utang Usaha', 'LIABILITY', 'Current Liabilities', 'Utang kepada pemasok', TRUE, NULL, NOW(), NOW()),
(UUID(), '2-1100', 'Utang Pajak', 'LIABILITY', 'Current Liabilities', 'Kewajiban pajak yang belum dibayar', TRUE, NULL, NOW(), NOW()),
(UUID(), '2-1200', 'Utang Gaji', 'LIABILITY', 'Current Liabilities', 'Gaji karyawan yang belum dibayar', TRUE, NULL, NOW(), NOW()),
(UUID(), '2-1300', 'Utang Bank Jangka Pendek', 'LIABILITY', 'Current Liabilities', 'Pinjaman bank jatuh tempo < 1 tahun', TRUE, NULL, NOW(), NOW()),

-- Long-term Liabilities
(UUID(), '2-2000', 'KEWAJIBAN JANGKA PANJANG', 'LIABILITY', 'Long-term Liabilities', 'Kewajiban jangka panjang (> 1 tahun)', TRUE, NULL, NOW(), NOW()),
(UUID(), '2-2100', 'Utang Bank Jangka Panjang', 'LIABILITY', 'Long-term Liabilities', 'Pinjaman bank jatuh tempo > 1 tahun', TRUE, NULL, NOW(), NOW());

-- EQUITY (3-xxxx)
INSERT INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
(UUID(), '3-0000', 'EKUITAS', 'EQUITY', 'Equity', 'Modal pemilik perusahaan', TRUE, NULL, NOW(), NOW()),
(UUID(), '3-1000', 'Modal', 'EQUITY', 'Capital', 'Modal disetor pemilik', TRUE, NULL, NOW(), NOW()),
(UUID(), '3-2000', 'Laba Ditahan', 'EQUITY', 'Retained Earnings', 'Akumulasi laba yang tidak dibagikan', TRUE, NULL, NOW(), NOW()),
(UUID(), '3-3000', 'Prive', 'EQUITY', 'Drawings', 'Pengambilan pribadi pemilik', TRUE, NULL, NOW(), NOW());

-- REVENUE (4-xxxx)
INSERT INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
(UUID(), '4-0000', 'PENDAPATAN', 'REVENUE', 'Revenue', 'Pendapatan dari aktivitas usaha', TRUE, NULL, NOW(), NOW()),
(UUID(), '4-1000', 'Pendapatan Usaha', 'REVENUE', 'Operating Revenue', 'Pendapatan dari penjualan produk/jasa', TRUE, NULL, NOW(), NOW()),
(UUID(), '4-2000', 'Pendapatan Lain-lain', 'REVENUE', 'Other Revenue', 'Pendapatan di luar usaha utama', TRUE, NULL, NOW(), NOW()),
(UUID(), '4-2100', 'Pendapatan Bunga', 'REVENUE', 'Other Revenue', 'Bunga dari deposito atau investasi', TRUE, NULL, NOW(), NOW());

-- EXPENSES (5-xxxx)
INSERT INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
(UUID(), '5-0000', 'BEBAN', 'EXPENSE', 'Expenses', 'Beban operasional perusahaan', TRUE, NULL, NOW(), NOW()),
(UUID(), '5-1000', 'Beban Gaji', 'EXPENSE', 'Operating Expense', 'Gaji dan tunjangan karyawan', TRUE, NULL, NOW(), NOW()),
(UUID(), '5-1100', 'Beban Sewa', 'EXPENSE', 'Operating Expense', 'Sewa kantor atau tempat usaha', TRUE, NULL, NOW(), NOW()),
(UUID(), '5-1200', 'Beban Listrik', 'EXPENSE', 'Operating Expense', 'Tagihan listrik', TRUE, NULL, NOW(), NOW()),
(UUID(), '5-1300', 'Beban Air', 'EXPENSE', 'Operating Expense', 'Tagihan air', TRUE, NULL, NOW(), NOW()),
(UUID(), '5-1400', 'Beban Telepon & Internet', 'EXPENSE', 'Operating Expense', 'Tagihan komunikasi', TRUE, NULL, NOW(), NOW()),
(UUID(), '5-1500', 'Beban Perlengkapan', 'EXPENSE', 'Operating Expense', 'Pembelian perlengkapan kantor', TRUE, NULL, NOW(), NOW()),
(UUID(), '5-1600', 'Beban Transportasi', 'EXPENSE', 'Operating Expense', 'Biaya transportasi operasional', TRUE, NULL, NOW(), NOW()),
(UUID(), '5-1700', 'Beban Pemeliharaan', 'EXPENSE', 'Operating Expense', 'Pemeliharaan aset dan fasilitas', TRUE, NULL, NOW(), NOW()),
(UUID(), '5-1800', 'Beban Penyusutan', 'EXPENSE', 'Operating Expense', 'Penyusutan aset tetap', TRUE, NULL, NOW(), NOW()),
(UUID(), '5-2000', 'Beban Pajak', 'EXPENSE', 'Tax Expense', 'Beban pajak penghasilan', TRUE, NULL, NOW(), NOW()),
(UUID(), '5-3000', 'Beban Lain-lain', 'EXPENSE', 'Other Expense', 'Beban di luar operasional utama', TRUE, NULL, NOW(), NOW());
