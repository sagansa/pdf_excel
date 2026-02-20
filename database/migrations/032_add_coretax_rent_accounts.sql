-- Migration 032: Ensure Coretax rent/prepaid/tax accounts exist
-- Required defaults for rental contract + PPh 4(2) flow:
-- 1135 (Prepaid Rent), 2141 (PPh Final 4(2) Payable), 5105 (Rent Expense)

INSERT IGNORE INTO chart_of_accounts
    (id, code, name, category, subcategory, description, is_active, created_at, updated_at)
VALUES
    (UUID(), '1135', 'Biaya Dibayar Dimuka', 'ASSET', 'Current Assets', 'Prepaid Expenses - Rent', TRUE, NOW(), NOW()),
    (UUID(), '2141', 'Utang PPh Final Pasal 4(2)', 'LIABILITY', 'Current Liabilities', 'PPh Final Article 4(2) Payable', TRUE, NOW(), NOW()),
    (UUID(), '5105', 'Beban Sewa', 'EXPENSE', 'Operating Expenses', 'Rent Expense', TRUE, NOW(), NOW());
