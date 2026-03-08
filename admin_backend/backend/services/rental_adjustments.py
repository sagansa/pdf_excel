import logging

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

logger = logging.getLogger(__name__)


def _contract_tax_query_columns(contract_columns):
    return {
        'total_amount_sql': "COALESCE(c.total_amount, 0)" if 'total_amount' in contract_columns else "0",
        'method_sql': "COALESCE(c.calculation_method, 'BRUTO')" if 'calculation_method' in contract_columns else "'BRUTO'",
        'rate_sql': "COALESCE(c.pph42_rate, 10)" if 'pph42_rate' in contract_columns else "10",
        'timing_sql': "COALESCE(c.pph42_payment_timing, 'same_period')" if 'pph42_payment_timing' in contract_columns else "'same_period'",
        'payment_date_sql': "c.pph42_payment_date" if 'pph42_payment_date' in contract_columns else "NULL",
    }


def _calculate_tax_from_bruto(amount_bruto, rate):
    if amount_bruto <= 0:
        return 0.0
    amount_net = amount_bruto * (1.0 - (rate / 100.0))
    return max(0.0, amount_bruto - amount_net)


def _resolve_contract_bruto_amount(total_amount, linked_total, method, rate):
    total_amount = _to_float(total_amount, 0.0)
    linked_total = _to_float(linked_total, 0.0)
    method = str(method or 'BRUTO').strip().upper()
    rate = max(0.0, min(_to_float(rate, 10.0), 100.0))

    if total_amount > 0:
        return total_amount, rate
    if linked_total <= 0:
        return 0.0, rate
    if method == 'NETTO':
        divisor = max(0.000001, 1.0 - (rate / 100.0))
        return linked_total / divisor, rate
    return linked_total, rate


def _build_rental_contract_tax_query(conn, contract_columns, report_type):
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 'tpay')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
    columns = _contract_tax_query_columns(contract_columns)

    return text(f"""
        SELECT
            c.id,
            c.start_date,
            {columns['total_amount_sql']} AS total_amount,
            {columns['method_sql']} AS calculation_method,
            {columns['rate_sql']} AS pph42_rate,
            {columns['timing_sql']} AS pph42_payment_timing,
            {columns['payment_date_sql']} AS pph42_payment_date,
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


def _fetch_rental_contract_tax_rows(conn, as_of_date, company_id, report_type, require_deferred_only=False):
    contract_columns = get_table_columns(conn, 'rental_contracts')
    txn_columns = get_table_columns(conn, 'transactions')
    if 'rental_contract_id' not in txn_columns:
        return []
    if not contract_columns or 'start_date' not in contract_columns:
        return []
    if require_deferred_only and 'pph42_payment_timing' not in contract_columns:
        return []

    query = _build_rental_contract_tax_query(conn, contract_columns, report_type)
    rows = conn.execute(query, {
        'as_of_date': as_of_date,
        'company_id': company_id,
    })
    if not require_deferred_only:
        return rows

    deferred_rows = []
    for row in rows:
        timing = str(row.pph42_payment_timing or 'same_period').strip().lower()
        if timing in {'next_period', 'next_year'}:
            deferred_rows.append(row)
    return deferred_rows


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
    except Exception as exc:
        logger.warning("Failed to read prepaid_rent_expense_coa setting: %s", exc)

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
                'category': 'EXPENSE',
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
                'category': 'EXPENSE',
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
        'category': 'EXPENSE',
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
        'company_id': company_id,
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
            'category': 'EXPENSE',
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
        'company_id': company_id,
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
        if linked_total <= 0:
            continue

        total_months = (contract_end.year - contract_start.year) * 12 + (contract_end.month - contract_start.month) + 1
        if total_months <= 0:
            total_months = 1

        monthly_amount = linked_total / total_months
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


def _calculate_cumulative_rental_amortization_as_of(conn, as_of_date, company_id=None, report_type='real'):
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
        'company_id': company_id,
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

        amort_end = min(as_of_date_obj, contract_end)
        if amort_end < contract_start:
            continue

        total_months = (contract_end.year - contract_start.year) * 12 + (contract_end.month - contract_start.month) + 1
        if total_months <= 0:
            total_months = 1

        elapsed_months = (amort_end.year - contract_start.year) * 12 + (amort_end.month - contract_start.month)
        if amort_end.day >= contract_start.day or amort_end.month != contract_start.month or amort_end >= contract_end:
            elapsed_months += 1
        elapsed_months = min(elapsed_months, total_months)
        if elapsed_months <= 0:
            continue

        monthly_amount = linked_total / total_months
        total_amortized += monthly_amount * elapsed_months

    return total_amortized


def _calculate_rental_tax_breakdown(conn, as_of_date, company_id=None, report_type='real'):
    result_default = {'total_tax': 0.0, 'unpaid_tax': 0.0, 'paid_tax': 0.0}
    as_of_date_obj = _parse_date(as_of_date)
    if not as_of_date_obj:
        return result_default

    rows = _fetch_rental_contract_tax_rows(conn, as_of_date, company_id, report_type)
    total_tax = 0.0
    unpaid_tax = 0.0
    paid_tax = 0.0

    for row in rows:
        amount_bruto, rate = _resolve_contract_bruto_amount(
            row.total_amount,
            row.linked_total,
            row.calculation_method,
            row.pph42_rate,
        )
        timing = str(row.pph42_payment_timing or 'same_period').strip().lower()
        payment_date = _parse_date(row.pph42_payment_date)
        if amount_bruto <= 0:
            continue

        tax = _calculate_tax_from_bruto(amount_bruto, rate)
        total_tax += tax
        if timing in ('next_period', 'next_year'):
            if payment_date and payment_date <= as_of_date_obj:
                paid_tax += tax
            else:
                unpaid_tax += tax

    return {'total_tax': total_tax, 'unpaid_tax': unpaid_tax, 'paid_tax': paid_tax}


def _calculate_rental_tax_payable_as_of(conn, as_of_date, company_id=None, report_type='real'):
    as_of_date_obj = _parse_date(as_of_date)
    if not as_of_date_obj:
        return 0.0

    result = _fetch_rental_contract_tax_rows(
        conn,
        as_of_date,
        company_id,
        report_type,
        require_deferred_only=True,
    )

    total_rental_tax_payable = 0.0
    for row in result:
        payment_date = _parse_date(row.pph42_payment_date)
        if payment_date and payment_date <= as_of_date_obj:
            continue

        amount_bruto, rate = _resolve_contract_bruto_amount(
            row.total_amount,
            row.linked_total,
            row.calculation_method,
            row.pph42_rate,
        )
        if amount_bruto <= 0:
            continue

        total_rental_tax_payable += _calculate_tax_from_bruto(amount_bruto, rate)

    return total_rental_tax_payable
