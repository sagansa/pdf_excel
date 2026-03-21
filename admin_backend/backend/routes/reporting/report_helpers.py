from datetime import datetime

from sqlalchemy import text

from backend.errors import BadRequestError, NotFoundError
from backend.routes.accounting_utils import serialize_row_values


def default_report_period(start_date, end_date):
    now = datetime.now()
    return (
        start_date or f"{now.year}-01-01",
        end_date or now.strftime('%Y-%m-%d')
    )


def parse_year_or_default(raw_year):
    if not raw_year:
        return datetime.now().year
    try:
        return int(raw_year)
    except (TypeError, ValueError):
        raise BadRequestError('year must be numeric')


def get_first_active_coa_id(conn):
    first_coa = conn.execute(text("""
        SELECT id
        FROM chart_of_accounts
        WHERE is_active = TRUE
        LIMIT 1
    """)).fetchone()
    if not first_coa:
        raise BadRequestError('coa_id is required')
    return first_coa[0]


def get_coa_or_404(conn, coa_id):
    coa_row = conn.execute(
        text("SELECT * FROM chart_of_accounts WHERE id = :id"),
        {'id': coa_id}
    ).fetchone()
    if not coa_row:
        raise NotFoundError('COA not found')
    return serialize_row_values(coa_row._mapping)


def resolve_coa_detail_period(coa_category, as_of_date, start_date, end_date):
    if as_of_date:
        if coa_category in ('ASSET', 'LIABILITY', 'EQUITY'):
            return None, as_of_date
        as_of_year = datetime.strptime(as_of_date, '%Y-%m-%d').year
        return f"{as_of_year}-01-01", as_of_date
    return default_report_period(start_date, end_date)

def calculate_coa_effective_amount(coa_category, amount, db_cr, mapping_type):
    if coa_category in ('ASSET', 'LIABILITY', 'EQUITY'):
        return amount if mapping_type == 'DEBIT' else -amount
    if (db_cr == 'CR' and mapping_type == 'CREDIT') or (db_cr == 'DB' and mapping_type == 'DEBIT'):
        return amount
    return -amount


def apply_service_tax_adjustment(row, coa_category):
    if coa_category not in ('EXPENSE', 'REVENUE'):
        return row

    is_service = str(row.get('is_service', '0')).lower() in ('1', 'true', 'yes', 'y')
    has_npwp_col = row.get('service_npwp') is not None
    if not (is_service or has_npwp_col):
        return row

    npwp_digits = ''.join(ch for ch in str(row.get('service_npwp') or '') if ch.isdigit())
    has_npwp = len(npwp_digits) == 15
    tax_rate = 2.0 if has_npwp else 4.0
    amount_abs = abs(float(row['amount']))
    method = str(row.get('service_calculation_method') or 'BRUTO').strip().upper()

    if method == 'NETTO':
        divisor = max(0.000001, 1.0 - (tax_rate / 100.0))
        tax_to_add = (amount_abs / divisor) - amount_abs
    else:
        tax_to_add = amount_abs * (tax_rate / 100.0)

    if tax_to_add <= 0:
        return row

    row['effective_amount'] += tax_to_add if row['effective_amount'] >= 0 else -tax_to_add
    row['amount'] = float(row['amount']) + (tax_to_add if row['amount'] >= 0 else -tax_to_add)
    return row
def get_reporting_start_date(conn, company_id, report_type='real'):
    if not company_id:
        return None
        
    res = conn.execute(text("""
        SELECT start_year
        FROM initial_capital_settings
        WHERE company_id = :company_id AND report_type = :report_type
        LIMIT 1
    """), {'company_id': company_id, 'report_type': report_type}).fetchone()
    
    if res and res.start_year:
        return f"{res.start_year}-01-01"
    return None
