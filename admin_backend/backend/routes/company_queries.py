from sqlalchemy import text


def get_companies_query():
    return text("SELECT * FROM companies ORDER BY name ASC")


def insert_company_query():
    return text("""
        INSERT INTO companies (id, name, short_name, created_at, updated_at)
        VALUES (:id, :name, :short_name, :now, :now)
    """)


def update_company_query():
    return text("""
        UPDATE companies
        SET name = :name, short_name = :short_name, updated_at = :now
        WHERE id = :id
    """)


def clear_company_transactions_query():
    return text("UPDATE transactions SET company_id = NULL WHERE company_id = :cid")


def delete_company_query():
    return text("DELETE FROM companies WHERE id = :id")


def get_view_filters_query():
    return text("SELECT filters FROM user_filters WHERE view_name = :view")


def upsert_view_filters_query(now_expr):
    return text(f"""
        INSERT INTO user_filters (view_name, filters)
        VALUES (:view, :filters)
        ON DUPLICATE KEY UPDATE filters = :filters, updated_at = {now_expr}
    """)
