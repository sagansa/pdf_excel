from sqlalchemy import text
from backend.services.reporting.report_sql_fragments import (
    _effective_coa_id_expr,
    _effective_mapping_type_expr,
    _effective_natural_direction_expr,
)


def build_general_ledger_entries_query(conn, mark_coa_join, company_filter="", coretax_filter="", coa_filter="", report_type='real'):
    effective_coa_id = _effective_coa_id_expr(conn, report_type, txn_alias='t', mapping_alias='mcm')
    effective_mapping_type = _effective_mapping_type_expr(conn, report_type, txn_alias='t', mapping_alias='mcm')
    effective_natural_direction = _effective_natural_direction_expr(conn, report_type, txn_alias='t', mark_alias='m')
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
            {effective_mapping_type} AS mapping_type,
            (CASE
                WHEN {effective_mapping_type} = 'DEBIT' THEN t.amount
                WHEN {effective_mapping_type} = 'CREDIT' THEN -t.amount
                ELSE 0
            END)
            * (CASE
                WHEN {effective_natural_direction} IS NOT NULL
                     AND UPPER(TRIM(COALESCE(t.db_cr, ''))) != ''
                     AND (
                        (UPPER({effective_natural_direction}) = 'DB' AND UPPER(TRIM(t.db_cr)) IN ('CR', 'CREDIT', 'K', 'KREDIT'))
                        OR
                        (UPPER({effective_natural_direction}) = 'CR' AND UPPER(TRIM(t.db_cr)) IN ('DB', 'DEBIT', 'D', 'DE'))
                     )
                THEN 0 ELSE 1
            END) AS signed_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        INNER JOIN chart_of_accounts coa ON {effective_coa_id} = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
          {company_filter}
          {coretax_filter}
          {coa_filter}
        ORDER BY t.txn_date, t.id, {effective_mapping_type}
    """)


def build_general_ledger_summary_query(conn, mark_coa_join, company_filter="", coretax_filter="", report_type='real'):
    effective_coa_id = _effective_coa_id_expr(conn, report_type, txn_alias='t', mapping_alias='mcm')
    effective_mapping_type = _effective_mapping_type_expr(conn, report_type, txn_alias='t', mapping_alias='mcm')
    effective_natural_direction = _effective_natural_direction_expr(conn, report_type, txn_alias='t', mark_alias='m')
    return text(f"""
        SELECT
            coa.code AS coa_code,
            coa.name AS coa_name,
            coa.category AS coa_category,
            SUM(
                (CASE
                    WHEN {effective_mapping_type} = 'DEBIT' THEN t.amount
                    WHEN {effective_mapping_type} = 'CREDIT' THEN -t.amount
                    ELSE 0
                END)
                * (CASE
                    WHEN {effective_natural_direction} IS NOT NULL
                         AND UPPER(TRIM(COALESCE(t.db_cr, ''))) != ''
                         AND (
                            (UPPER({effective_natural_direction}) = 'DB' AND UPPER(TRIM(t.db_cr)) IN ('CR', 'CREDIT', 'K', 'KREDIT'))
                            OR
                            (UPPER({effective_natural_direction}) = 'CR' AND UPPER(TRIM(t.db_cr)) IN ('DB', 'DEBIT', 'D', 'DE'))
                         )
                    THEN 0 ELSE 1
                END)
            ) AS balance,
            SUM(CASE WHEN {effective_mapping_type} = 'DEBIT' THEN t.amount ELSE 0 END) AS total_debit,
            SUM(CASE WHEN {effective_mapping_type} = 'CREDIT' THEN t.amount ELSE 0 END) AS total_credit,
            COUNT(DISTINCT t.id) AS transaction_count
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        INNER JOIN chart_of_accounts coa ON {effective_coa_id} = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
          {company_filter}
          {coretax_filter}
        GROUP BY coa.code, coa.name, coa.category
        HAVING balance != 0
        ORDER BY coa.code
    """)
