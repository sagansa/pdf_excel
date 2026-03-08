from sqlalchemy import text


def build_available_years_query(year_expr, split_exclusion):
    return text(f"""
        SELECT DISTINCT {year_expr} AS year
        FROM transactions t
        WHERE t.txn_date IS NOT NULL
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion}
        ORDER BY year DESC
    """)


def build_coa_detail_query(npwp_expr, method_expr, split_exclusion):
    return text(f"""
        SELECT
            t.id, t.txn_date, t.description, t.amount, t.db_cr,
            m.personal_use as mark_name, m.is_service, c.name as company_name, mcm.mapping_type,
            {npwp_expr} AS service_npwp,
            {method_expr} AS service_calculation_method
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        LEFT JOIN companies c ON t.company_id = c.id
        WHERE mcm.coa_id = :coa_id
          AND (:start_date IS NULL OR t.txn_date >= :start_date)
          AND (:end_date IS NULL OR t.txn_date <= :end_date)
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion}
        ORDER BY t.txn_date DESC
    """)


def build_marks_summary_query():
    return text("""
        SELECT
            m.id as mark_id,
            m.personal_use as mark_name,
            SUM(CASE
                WHEN t.db_cr = 'CR' THEN t.amount
                WHEN t.db_cr = 'DB' THEN 0
                ELSE 0
            END) as total_debit,
            SUM(CASE
                WHEN t.db_cr = 'DB' THEN t.amount
                WHEN t.db_cr = 'CR' THEN 0
                ELSE 0
            END) as total_credit,
            COUNT(t.id) as transaction_count
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        WHERE t.txn_date >= :start_date AND t.txn_date <= :end_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
        GROUP BY m.id, m.personal_use
        ORDER BY mark_name ASC
    """)
