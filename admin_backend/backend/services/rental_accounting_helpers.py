from sqlalchemy import text

from backend.db.schema import get_table_columns


def get_supported_table_columns(conn, table_name):
    allowed_tables = {
        'rental_contracts',
        'rental_stores',
        'rental_locations',
        'prepaid_expenses',
        'chart_of_accounts',
        'amortization_settings',
    }
    return get_table_columns(conn, table_name, allowed_tables=allowed_tables)


def get_setting_value(conn, company_id, setting_name):
    row = conn.execute(text("""
        SELECT setting_value
        FROM amortization_settings
        WHERE setting_name = :setting_name
          AND (company_id = :company_id OR company_id IS NULL)
        ORDER BY company_id DESC
        LIMIT 1
    """), {
        'setting_name': setting_name,
        'company_id': company_id,
    }).fetchone()
    return row[0] if row else None


def resolve_coa_by_setting(conn, company_id, setting_name, fallback_codes):
    if isinstance(fallback_codes, str):
        fallback_codes = [fallback_codes]
    fallback_codes = [str(code) for code in (fallback_codes or []) if str(code).strip()]

    value = get_setting_value(conn, company_id, setting_name)
    coa_row = None

    if value:
        coa_row = conn.execute(text("""
            SELECT id, code, name
            FROM chart_of_accounts
            WHERE id = :value OR code = :value
            LIMIT 1
        """), {'value': str(value)}).fetchone()

    if not coa_row and fallback_codes:
        for code in fallback_codes:
            coa_row = conn.execute(text("""
                SELECT id, code, name
                FROM chart_of_accounts
                WHERE code = :code
                LIMIT 1
            """), {'code': code}).fetchone()
            if coa_row:
                break

    if not coa_row:
        fallback = fallback_codes[0] if fallback_codes else None
        return {'id': None, 'code': fallback, 'name': fallback}

    return {
        'id': coa_row.id,
        'code': coa_row.code,
        'name': coa_row.name,
    }


def resolve_cash_account(conn, company_id=None):
    value = get_setting_value(conn, company_id, 'rental_cash_coa')
    if value:
        row = conn.execute(text("""
            SELECT id, code, name
            FROM chart_of_accounts
            WHERE id = :val OR code = :val
            LIMIT 1
        """), {'val': str(value)}).fetchone()
        if row:
            return {'id': row.id, 'code': row.code, 'name': row.name}

    for code in ('1111', '1101', '1102', '1100'):
        row = conn.execute(text("""
            SELECT id, code, name
            FROM chart_of_accounts
            WHERE code = :code
            LIMIT 1
        """), {'code': code}).fetchone()
        if row:
            return {'id': row.id, 'code': row.code, 'name': row.name}

    return {'id': None, 'code': 'CASH', 'name': 'Kas/Bank'}
