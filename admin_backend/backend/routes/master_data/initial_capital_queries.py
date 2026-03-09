from sqlalchemy import text


def get_initial_capital_by_company_query():
    return text("""
        SELECT id, company_id, amount, previous_retained_earnings_amount, start_year, description, created_at, updated_at
        FROM initial_capital_settings
        WHERE company_id = :company_id
    """)


def get_initial_capital_id_by_company_query():
    return text("""
        SELECT id
        FROM initial_capital_settings
        WHERE company_id = :company_id
    """)


def update_initial_capital_query(now_expr):
    return text(f"""
        UPDATE initial_capital_settings
        SET amount = :amount,
            previous_retained_earnings_amount = :previous_retained_earnings_amount,
            start_year = :start_year,
            description = :description,
            updated_at = {now_expr}
        WHERE company_id = :company_id
    """)


def insert_initial_capital_query(now_expr):
    return text(f"""
        INSERT INTO initial_capital_settings
        (id, company_id, amount, previous_retained_earnings_amount, start_year, description, created_at, updated_at)
        VALUES (:id, :company_id, :amount, :previous_retained_earnings_amount, :start_year, :description, {now_expr}, {now_expr})
    """)


def delete_initial_capital_by_company_query():
    return text("""
        DELETE FROM initial_capital_settings
        WHERE company_id = :company_id
    """)
