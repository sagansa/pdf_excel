from sqlalchemy import text

from backend.db.schema import get_table_columns
from backend.services.report_sql_fragments import (
    _coretax_filter_clause,
    _mark_coa_join_clause,
    _split_parent_exclusion_clause,
)
from backend.services.report_value_utils import (
    _parse_date,
    _to_float,
)


def _service_tax_rate_and_amount(amount, npwp_value, method):
    npwp_digits = ''.join(ch for ch in str(npwp_value or '') if ch.isdigit())
    has_npwp = len(npwp_digits) == 15
    tax_rate = 2.0 if has_npwp else 4.0
    amount_base = abs(_to_float(amount, 0.0))
    method = str(method or 'BRUTO').strip().upper()
    if method not in {'BRUTO', 'NETTO', 'NONE'}:
        method = 'BRUTO'
    if method == 'NONE':
        return tax_rate, 0.0
    if method == 'NETTO':
        divisor = max(0.000001, 1.0 - (tax_rate / 100.0))
        bruto = amount_base / divisor
        return tax_rate, max(0.0, bruto - amount_base)
    return tax_rate, amount_base * (tax_rate / 100.0)


def _resolve_service_tax_payable_account(conn, company_id=None, preferred_setting=None):
    setting_candidates = ['service_tax_payable_coa', 'prepaid_tax_payable_coa']
    if preferred_setting and preferred_setting in setting_candidates:
        setting_candidates.remove(preferred_setting)
        setting_candidates.insert(0, preferred_setting)

    try:
        settings_columns = get_table_columns(conn, 'amortization_settings')
    except Exception:
        settings_columns = set()

    if settings_columns:
        for setting_name in setting_candidates:
            setting_row = conn.execute(text("""
                SELECT setting_value
                FROM amortization_settings
                WHERE setting_name = :setting_name
                  AND (company_id = :company_id OR company_id IS NULL)
                ORDER BY company_id DESC
                LIMIT 1
            """), {'setting_name': setting_name, 'company_id': company_id}).fetchone()
            value = str(setting_row[0]).strip() if setting_row and setting_row[0] else None
            if not value:
                continue
            coa_row = conn.execute(text("""
                SELECT id, code, name, subcategory
                FROM chart_of_accounts
                WHERE id = :value OR code = :value
                LIMIT 1
            """), {'value': value}).fetchone()
            if coa_row:
                return {
                    'id': coa_row.id,
                    'code': str(coa_row.code),
                    'name': coa_row.name,
                    'subcategory': coa_row.subcategory,
                }

    for code in ('2191', '2141'):
        coa_row = conn.execute(text("""
            SELECT id, code, name, subcategory
            FROM chart_of_accounts
            WHERE code = :code
            LIMIT 1
        """), {'code': code}).fetchone()
        if coa_row:
            return {
                'id': coa_row.id,
                'code': str(coa_row.code),
                'name': coa_row.name,
                'subcategory': coa_row.subcategory,
            }

    return {
        'id': None,
        'code': '2191',
        'name': 'Utang PPh Jasa',
        'subcategory': 'Current Liabilities',
    }


def _service_tracking_config(conn, report_type, mark_alias='m', transaction_alias='t'):
    txn_columns = get_table_columns(conn, 'transactions')
    mark_columns = get_table_columns(conn, 'marks')
    tracked_columns = {'service_npwp', 'service_calculation_method', 'service_tax_payment_timing', 'service_tax_payment_date'}
    has_any_service_tracking = any(col in txn_columns for col in tracked_columns)
    has_service_mark = 'is_service' in mark_columns
    if not has_service_mark and not has_any_service_tracking:
        return None

    npwp_expr = f"{transaction_alias}.service_npwp" if 'service_npwp' in txn_columns else "NULL"
    method_expr = f"COALESCE({transaction_alias}.service_calculation_method, 'BRUTO')" if 'service_calculation_method' in txn_columns else "'BRUTO'"
    timing_expr = f"COALESCE({transaction_alias}.service_tax_payment_timing, 'same_period')" if 'service_tax_payment_timing' in txn_columns else "'same_period'"
    payment_date_expr = f"{transaction_alias}.service_tax_payment_date" if 'service_tax_payment_date' in txn_columns else "NULL"
    split_exclusion_clause = _split_parent_exclusion_clause(conn, transaction_alias)
    coretax_clause = _coretax_filter_clause(conn, report_type, mark_alias)

    if conn.dialect.name == 'sqlite':
        mark_is_service_expr = f"LOWER(COALESCE(CAST({mark_alias}.is_service AS TEXT), '0')) IN ('1', 'true', 'yes', 'y')"
    else:
        mark_is_service_expr = f"LOWER(COALESCE(CAST({mark_alias}.is_service AS CHAR), '0')) IN ('1', 'true', 'yes', 'y')"

    service_filters = []
    if has_service_mark:
        service_filters.append(mark_is_service_expr)
    if 'service_npwp' in txn_columns:
        service_filters.append(f"COALESCE({transaction_alias}.service_npwp, '') <> ''")
    if 'service_tax_payment_timing' in txn_columns:
        service_filters.append(f"COALESCE({transaction_alias}.service_tax_payment_timing, 'same_period') IN ('next_period', 'next_year')")
    if 'service_tax_payment_date' in txn_columns:
        service_filters.append(f"{transaction_alias}.service_tax_payment_date IS NOT NULL")
    if not service_filters:
        return None

    return {
        'npwp_expr': npwp_expr,
        'method_expr': method_expr,
        'timing_expr': timing_expr,
        'payment_date_expr': payment_date_expr,
        'split_exclusion_clause': split_exclusion_clause,
        'coretax_clause': coretax_clause,
        'service_where_clause': " OR ".join(service_filters),
    }


def _calculate_service_tax_payable_as_of(conn, as_of_date, company_id=None, report_type='real'):
    config = _service_tracking_config(conn, report_type)
    if not config:
        return 0.0

    as_of_date_obj = _parse_date(as_of_date)
    if not as_of_date_obj:
        return 0.0

    query = text(f"""
        SELECT
            t.id,
            t.txn_date,
            t.amount,
            t.mark_id,
            m.is_service,
            {config['npwp_expr']} AS service_npwp,
            {config['method_expr']} AS service_calculation_method,
            {config['timing_expr']} AS service_tax_payment_timing,
            {config['payment_date_expr']} AS service_tax_payment_date
        FROM transactions t
        LEFT JOIN marks m ON t.mark_id = m.id
        WHERE ({config['service_where_clause']})
          AND t.txn_date <= :as_of_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {config['split_exclusion_clause']}
                {config['coretax_clause']}
    """)

    rows = conn.execute(query, {'as_of_date': as_of_date, 'company_id': company_id})
    total_payable = 0.0
    for row in rows:
        _, tax_amount = _service_tax_rate_and_amount(row.amount, row.service_npwp, row.service_calculation_method)
        if tax_amount <= 0:
            continue

        timing = str(row.service_tax_payment_timing or 'same_period').strip().lower()
        if timing not in {'same_period', 'next_period', 'next_year'}:
            timing = 'same_period'

        payment_date = _parse_date(row.service_tax_payment_date)
        if payment_date and payment_date <= as_of_date_obj:
            continue
        total_payable += tax_amount
    return total_payable


def _calculate_service_tax_adjustment_for_period(conn, start_date, end_date, company_id=None, report_type='real'):
    config = _service_tracking_config(conn, report_type)
    if not config:
        return []

    mark_coa_join = _mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='INNER')
    query = text(f"""
        SELECT
            coa.code,
            coa.name,
            coa.subcategory,
            t.amount,
            {config['npwp_expr']} AS service_npwp,
            {config['method_expr']} AS service_calculation_method
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE ({config['service_where_clause']})
          AND coa.category = 'EXPENSE'
          AND t.txn_date BETWEEN :start_date AND :end_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {config['split_exclusion_clause']}
                {config['coretax_clause']}
    """)

    rows = conn.execute(query, {
        'start_date': start_date,
        'end_date': end_date,
        'company_id': company_id,
    }).fetchall()

    adjustments_by_coa = {}
    for row in rows:
        _, tax_amount = _service_tax_rate_and_amount(row.amount, row.service_npwp, row.service_calculation_method)
        if tax_amount <= 0:
            continue

        coa_code = str(row.code)
        if coa_code not in adjustments_by_coa:
            adjustments_by_coa[coa_code] = {
                'code': coa_code,
                'name': row.name,
                'subcategory': row.subcategory,
                'amount': 0.0,
                'category': 'EXPENSE',
            }
        adjustments_by_coa[coa_code]['amount'] += tax_amount

    return list(adjustments_by_coa.values())
