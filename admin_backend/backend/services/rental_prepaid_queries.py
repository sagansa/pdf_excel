from sqlalchemy import text


def build_contract_lookup_query(store_name_sql):
    return text(f"""
        SELECT
            c.*,
            {store_name_sql} AS store_name,
            l.location_name
        FROM rental_contracts c
        LEFT JOIN rental_stores s ON c.store_id = s.id
        LEFT JOIN rental_locations l ON c.location_id = l.id
        WHERE c.id = :id
          AND (:company_id IS NULL OR c.company_id = :company_id)
        LIMIT 1
    """)


def build_contract_payment_stats_query():
    return text("""
        SELECT
            COUNT(*) AS txn_count,
            COALESCE(SUM(ABS(amount)), 0) AS total_paid,
            MIN(txn_date) AS first_payment_date
        FROM transactions
        WHERE rental_contract_id = :contract_id
    """)


def build_existing_prepaid_by_contract_query():
    return text("""
        SELECT *
        FROM prepaid_expenses
        WHERE contract_id = :contract_id
        ORDER BY updated_at DESC
        LIMIT 1
    """)


def build_existing_prepaid_by_id_query():
    return text("""
        SELECT *
        FROM prepaid_expenses
        WHERE id = :id
        LIMIT 1
    """)


def build_update_prepaid_query(set_clause):
    return text(f"""
        UPDATE prepaid_expenses
        SET {set_clause}
        WHERE id = :id
    """)


def build_insert_prepaid_query(columns_sql, values_sql):
    return text(f"""
        INSERT INTO prepaid_expenses ({columns_sql})
        VALUES ({values_sql})
    """)


def build_update_contract_query(update_sql):
    return text(f"""
        UPDATE rental_contracts
        SET {update_sql}
        WHERE id = :id
    """)
