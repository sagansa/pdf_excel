-- Add CoreTax 2025 specific accounts based on user requirements

-- REVENUE DEDUCTIONS (Contra-Revenue)
-- User should map these with mapping_type = 'DEBIT' to reduce total revenue
INSERT IGNORE INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
('4011-uuid', '4011', 'Retur Penjualan', 'REVENUE', 'Sales Deductions', 'Pengembalian barang dari pelanggan (Contra Revenue)', TRUE, NULL, NOW(), NOW()),
('4012-uuid', '4012', 'Potongan Penjualan', 'REVENUE', 'Sales Deductions', 'Diskon atau potongan harga penjualan (Contra Revenue)', TRUE, NULL, NOW(), NOW()),
('4013-uuid', '4013', 'Penyesuaian Penjualan', 'REVENUE', 'Sales Deductions', 'Penyesuaian harga jual (Contra Revenue)', TRUE, NULL, NOW(), NOW());

-- COST OF GOODS SOLD (HPP) - Categorized as EXPENSE for now as simplistic model
INSERT IGNORE INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
(UUID(), '5001', 'Pembelian', 'EXPENSE', 'Cost of Goods Sold', 'Pembelian barang dagang', TRUE, NULL, NOW(), NOW()),
(UUID(), '5003', 'Beban Pengangkutan', 'EXPENSE', 'Cost of Goods Sold', 'Biaya angkut pembelian', TRUE, NULL, NOW(), NOW()),
(UUID(), '5007', 'Beban Operasional Lainnya', 'EXPENSE', 'Cost of Goods Sold', 'Biaya terkait HPP lainnya', TRUE, NULL, NOW(), NOW()),
(UUID(), '5008', 'Persediaan - Awal', 'EXPENSE', 'Cost of Goods Sold', 'Nilai persediaan awal periode', TRUE, NULL, NOW(), NOW()),
(UUID(), '5009', 'Persediaan - Akhir', 'EXPENSE', 'Cost of Goods Sold', 'Nilai persediaan akhir periode (Contra Expense)', TRUE, NULL, NOW(), NOW());

-- OPERATING EXPENSES (Beban Usaha) - Specific CoreTax Codes
INSERT IGNORE INTO chart_of_accounts (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at) VALUES
(UUID(), '5313', 'Beban Transportasi', 'EXPENSE', 'Operating Expenses', 'Biaya transportasi dinas', TRUE, NULL, NOW(), NOW()),
(UUID(), '5314', 'Beban Penyusutan dan Amortisasi', 'EXPENSE', 'Operating Expenses', 'Penyusutan aset tetap dan amortisasi', TRUE, NULL, NOW(), NOW()),
(UUID(), '5315', 'Beban Sewa', 'EXPENSE', 'Operating Expenses', 'Sewa gedung/kantor', TRUE, NULL, NOW(), NOW()),
(UUID(), '5316', 'Beban Bunga', 'EXPENSE', 'Operating Expenses', 'Bunga pinjaman', TRUE, NULL, NOW(), NOW()),
(UUID(), '5317', 'Beban Sehubungan dengan Jasa', 'EXPENSE', 'Operating Expenses', 'Biaya jasa profesional/teknik', TRUE, NULL, NOW(), NOW()),
(UUID(), '5318', 'Beban Penurunan Nilai', 'EXPENSE', 'Operating Expenses', 'Impairment loss', TRUE, NULL, NOW(), NOW()),
(UUID(), '5319', 'Beban Royalti', 'EXPENSE', 'Operating Expenses', 'Biaya royalti', TRUE, NULL, NOW(), NOW()),
(UUID(), '5320', 'Beban Pemasaran atau Promosi', 'EXPENSE', 'Operating Expenses', 'Biaya marketing dan iklan', TRUE, NULL, NOW(), NOW()),
(UUID(), '5321', 'Beban Entertainment', 'EXPENSE', 'Operating Expenses', 'Biaya reprentasi/jamuan', TRUE, NULL, NOW(), NOW()),
(UUID(), '5322', 'Beban Umum dan Administrasi', 'EXPENSE', 'Operating Expenses', 'Biaya admin kantor', TRUE, NULL, NOW(), NOW()),
(UUID(), '5399', 'Beban usaha lainnya', 'EXPENSE', 'Operating Expenses', 'Biaya operasional lain-lain', TRUE, NULL, NOW(), NOW());
