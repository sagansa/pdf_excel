from sqlalchemy import bindparam, text


def build_filter_rent_transaction_ids_query():
    return text("""
        SELECT DISTINCT t.id
        FROM transactions t
        LEFT JOIN marks m ON t.mark_id = m.id
        WHERE t.id IN :txn_ids
          AND (
            :company_id IS NULL
            OR t.company_id = :company_id
            OR t.company_id IS NULL
          )
          AND (
            LOWER(COALESCE(m.personal_use, '')) LIKE '%%sewa tempat%%'
            OR LOWER(COALESCE(m.internal_report, '')) LIKE '%%sewa tempat%%'
            OR LOWER(COALESCE(m.tax_report, '')) LIKE '%%sewa tempat%%'
            OR LOWER(COALESCE(m.personal_use, '')) LIKE '%%sewa%%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%%sewa%%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%%rent%%'
            OR COALESCE(m.is_rental, 0) = 1
            OR EXISTS (
              SELECT 1
              FROM mark_coa_mapping mcm
              INNER JOIN chart_of_accounts coa ON coa.id = mcm.coa_id
              WHERE mcm.mark_id = t.mark_id
                AND coa.code IN ('5315', '5105')
            )
          )
    """).bindparams(bindparam('txn_ids', expanding=True))


def build_locations_query():
    return text("""
        SELECT l.*, c.name AS company_name
        FROM rental_locations l
        LEFT JOIN companies c ON l.company_id = c.id
        WHERE (:company_id IS NULL OR l.company_id = :company_id)
        ORDER BY l.location_name
    """)


def build_stores_query(store_name_expr, store_code_expr, location_join):
    return text(f"""
        SELECT
            s.*,
            {store_name_expr} AS store_name,
            {store_code_expr} AS store_code,
            l.location_name
        FROM rental_stores s
        {location_join}
        WHERE (:company_id IS NULL OR s.company_id = :company_id)
        ORDER BY {store_name_expr} ASC
    """)


def build_contracts_query(
    calculation_method_sql,
    pph42_rate_sql,
    pph42_timing_sql,
    pph42_date_sql,
    pph42_ref_sql,
    store_name_sql,
    store_code_sql,
):
    return text(f"""
        SELECT
            c.*,
            {store_name_sql} AS store_name,
            {store_code_sql} AS store_code,
            l.location_name,
            l.address AS location_address,
            COALESCE(txn.txn_count, 0) AS transaction_count,
            COALESCE(txn.total_paid, 0) AS total_paid,
            {calculation_method_sql} AS calculation_method,
            {pph42_rate_sql} AS pph42_rate,
            {pph42_timing_sql} AS pph42_payment_timing,
            {pph42_date_sql} AS pph42_payment_date,
            {pph42_ref_sql} AS pph42_payment_ref
        FROM rental_contracts c
        LEFT JOIN rental_stores s ON c.store_id = s.id
        LEFT JOIN rental_locations l ON c.location_id = l.id
        LEFT JOIN (
            SELECT
                rental_contract_id,
                COUNT(*) AS txn_count,
                COALESCE(SUM(ABS(amount)), 0) AS total_paid
            FROM transactions
            WHERE rental_contract_id IS NOT NULL
            GROUP BY rental_contract_id
        ) txn ON txn.rental_contract_id = c.id
        WHERE (:company_id IS NULL OR c.company_id = :company_id)
          AND (:status IS NULL OR c.status = :status)
        ORDER BY c.start_date DESC, c.created_at DESC
    """)


def build_expiring_contracts_query_sqlite(store_name_sql):
    return text(f"""
        SELECT c.*, {store_name_sql} AS store_name
        FROM rental_contracts c
        LEFT JOIN rental_stores s ON c.store_id = s.id
        WHERE (:company_id IS NULL OR c.company_id = :company_id)
          AND c.status = 'active'
          AND date(c.end_date) <= date('now', :window)
        ORDER BY c.end_date ASC
    """)


def build_expiring_contracts_query_default(store_name_sql):
    return text(f"""
        SELECT c.*, {store_name_sql} AS store_name
        FROM rental_contracts c
        LEFT JOIN rental_stores s ON c.store_id = s.id
        WHERE (:company_id IS NULL OR c.company_id = :company_id)
          AND c.status = 'active'
          AND c.end_date <= DATE_ADD(CURDATE(), INTERVAL :days DAY)
        ORDER BY c.end_date ASC
    """)


def build_contract_transactions_query():
    return text("""
        SELECT
            t.*,
            m.personal_use,
            m.internal_report,
            m.tax_report
        FROM transactions t
        LEFT JOIN marks m ON t.mark_id = m.id
        WHERE t.rental_contract_id = :contract_id
        ORDER BY t.txn_date DESC, t.created_at DESC
    """)


def build_linkable_transactions_query():
    return text("""
        SELECT
            t.*,
            m.personal_use,
            m.internal_report,
            m.tax_report
        FROM transactions t
        LEFT JOIN marks m ON t.mark_id = m.id
        WHERE (
              :company_id IS NULL
              OR t.company_id = :company_id
              OR (t.rental_contract_id = :current_contract_id)
          )
          AND (t.rental_contract_id IS NULL OR t.rental_contract_id = :current_contract_id)
          AND (
              t.rental_contract_id = :current_contract_id
              OR
              LOWER(COALESCE(m.personal_use, '')) LIKE '%%sewa tempat%%'
              OR LOWER(COALESCE(m.internal_report, '')) LIKE '%%sewa tempat%%'
              OR LOWER(COALESCE(m.tax_report, '')) LIKE '%%sewa tempat%%'
              OR LOWER(COALESCE(m.personal_use, '')) LIKE '%%sewa%%'
              OR LOWER(COALESCE(t.description, '')) LIKE '%%sewa%%'
              OR LOWER(COALESCE(t.description, '')) LIKE '%%rent%%'
              OR COALESCE(m.is_rental, 0) = 1
              OR EXISTS (
                  SELECT 1
                  FROM mark_coa_mapping mcm
                  INNER JOIN chart_of_accounts coa ON coa.id = mcm.coa_id
                  WHERE mcm.mark_id = t.mark_id
                    AND coa.code IN ('5315', '5105')
              )
          )
        ORDER BY t.txn_date DESC, t.created_at DESC
    """)
