import re

# Read the file
with open('backend/services/report_service.py', 'r') as f:
    content = f.read()

# Fix Balance Sheet query (around line 988-1005)
old_bs_query = """WITH coa_balances AS (
            SELECT 
                mcm.coa_id,
                SUM(
                    CASE
                        -- Match transaction db_cr with mapping_type
                        -- DEBIT mapping for DB transactions, CREDIT mapping for CR transactions
                        WHEN t.db_cr = 'DB' AND UPPER(COALESCE(mcm.mapping_type, '')) = 'DEBIT' THEN t.amount
                        WHEN t.db_cr = 'CR' AND UPPER(COALESCE(mcm.mapping_type, '')) = 'CREDIT' THEN -t.amount
                        ELSE 0
                    END
                ) as total_amount
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
            WHERE t.txn_date <= :as_of_date
                AND (:company_id IS NULL OR t.company_id = :company_id)
                {split_exclusion_clause}
                {coretax_clause}
                -- Ensure we only use the mapping that matches the transaction direction
                AND (
                    (t.db_cr = 'DB' AND UPPER(COALESCE(mcm.mapping_type, '')) = 'DEBIT')
                    OR (t.db_cr = 'CR' AND UPPER(COALESCE(mcm.mapping_type, '')) = 'CREDIT')
                )
            GROUP BY mcm.coa_id
        )"""

new_bs_query = """WITH coa_balances AS (
            SELECT 
                mcm.coa_id,
                SUM(
                    CASE
                        -- CR = positive (money in), DB = negative (money out)
                        -- This ensures marks with mixed DB/CR will net out correctly
                        WHEN t.db_cr = 'CR' THEN t.amount
                        WHEN t.db_cr = 'DB' THEN -t.amount
                        ELSE 0
                    END
                ) as total_amount
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
            WHERE t.txn_date <= :as_of_date
                AND (:company_id IS NULL OR t.company_id = :company_id)
                {split_exclusion_clause}
                {coretax_clause}
            GROUP BY mcm.coa_id
        )"""

content = content.replace(old_bs_query, new_bs_query)

# Write the file
with open('backend/services/report_service.py', 'w') as f:
    f.write(content)

print("Fixed Balance Sheet query successfully!")
