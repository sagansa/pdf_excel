import logging

from sqlalchemy import text

from backend.db.schema import get_table_columns
from backend.services.report_common import (
    _coretax_filter_clause,
    _mark_coa_join_clause,
    _parse_date,
    _split_parent_exclusion_clause,
    _to_float,
)

logger = logging.getLogger(__name__)
def _overlap_days(start_a, end_a, start_b, end_b):
    if not all([start_a, end_a, start_b, end_b]):
        return 0

    overlap_start = max(start_a, start_b)
    overlap_end = min(end_a, end_b)
    if overlap_end < overlap_start:
        return 0

    return (overlap_end - overlap_start).days + 1


def _resolve_rent_expense_account(conn, company_id=None, templates=None):
    templates = templates or {}
    setting_value = None

    try:
        if get_table_columns(conn, 'amortization_settings'):
            setting_row = conn.execute(text("""
                SELECT setting_value
                FROM amortization_settings
                WHERE setting_name = 'prepaid_rent_expense_coa'
                  AND (company_id = :company_id OR company_id IS NULL)
                ORDER BY company_id DESC
                LIMIT 1
            """), {'company_id': company_id}).fetchone()
            setting_value = str(setting_row[0]).strip() if setting_row and setting_row[0] else None
    except Exception as e:
        logger.warning(f"Failed to read prepaid_rent_expense_coa setting: {e}")

    if setting_value:
        row = conn.execute(text("""
            SELECT code, name, subcategory
            FROM chart_of_accounts
            WHERE (id = :value OR code = :value)
            LIMIT 1
        """), {'value': setting_value}).fetchone()
        if row:
            return {
                'code': str(row.code),
                'name': row.name,
                'subcategory': row.subcategory,
                'category': 'EXPENSE'
            }

    for code in ('5315', '5105'):
        row = conn.execute(text("""
            SELECT code, name, subcategory
            FROM chart_of_accounts
            WHERE code = :code
            LIMIT 1
        """), {'code': code}).fetchone()
        if row:
            return {
                'code': str(row.code),
                'name': row.name,
                'subcategory': row.subcategory,
                'category': 'EXPENSE'
            }

    for code in ('5315', '5105'):
        if code in templates:
            return templates[code]
    if templates:
        return next(iter(templates.values()))

    return {
        'code': '5315',
        'name': 'Beban Sewa',
        'subcategory': 'Operating Expenses',
        'category': 'EXPENSE'
    }
def _fetch_non_contract_rent_expense_items(conn, start_date, end_date, company_id=None, report_type='real'):
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
    mark_coa_join = _mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='INNER')
    txn_columns = get_table_columns(conn, 'transactions')
    contract_filter = "AND t.rental_contract_id IS NULL" if 'rental_contract_id' in txn_columns else ""

    query = text(f"""
        SELECT
            coa.code,
            coa.name,
            coa.subcategory,
            SUM(
                CASE
                    WHEN UPPER(COALESCE(mcm.mapping_type, '')) = 'DEBIT' THEN t.amount
                    WHEN UPPER(COALESCE(mcm.mapping_type, '')) = 'CREDIT' THEN -t.amount
                    WHEN t.db_cr = 'DB' THEN t.amount
                    WHEN t.db_cr = 'CR' THEN -t.amount
                    ELSE 0
                END
            ) AS total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
          AND coa.category = 'EXPENSE'
          AND coa.code IN ('5315', '5105')
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {contract_filter}
          {split_exclusion_clause}
                {coretax_clause}
        GROUP BY coa.code, coa.name, coa.subcategory
    """)

    rows = conn.execute(query, {
        'start_date': start_date,
        'end_date': end_date,
        'company_id': company_id
    })

    items = []
    for row in rows:
        amount = _to_float(row.total_amount, 0.0)
        if abs(amount) < 0.000001:
            continue
        items.append({
            'code': str(row.code),
            'name': row.name,
            'subcategory': row.subcategory,
            'amount': amount,
            'category': 'EXPENSE'
        })

    return items


def _calculate_prorated_contract_rent_expense(conn, start_date, end_date, company_id=None, report_type='real'):
    txn_columns = get_table_columns(conn, 'transactions')
    contract_columns = get_table_columns(conn, 'rental_contracts')

    if 'rental_contract_id' not in txn_columns:
        return 0.0
    if not contract_columns or 'start_date' not in contract_columns or 'end_date' not in contract_columns:
        return 0.0

    report_start = _parse_date(start_date)
    report_end = _parse_date(end_date)
    if not report_start or not report_end or report_end < report_start:
        return 0.0

    split_exclusion_clause = _split_parent_exclusion_clause(conn, 'tpay')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
    total_amount_sql = "COALESCE(c.total_amount, 0)" if 'total_amount' in contract_columns else "0"
    method_sql = "COALESCE(c.calculation_method, 'BRUTO')" if 'calculation_method' in contract_columns else "'BRUTO'"
    rate_sql = "COALESCE(c.pph42_rate, 10)" if 'pph42_rate' in contract_columns else "10"

    query = text(f"""
        SELECT
            c.id,
            c.start_date,
            c.end_date,
            {total_amount_sql} AS total_amount,
            {method_sql} AS calculation_method,
            {rate_sql} AS pph42_rate,
            COALESCE(txn.linked_total, 0) AS linked_total
        FROM rental_contracts c
        LEFT JOIN (
            SELECT
                tpay.rental_contract_id,
                COALESCE(SUM(ABS(tpay.amount)), 0) AS linked_total
            FROM transactions tpay
            LEFT JOIN marks m ON tpay.mark_id = m.id
            WHERE tpay.rental_contract_id IS NOT NULL
              AND (:company_id IS NULL OR tpay.company_id = :company_id)
              {split_exclusion_clause}
              {coretax_clause}
            GROUP BY tpay.rental_contract_id
        ) txn ON txn.rental_contract_id = c.id
        WHERE c.start_date <= :report_end
          AND c.end_date >= :report_start
          AND (:company_id IS NULL OR c.company_id = :company_id)
    """)

    result = conn.execute(query, {
        'report_start': start_date,
        'report_end': end_date,
        'company_id': company_id
    })

    total_prorated = 0.0
    for row in result:
        contract_start = _parse_date(row.start_date)
        contract_end = _parse_date(row.end_date) or contract_start
        if not contract_start or not contract_end:
            continue
        if contract_end < contract_start:
            contract_end = contract_start

        linked_total = _to_float(row.linked_total, 0.0)

        if str(report_type).strip().lower() == 'coretax' and linked_total <= 0:
            continue

        # Use netto (linked_total) as amortization base - matches 1421 balance
        if linked_total <= 0:
            continue

        # Monthly proration (consistent with BS amortization)
        total_months = (contract_end.year - contract_start.year) * 12 + (contract_end.month - contract_start.month) + 1
        if total_months <= 0:
            total_months = 1

        monthly_amount = linked_total / total_months

        # Calculate overlap months in the report period
        overlap_start = max(contract_start, report_start)
        overlap_end = min(contract_end, report_end)
        if overlap_end < overlap_start:
            continue

        overlap_months = (overlap_end.year - overlap_start.year) * 12 + (overlap_end.month - overlap_start.month) + 1
        overlap_months = min(overlap_months, total_months)

        if overlap_months <= 0:
            continue

        total_prorated += monthly_amount * overlap_months

    return total_prorated


def _resolve_service_tax_payable_account(conn, company_id=None, preferred_setting=None):
    setting_candidates = ['service_tax_payable_coa', 'prepaid_tax_payable_coa']
    if preferred_setting and preferred_setting in setting_candidates:
        # Move preferred to front
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
                    'subcategory': coa_row.subcategory
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
                'subcategory': coa_row.subcategory
            }

    return {
        'id': None,
        'code': '2191',
        'name': 'Utang PPh Jasa',
        'subcategory': 'Current Liabilities'
    }


def _calculate_service_tax_payable_as_of(conn, as_of_date, company_id=None, report_type='real'):
    txn_columns = get_table_columns(conn, 'transactions')
    mark_columns = get_table_columns(conn, 'marks')
    tracked_columns = {'service_npwp', 'service_calculation_method', 'service_tax_payment_timing', 'service_tax_payment_date'}
    has_any_service_tracking = any(col in txn_columns for col in tracked_columns)
    has_service_mark = 'is_service' in mark_columns
    if not has_service_mark and not has_any_service_tracking:
        return 0.0

    as_of_date_obj = _parse_date(as_of_date)
    if not as_of_date_obj:
        return 0.0

    npwp_expr = "t.service_npwp" if 'service_npwp' in txn_columns else "NULL"
    method_expr = "COALESCE(t.service_calculation_method, 'BRUTO')" if 'service_calculation_method' in txn_columns else "'BRUTO'"
    timing_expr = "COALESCE(t.service_tax_payment_timing, 'same_period')" if 'service_tax_payment_timing' in txn_columns else "'same_period'"
    payment_date_expr = "t.service_tax_payment_date" if 'service_tax_payment_date' in txn_columns else "NULL"
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')

    if conn.dialect.name == 'sqlite':
        mark_is_service_expr = "LOWER(COALESCE(CAST(m.is_service AS TEXT), '0')) IN ('1', 'true', 'yes', 'y')"
    else:
        mark_is_service_expr = "LOWER(COALESCE(CAST(m.is_service AS CHAR), '0')) IN ('1', 'true', 'yes', 'y')"

    service_filters = []
    if has_service_mark:
        service_filters.append(mark_is_service_expr)
    if 'service_npwp' in txn_columns:
        service_filters.append("COALESCE(t.service_npwp, '') <> ''")
    if 'service_tax_payment_timing' in txn_columns:
        service_filters.append("COALESCE(t.service_tax_payment_timing, 'same_period') IN ('next_period', 'next_year')")
    if 'service_tax_payment_date' in txn_columns:
        service_filters.append("t.service_tax_payment_date IS NOT NULL")

    if not service_filters:
        return 0.0
    service_where_clause = " OR ".join(service_filters)

    query = text(f"""
        SELECT
            t.id,
            t.txn_date,
            t.amount,
            t.mark_id,
            m.is_service,
            {npwp_expr} AS service_npwp,
            {method_expr} AS service_calculation_method,
            {timing_expr} AS service_tax_payment_timing,
            {payment_date_expr} AS service_tax_payment_date
        FROM transactions t
        LEFT JOIN marks m ON t.mark_id = m.id
        WHERE ({service_where_clause})
          AND t.txn_date <= :as_of_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion_clause}
                {coretax_clause}
    """)

    rows = conn.execute(query, {'as_of_date': as_of_date, 'company_id': company_id})
    total_payable = 0.0

    for row in rows:
        npwp_digits = ''.join(ch for ch in str(row.service_npwp or '') if ch.isdigit())
        has_npwp = len(npwp_digits) == 15
        tax_rate = 2.0 if has_npwp else 4.0
        amount_base = abs(_to_float(row.amount, 0.0))
        method = str(row.service_calculation_method or 'BRUTO').strip().upper()
        if method not in {'BRUTO', 'NETTO', 'NONE'}:
            method = 'BRUTO'

        if method == 'NONE':
            continue

        if method == 'NETTO':
            divisor = max(0.000001, 1.0 - (tax_rate / 100.0))
            bruto = amount_base / divisor
            tax_amount = max(0.0, bruto - amount_base)
        else:
            tax_amount = amount_base * (tax_rate / 100.0)

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
    """
    Calculates the total service withholding tax (PPh 23/21) for a given period.
    This is used to 'gross up' the expenses in the Income Statement.
    """
    txn_columns = get_table_columns(conn, 'transactions')
    mark_columns = get_table_columns(conn, 'marks')
    tracked_columns = {'service_npwp', 'service_calculation_method', 'service_tax_payment_timing'}
    has_any_service_tracking = any(col in txn_columns for col in tracked_columns)
    has_service_mark = 'is_service' in mark_columns
    if not has_service_mark and not has_any_service_tracking:
        return []

    npwp_expr = "t.service_npwp" if 'service_npwp' in txn_columns else "NULL"
    method_expr = "COALESCE(t.service_calculation_method, 'BRUTO')" if 'service_calculation_method' in txn_columns else "'BRUTO'"
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
    mark_coa_join = _mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='INNER')

    if conn.dialect.name == 'sqlite':
        mark_is_service_expr = "LOWER(COALESCE(CAST(m.is_service AS TEXT), '0')) IN ('1', 'true', 'yes', 'y')"
    else:
        mark_is_service_expr = "LOWER(COALESCE(CAST(m.is_service AS CHAR), '0')) IN ('1', 'true', 'yes', 'y')"

    service_filters = []
    if has_service_mark:
        service_filters.append(mark_is_service_expr)
    if 'service_npwp' in txn_columns:
        service_filters.append("COALESCE(t.service_npwp, '') <> ''")
    if 'service_tax_payment_timing' in txn_columns:
        service_filters.append("COALESCE(t.service_tax_payment_timing, 'same_period') IN ('next_period', 'next_year')")
    if 'service_tax_payment_date' in txn_columns:
        service_filters.append("t.service_tax_payment_date IS NOT NULL")
    
    if not service_filters:
        return []
    service_where_clause = " OR ".join(service_filters)

    query = text(f"""
        SELECT
            coa.code,
            coa.name,
            coa.subcategory,
            t.amount,
            {npwp_expr} AS service_npwp,
            {method_expr} AS service_calculation_method
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE ({service_where_clause})
          AND coa.category = 'EXPENSE'
          AND t.txn_date BETWEEN :start_date AND :end_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion_clause}
                {coretax_clause}
    """)

    rows = conn.execute(query, {
        'start_date': start_date,
        'end_date': end_date,
        'company_id': company_id
    }).fetchall()
    
    adjustments_by_coa = {}

    for row in rows:
        npwp_digits = ''.join(ch for ch in str(row.service_npwp or '') if ch.isdigit())
        has_npwp = len(npwp_digits) == 15
        tax_rate = 2.0 if has_npwp else 4.0
        amount_base = abs(_to_float(row.amount, 0.0))
        method = str(row.service_calculation_method or 'BRUTO').strip().upper()
        
        tax_amount = 0.0
        if method == 'NONE':
            tax_amount = 0.0
        elif method == 'NETTO':
            divisor = max(0.000001, 1.0 - (tax_rate / 100.0))
            bruto = amount_base / divisor
            tax_amount = max(0.0, bruto - amount_base)
        else:
            # For BRUTO, we assume the user paid the 'base' amount, 
            # and the withheld tax is an ADDITION to that expense.
            tax_amount = amount_base * (tax_rate / 100.0)

        if tax_amount <= 0:
            continue

        coa_code = str(row.code)
        if coa_code not in adjustments_by_coa:
            adjustments_by_coa[coa_code] = {
                'code': coa_code,
                'name': row.name,
                'subcategory': row.subcategory,
                'amount': 0.0,
                'category': 'EXPENSE'
            }
        adjustments_by_coa[coa_code]['amount'] += tax_amount

    return list(adjustments_by_coa.values())


def _calculate_cumulative_rental_amortization_as_of(conn, as_of_date, company_id=None, report_type='real'):
    """
    Computes cumulative prepaid rent amortized from contract start through as_of_date.
    
    Uses linked_total (netto payment amount) as the base, since 1421 balance
    comes from bank transaction amounts which are netto payments.
    
    The monthly amortization = linked_total / duration_months.
    Prorated by elapsed months from contract start to min(as_of_date, contract_end).
    """
    contract_columns = get_table_columns(conn, 'rental_contracts')
    txn_columns = get_table_columns(conn, 'transactions')
    if 'rental_contract_id' not in txn_columns:
        return 0.0
    if not contract_columns or 'start_date' not in contract_columns or 'end_date' not in contract_columns:
        return 0.0

    as_of_date_obj = _parse_date(as_of_date)
    if not as_of_date_obj:
        return 0.0

    split_exclusion_clause = _split_parent_exclusion_clause(conn, 'tpay')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')

    query = text(f"""
        SELECT
            c.id,
            c.start_date,
            c.end_date,
            COALESCE(txn.linked_total, 0) AS linked_total
        FROM rental_contracts c
        LEFT JOIN (
            SELECT
                tpay.rental_contract_id,
                COALESCE(SUM(ABS(tpay.amount)), 0) AS linked_total
            FROM transactions tpay
            LEFT JOIN marks m ON tpay.mark_id = m.id
            WHERE tpay.rental_contract_id IS NOT NULL
              AND (:company_id IS NULL OR tpay.company_id = :company_id)
              {split_exclusion_clause}
              {coretax_clause}
            GROUP BY tpay.rental_contract_id
        ) txn ON txn.rental_contract_id = c.id
        WHERE c.start_date <= :as_of_date
          AND (:company_id IS NULL OR c.company_id = :company_id)
    """)

    result = conn.execute(query, {
        'as_of_date': as_of_date,
        'company_id': company_id
    })

    total_amortized = 0.0

    for row in result:
        contract_start = _parse_date(row.start_date)
        contract_end = _parse_date(row.end_date) or contract_start
        if not contract_start or not contract_end:
            continue
        if contract_end < contract_start:
            contract_end = contract_start

        linked_total = _to_float(row.linked_total, 0.0)
        if linked_total <= 0:
            continue

        # Calculate elapsed months
        amort_end = min(as_of_date_obj, contract_end)
        if amort_end < contract_start:
            continue

        total_months = (contract_end.year - contract_start.year) * 12 + (contract_end.month - contract_start.month) + 1
        if total_months <= 0:
            total_months = 1

        elapsed_months = (amort_end.year - contract_start.year) * 12 + (amort_end.month - contract_start.month)
        # Count current month if we're past the start day
        if amort_end.day >= contract_start.day or amort_end.month != contract_start.month or amort_end >= contract_end:
            elapsed_months += 1
        elapsed_months = min(elapsed_months, total_months)

        if elapsed_months <= 0:
            continue

        # Use linked_total (netto payment) as base — matches what's in 1421
        monthly_amount = linked_total / total_months
        total_amortized += monthly_amount * elapsed_months

    return total_amortized


def _calculate_rental_tax_breakdown(conn, as_of_date, company_id=None, report_type='real'):
    """
    Returns a breakdown of rental PPh 4(2) tax:
      - total_tax: tax for all contracts that started by as_of_date (Dr 1421)
      - unpaid_tax: deferred tax not yet paid (Cr 2191)
      - paid_tax: deferred tax already paid (Cr 1101)
    """
    contract_columns = get_table_columns(conn, 'rental_contracts')
    txn_columns = get_table_columns(conn, 'transactions')
    result_default = {'total_tax': 0.0, 'unpaid_tax': 0.0, 'paid_tax': 0.0}

    if 'rental_contract_id' not in txn_columns:
        return result_default
    if not contract_columns or 'start_date' not in contract_columns:
        return result_default

    as_of_date_obj = _parse_date(as_of_date)
    if not as_of_date_obj:
        return result_default

    split_exclusion_clause = _split_parent_exclusion_clause(conn, 'tpay')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
    total_amount_sql = "COALESCE(c.total_amount, 0)" if 'total_amount' in contract_columns else "0"
    method_sql = "COALESCE(c.calculation_method, 'BRUTO')" if 'calculation_method' in contract_columns else "'BRUTO'"
    rate_sql = "COALESCE(c.pph42_rate, 10)" if 'pph42_rate' in contract_columns else "10"
    timing_sql = "COALESCE(c.pph42_payment_timing, 'same_period')" if 'pph42_payment_timing' in contract_columns else "'same_period'"
    payment_date_sql = "c.pph42_payment_date" if 'pph42_payment_date' in contract_columns else "NULL"

    query = text(f"""
        SELECT
            c.id,
            c.start_date,
            {total_amount_sql} AS total_amount,
            {method_sql} AS calculation_method,
            {rate_sql} AS pph42_rate,
            {timing_sql} AS pph42_payment_timing,
            {payment_date_sql} AS pph42_payment_date,
            COALESCE(txn.linked_total, 0) AS linked_total
        FROM rental_contracts c
        LEFT JOIN (
            SELECT
                tpay.rental_contract_id,
                COALESCE(SUM(ABS(tpay.amount)), 0) AS linked_total
            FROM transactions tpay
            LEFT JOIN marks m ON tpay.mark_id = m.id
            WHERE tpay.rental_contract_id IS NOT NULL
              {coretax_clause}
              AND (:company_id IS NULL OR tpay.company_id = :company_id)
              AND tpay.txn_date <= :as_of_date
              {split_exclusion_clause}
            GROUP BY tpay.rental_contract_id
        ) txn ON txn.rental_contract_id = c.id
        WHERE c.start_date <= :as_of_date
          AND (:company_id IS NULL OR c.company_id = :company_id)
    """)

    rows = conn.execute(query, {
        'as_of_date': as_of_date,
        'company_id': company_id
    })

    total_tax = 0.0
    unpaid_tax = 0.0
    paid_tax = 0.0

    for row in rows:
        total_amount = _to_float(row.total_amount, 0.0)
        linked_total = _to_float(row.linked_total, 0.0)
        method = str(row.calculation_method or 'BRUTO').strip().upper()
        rate = max(0.0, min(_to_float(row.pph42_rate, 10.0), 100.0))
        timing = str(row.pph42_payment_timing or 'same_period').strip().lower()
        payment_date = _parse_date(row.pph42_payment_date)

        if total_amount > 0:
            amount_bruto = total_amount
        elif linked_total > 0:
            if method == 'NETTO':
                divisor = max(0.000001, 1.0 - (rate / 100.0))
                amount_bruto = linked_total / divisor
            else:
                amount_bruto = linked_total
        else:
            continue

        if amount_bruto <= 0:
            continue

        amount_net = amount_bruto * (1.0 - (rate / 100.0))
        tax = max(0.0, amount_bruto - amount_net)
        total_tax += tax

        # Deferred timing: tax is a liability until paid
        if timing in ('next_period', 'next_year'):
            if payment_date and payment_date <= as_of_date_obj:
                paid_tax += tax  # Already paid → Cr 1101
            else:
                unpaid_tax += tax  # Still owed → Cr 2191

    return {'total_tax': total_tax, 'unpaid_tax': unpaid_tax, 'paid_tax': paid_tax}


def _calculate_rental_tax_payable_as_of(conn, as_of_date, company_id=None, report_type='real'):
    """
    Computes unpaid / deferred PPh 4(2) liability from rental contracts.
    Liability exists if payment_timing is deferred and the stated payment_date (if any)
    is past the report's as_of_date.
    """
    contract_columns = get_table_columns(conn, 'rental_contracts')
    txn_columns = get_table_columns(conn, 'transactions')
    if 'rental_contract_id' not in txn_columns or 'pph42_payment_timing' not in contract_columns:
        return 0.0

    as_of_date_obj = _parse_date(as_of_date)
    if not as_of_date_obj:
        return 0.0

    split_exclusion_clause = _split_parent_exclusion_clause(conn, 'tpay')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
    total_amount_sql = "COALESCE(c.total_amount, 0)" if 'total_amount' in contract_columns else "0"
    method_sql = "COALESCE(c.calculation_method, 'BRUTO')" if 'calculation_method' in contract_columns else "'BRUTO'"
    rate_sql = "COALESCE(c.pph42_rate, 10)" if 'pph42_rate' in contract_columns else "10"
    timing_sql = "COALESCE(c.pph42_payment_timing, 'same_period')" if 'pph42_payment_timing' in contract_columns else "'same_period'"
    payment_date_sql = "c.pph42_payment_date" if 'pph42_payment_date' in contract_columns else "NULL"

    query = text(f"""
        SELECT
            c.id,
            c.start_date,
            {total_amount_sql} AS total_amount,
            {method_sql} AS calculation_method,
            {rate_sql} AS pph42_rate,
            {timing_sql} AS pph42_payment_timing,
            {payment_date_sql} AS pph42_payment_date,
            COALESCE(txn.linked_total, 0) AS linked_total
        FROM rental_contracts c
        LEFT JOIN (
            SELECT
                tpay.rental_contract_id,
                COALESCE(SUM(ABS(tpay.amount)), 0) AS linked_total
            FROM transactions tpay
            LEFT JOIN marks m ON tpay.mark_id = m.id
            WHERE tpay.rental_contract_id IS NOT NULL
              {coretax_clause}
              AND (:company_id IS NULL OR tpay.company_id = :company_id)
              AND tpay.txn_date <= :as_of_date
              {split_exclusion_clause}
            GROUP BY tpay.rental_contract_id
        ) txn ON txn.rental_contract_id = c.id
        WHERE c.start_date <= :as_of_date
          AND {timing_sql} IN ('next_period', 'next_year')
          AND (:company_id IS NULL OR c.company_id = :company_id)
    """)

    result = conn.execute(query, {
        'as_of_date': as_of_date,
        'company_id': company_id
    })

    total_rental_tax_payable = 0.0

    for row in result:
        payment_date = _parse_date(row.pph42_payment_date)
        if payment_date and payment_date <= as_of_date_obj:
            # Tax has presumably been paid by this period
            continue

        total_amount = _to_float(row.total_amount, 0.0)
        linked_total = _to_float(row.linked_total, 0.0)
        method = str(row.calculation_method or 'BRUTO').strip().upper()
        rate = max(0.0, min(_to_float(row.pph42_rate, 10.0), 100.0))

        if total_amount > 0:
            amount_bruto = total_amount
        elif linked_total > 0:
            if method == 'NETTO':
                divisor = max(0.000001, 1.0 - (rate / 100.0))
                amount_bruto = linked_total / divisor
            else:
                amount_bruto = linked_total
        else:
            amount_bruto = 0.0

        if amount_bruto <= 0:
            continue

        amount_net = amount_bruto * (1.0 - (rate / 100.0))
        tax_amount = max(0.0, amount_bruto - amount_net)
        
        total_rental_tax_payable += tax_amount

    return total_rental_tax_payable
