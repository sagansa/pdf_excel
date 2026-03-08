from sqlalchemy import text


def build_general_ledger_entries_query(mark_coa_join, company_filter="", coretax_filter="", coa_filter=""):
    return text(f"""
        SELECT
            t.id AS transaction_id,
            t.txn_date,
            t.description,
            t.amount,
            t.db_cr,
            m.id AS mark_id,
            COALESCE(NULLIF(TRIM(m.personal_use), ''), NULLIF(TRIM(m.internal_report), ''), NULLIF(TRIM(m.tax_report), ''), '(Unnamed Mark)') AS mark_name,
            coa.code AS coa_code,
            coa.name AS coa_name,
            coa.category AS coa_category,
            mcm.mapping_type,
            (CASE
                WHEN mcm.mapping_type = 'DEBIT' THEN t.amount
                WHEN mcm.mapping_type = 'CREDIT' THEN -t.amount
                ELSE 0
            END)
            * (CASE
                WHEN m.natural_direction IS NOT NULL
                     AND UPPER(TRIM(COALESCE(t.db_cr, ''))) != ''
                     AND (
                        (UPPER(m.natural_direction) = 'DB' AND UPPER(TRIM(t.db_cr)) IN ('CR', 'CREDIT', 'K', 'KREDIT'))
                        OR
                        (UPPER(m.natural_direction) = 'CR' AND UPPER(TRIM(t.db_cr)) IN ('DB', 'DEBIT', 'D', 'DE'))
                     )
                THEN 0 ELSE 1
            END) AS signed_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
          {company_filter}
          {coretax_filter}
          {coa_filter}
        ORDER BY t.txn_date, t.id, mcm.mapping_type
    """)


def build_general_ledger_summary_query(mark_coa_join, company_filter="", coretax_filter=""):
    return text(f"""
        SELECT
            coa.code AS coa_code,
            coa.name AS coa_name,
            coa.category AS coa_category,
            SUM(
                (CASE
                    WHEN mcm.mapping_type = 'DEBIT' THEN t.amount
                    WHEN mcm.mapping_type = 'CREDIT' THEN -t.amount
                    ELSE 0
                END)
                * (CASE
                    WHEN m.natural_direction IS NOT NULL
                         AND UPPER(TRIM(COALESCE(t.db_cr, ''))) != ''
                         AND (
                            (UPPER(m.natural_direction) = 'DB' AND UPPER(TRIM(t.db_cr)) IN ('CR', 'CREDIT', 'K', 'KREDIT'))
                            OR
                            (UPPER(m.natural_direction) = 'CR' AND UPPER(TRIM(t.db_cr)) IN ('DB', 'DEBIT', 'D', 'DE'))
                         )
                    THEN 0 ELSE 1
                END)
            ) AS balance,
            SUM(CASE WHEN mcm.mapping_type = 'DEBIT' THEN t.amount ELSE 0 END) AS total_debit,
            SUM(CASE WHEN mcm.mapping_type = 'CREDIT' THEN t.amount ELSE 0 END) AS total_credit,
            COUNT(DISTINCT t.id) AS transaction_count
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
          {company_filter}
          {coretax_filter}
        GROUP BY coa.code, coa.name, coa.category
        HAVING balance != 0
        ORDER BY coa.code
    """)
