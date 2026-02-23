import logging
import json
import os
import re
from datetime import datetime, date
from sqlalchemy import text
from backend.db.session import get_sagansa_engine

logger = logging.getLogger(__name__)
RENT_EXPENSE_CODES = {'5315', '5105'}

def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'y'}
    return False

def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').date()
        except ValueError:
            return None
    return None


def _table_columns(conn, table_name):
    if conn.dialect.name == 'sqlite':
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return {str(row[1]) for row in rows}

    rows = conn.execute(text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
    """), {'table_name': table_name}).fetchall()
    return {str(row[0]) for row in rows}


def _split_parent_exclusion_clause(conn, alias='t'):
    txn_columns = _table_columns(conn, 'transactions')
    if 'parent_id' not in txn_columns:
        return ''
    return f" AND NOT EXISTS (SELECT 1 FROM transactions t_child WHERE t_child.parent_id = {alias}.id)"


def _safe_identifier(value, fallback):
    raw = str(value or fallback).strip()
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', raw):
        return fallback
    return raw


def _fetch_sagansa_user_map():
    engine, error_msg = get_sagansa_engine()
    if engine is None:
        logger.warning(f"Failed to connect to Sagansa DB for payroll summary: {error_msg}")
        return {}

    user_table = _safe_identifier(os.environ.get('SAGANSA_USER_TABLE'), 'users')
    user_id_col = _safe_identifier(os.environ.get('SAGANSA_USER_ID_COLUMN'), 'id')
    user_name_col = _safe_identifier(os.environ.get('SAGANSA_USER_NAME_COLUMN'), 'name')
    user_active_col = _safe_identifier(os.environ.get('SAGANSA_USER_ACTIVE_COLUMN'), '')

    where_active_sql = f"WHERE COALESCE(`{user_active_col}`, 1) = 1" if user_active_col else ''
    query = text(f"""
        SELECT
            CAST(`{user_id_col}` AS CHAR) AS id,
            CAST(`{user_name_col}` AS CHAR) AS name
        FROM `{user_table}`
        {where_active_sql}
        ORDER BY `{user_name_col}` ASC
        LIMIT 5000
    """)

    user_map = {}
    try:
        with engine.connect() as conn:
            for row in conn.execute(query):
                user_id = str(row.id or '').strip()
                if not user_id:
                    continue
                user_map[user_id] = {
                    'id': user_id,
                    'name': str(row.name or '').strip() or user_id
                }
    except Exception as e:
        logger.warning(f"Failed to fetch Sagansa users for payroll summary: {e}")
        return {}

    return user_map

def _is_current_asset(subcategory, code):
    normalized = (subcategory or '').strip().lower()

    # Check non-current first because "non-current" contains the word "current".
    if 'non-current' in normalized or 'tidak lancar' in normalized:
        return False
    if 'current' in normalized or 'lancar' in normalized:
        return True

    # Fallback by code prefix.
    code_str = str(code or '')
    return code_str.startswith(('11', '12', '13', '14'))

def _calculate_accumulated_amortization(amount, rate, start_date, as_of_date, use_half_rate=False, allow_partial_year=True):
    if amount <= 0 or start_date is None or start_date > as_of_date:
        return 0.0

    annual_base = amount * (rate / 100.0)
    accumulated = 0.0

    for year in range(start_date.year, as_of_date.year + 1):
        year_amort = annual_base

        if year == start_date.year:
            if allow_partial_year:
                if year == as_of_date.year:
                    months_active = as_of_date.month - start_date.month + 1
                else:
                    months_active = 12 - start_date.month + 1
                months_active = max(0, min(months_active, 12))
                year_amort = annual_base * (months_active / 12.0)
            elif use_half_rate:
                year_amort = annual_base * 0.5
        elif year == as_of_date.year and as_of_date.month < 12:
            year_amort = annual_base * (as_of_date.month / 12.0)

        remaining = max(amount - accumulated, 0.0)
        if remaining <= 0:
            break
        accumulated += min(year_amort, remaining)

    return max(0.0, min(accumulated, amount))


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_text(value):
    return re.sub(r'[^a-z0-9]+', '', str(value or '').strip().lower())


def _is_cogs_expense_item(item):
    code = str((item or {}).get('code') or '').strip()
    subcategory = _normalize_text((item or {}).get('subcategory'))

    cogs_subcategories = {
        'cogs',
        'costofgoodssold',
        'costofgoodsold',
        'hargapokokpenjualan',
        'bebanpokokpenjualan'
    }

    if subcategory in cogs_subcategories:
        return True
    if 'costofgoods' in subcategory or 'hargapokok' in subcategory:
        return True

    # Fallback by COA code family: 50xx is generally COGS in this project setup.
    if code.startswith('50'):
        return True

    return False


def _load_amortization_calculation_settings(conn, company_id=None):
    default_rate = 20.0
    allow_partial_year = True

    if company_id:
        settings_query = text("""
            SELECT setting_name, setting_value
            FROM amortization_settings
            WHERE company_id = :company_id OR company_id IS NULL
            ORDER BY company_id ASC
        """)
        rows = conn.execute(settings_query, {'company_id': company_id})
    else:
        settings_query = text("""
            SELECT setting_name, setting_value
            FROM amortization_settings
            WHERE company_id IS NULL
        """)
        rows = conn.execute(settings_query)

    for row in rows:
        setting_name = str(row.setting_name or '').strip()
        setting_value = row.setting_value
        if setting_name == 'default_amortization_rate':
            default_rate = _to_float(setting_value, 20.0)
        elif setting_name == 'allow_partial_year':
            allow_partial_year = _parse_bool(setting_value)

    return default_rate, allow_partial_year


def _calculate_current_year_amortization(
    base_amount,
    tarif_rate,
    start_date_value,
    report_year,
    use_half_rate=False,
    allow_partial_year=True
):
    amount = _to_float(base_amount, 0.0)
    rate = _to_float(tarif_rate, 0.0)
    if amount <= 0 or rate <= 0:
        return 0.0

    start_date = _parse_date(start_date_value)
    if start_date is None:
        start_date = date(report_year, 1, 1)

    acquisition_year = start_date.year
    if acquisition_year > report_year:
        return 0.0

    annual_amort_base = amount * (rate / 100.0)
    accumulated_prev = 0.0
    current_year_amort = 0.0

    for year in range(acquisition_year, report_year + 1):
        year_amort = annual_amort_base
        if year == acquisition_year:
            if allow_partial_year:
                months = 12 - start_date.month + 1
                year_amort = annual_amort_base * (months / 12.0)
            elif use_half_rate:
                year_amort = annual_amort_base * 0.5

        remaining = amount - accumulated_prev
        year_amort = min(year_amort, max(remaining, 0.0))

        if year < report_year:
            accumulated_prev += year_amort
        else:
            current_year_amort = year_amort

    return max(current_year_amort, 0.0)


def _calculate_dynamic_5314_total(conn, start_date, company_id=None):
    report_year = int(str(start_date)[:4])
    default_rate, allow_partial_year = _load_amortization_calculation_settings(conn, company_id)

    if company_id:
        company_filter_sql = "AND ai.company_id = :company_id"
        company_params = {'company_id': company_id}
    else:
        company_filter_sql = ""
        company_params = {}

    manual_query = text(f"""
        SELECT
            ai.year,
            ai.amount,
            ai.amortization_date,
            ai.asset_group_id,
            ai.use_half_rate,
            ag.tarif_rate
        FROM amortization_items ai
        LEFT JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
        WHERE 1=1
          {company_filter_sql}
    """)
    manual_rows = conn.execute(manual_query, company_params)

    manual_total = 0.0
    for row in manual_rows:
        amount = _to_float(row.amount, 0.0)
        if amount <= 0:
            continue

        item_year = int(_to_float(row.year, report_year))
        start_date_value = _parse_date(row.amortization_date) or date(report_year, 1, 1)
        purchase_year = start_date_value.year

        # One-time direct adjustment: only recognized on item year.
        if not row.asset_group_id and item_year != report_year:
            continue
        if purchase_year > report_year:
            continue

        tarif_rate = _to_float(row.tarif_rate, default_rate) or default_rate
        if row.asset_group_id:
            annual_amort = _calculate_current_year_amortization(
                amount,
                tarif_rate,
                start_date_value,
                report_year,
                use_half_rate=_parse_bool(row.use_half_rate),
                allow_partial_year=allow_partial_year
            )
        else:
            annual_amort = amount

        manual_total += annual_amort

    if conn.dialect.name == 'sqlite':
        txn_year_clause = "CAST(strftime('%Y', t.txn_date) AS INTEGER) <= :report_year"
    else:
        txn_year_clause = "YEAR(t.txn_date) <= :report_year"

    txn_company_clause = "AND t.company_id = :company_id" if company_id else ""
    txn_query = text(f"""
        SELECT DISTINCT
            t.id,
            t.amount AS acquisition_cost,
            t.amortization_start_date,
            t.txn_date,
            t.use_half_rate,
            ag.tarif_rate
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON t.mark_id = mcm.mark_id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        LEFT JOIN amortization_asset_groups ag ON t.amortization_asset_group_id = ag.id
        WHERE coa.code = '5314'
          {txn_company_clause}
          AND {txn_year_clause}
    """)
    txn_params = {'report_year': report_year}
    if company_id:
        txn_params['company_id'] = company_id

    calculated_total = 0.0
    for row in conn.execute(txn_query, txn_params):
        base_amount = _to_float(row.acquisition_cost, 0.0)
        if base_amount <= 0:
            continue

        start_date_value = _parse_date(row.amortization_start_date) or _parse_date(row.txn_date) or date(report_year, 1, 1)
        tarif_rate = _to_float(row.tarif_rate, default_rate) or default_rate
        calculated_total += _calculate_current_year_amortization(
            base_amount,
            tarif_rate,
            start_date_value,
            report_year,
            use_half_rate=_parse_bool(row.use_half_rate),
            allow_partial_year=allow_partial_year
        )

    asset_company_clause = "AND a.company_id = :company_id" if company_id else ""
    assets_query = text(f"""
        SELECT
            a.acquisition_cost,
            a.acquisition_date,
            a.amortization_start_date,
            a.use_half_rate,
            ag.tarif_rate
        FROM amortization_assets a
        LEFT JOIN amortization_asset_groups ag ON a.asset_group_id = ag.id
        WHERE (a.is_active = TRUE OR a.is_active = 1)
          {asset_company_clause}
    """)
    asset_params = {'company_id': company_id} if company_id else {}
    for row in conn.execute(assets_query, asset_params):
        base_amount = _to_float(row.acquisition_cost, 0.0)
        if base_amount <= 0:
            continue

        start_date_value = _parse_date(row.amortization_start_date) or _parse_date(row.acquisition_date) or date(report_year, 1, 1)
        tarif_rate = _to_float(row.tarif_rate, default_rate) or default_rate
        calculated_total += _calculate_current_year_amortization(
            base_amount,
            tarif_rate,
            start_date_value,
            report_year,
            use_half_rate=_parse_bool(row.use_half_rate),
            allow_partial_year=allow_partial_year
        )

    total_5314 = manual_total + calculated_total
    return {
        'report_year': report_year,
        'manual_total': manual_total,
        'calculated_total': calculated_total,
        'total_5314': total_5314
    }


def _get_inventory_balance_with_carry(conn, year, company_id=None):
    year = int(year)
    current_query = text("""
        SELECT beginning_inventory_amount, beginning_inventory_qty,
               ending_inventory_amount, ending_inventory_qty
        FROM inventory_balances
        WHERE year = :year AND (:company_id IS NULL OR company_id = :company_id)
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
    """)
    current = conn.execute(current_query, {'year': year, 'company_id': company_id}).fetchone()

    beginning_amount = _to_float(current[0], 0.0) if current else 0.0
    beginning_qty = _to_float(current[1], 0.0) if current else 0.0
    ending_amount = _to_float(current[2], 0.0) if current else 0.0
    ending_qty = _to_float(current[3], 0.0) if current else 0.0

    if abs(beginning_amount) < 0.000001 and abs(beginning_qty) < 0.000001:
        prev_query = text("""
            SELECT ending_inventory_amount, ending_inventory_qty
            FROM inventory_balances
            WHERE year = :year AND (:company_id IS NULL OR company_id = :company_id)
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
        """)
        previous = conn.execute(prev_query, {'year': year - 1, 'company_id': company_id}).fetchone()
        if previous:
            prev_ending_amount = _to_float(previous[0], 0.0)
            prev_ending_qty = _to_float(previous[1], 0.0)
            if abs(prev_ending_amount) >= 0.000001 or abs(prev_ending_qty) >= 0.000001:
                beginning_amount = prev_ending_amount
                beginning_qty = prev_ending_qty

    return {
        'beginning_inventory_amount': beginning_amount,
        'beginning_inventory_qty': beginning_qty,
        'ending_inventory_amount': ending_amount,
        'ending_inventory_qty': ending_qty
    }


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
        if _table_columns(conn, 'amortization_settings'):
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


def _fetch_non_contract_rent_expense_items(conn, start_date, end_date, company_id=None):
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    txn_columns = _table_columns(conn, 'transactions')
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
        INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
          AND coa.category = 'EXPENSE'
          AND coa.code IN ('5315', '5105')
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {contract_filter}
          {split_exclusion_clause}
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


def _calculate_prorated_contract_rent_expense(conn, start_date, end_date, company_id=None):
    txn_columns = _table_columns(conn, 'transactions')
    contract_columns = _table_columns(conn, 'rental_contracts')

    if 'rental_contract_id' not in txn_columns:
        return 0.0
    if not contract_columns or 'start_date' not in contract_columns or 'end_date' not in contract_columns:
        return 0.0

    report_start = _parse_date(start_date)
    report_end = _parse_date(end_date)
    if not report_start or not report_end or report_end < report_start:
        return 0.0

    split_exclusion_clause = _split_parent_exclusion_clause(conn, 'tpay')
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
            WHERE tpay.rental_contract_id IS NOT NULL
              AND (:company_id IS NULL OR tpay.company_id = :company_id)
              {split_exclusion_clause}
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

        contract_days = (contract_end - contract_start).days + 1
        if contract_days <= 0:
            continue

        overlap = _overlap_days(contract_start, contract_end, report_start, report_end)
        if overlap <= 0:
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
        
        # Prorate the net rent expense over the contract days
        total_prorated += amount_net * (overlap / contract_days)

    return total_prorated


def _resolve_service_tax_payable_account(conn, company_id=None):
    setting_candidates = ['service_tax_payable_coa', 'prepaid_tax_payable_coa']

    try:
        settings_columns = _table_columns(conn, 'amortization_settings')
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


def _calculate_service_tax_payable_as_of(conn, as_of_date, company_id=None):
    txn_columns = _table_columns(conn, 'transactions')
    mark_columns = _table_columns(conn, 'marks')
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
            t.amount,
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
    """)

    rows = conn.execute(query, {'as_of_date': as_of_date, 'company_id': company_id})
    total_payable = 0.0

    for row in rows:
        npwp_digits = ''.join(ch for ch in str(row.service_npwp or '') if ch.isdigit())
        has_npwp = len(npwp_digits) == 15
        tax_rate = 2.0 if has_npwp else 4.0
        amount_base = abs(_to_float(row.amount, 0.0))
        method = str(row.service_calculation_method or 'BRUTO').strip().upper()
        if method not in {'BRUTO', 'NETTO'}:
            method = 'BRUTO'

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


def _calculate_rental_tax_payable_as_of(conn, as_of_date, company_id=None):
    """
    Computes unpaid / deferred PPh 4(2) liability from rental contracts.
    Liability exists if payment_timing is deferred and the stated payment_date (if any)
    is past the report's as_of_date.
    """
    contract_columns = _table_columns(conn, 'rental_contracts')
    txn_columns = _table_columns(conn, 'transactions')
    if 'rental_contract_id' not in txn_columns or 'pph42_payment_timing' not in contract_columns:
        return 0.0

    as_of_date_obj = _parse_date(as_of_date)
    if not as_of_date_obj:
        return 0.0

    split_exclusion_clause = _split_parent_exclusion_clause(conn, 'tpay')
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
            WHERE tpay.rental_contract_id IS NOT NULL
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

def fetch_balance_sheet_data(conn, as_of_date, company_id=None):
    """
    Helper function to fetch balance sheet data.
    Returns calculated values and lists of items.
    """
    as_of_date_obj = datetime.strptime(as_of_date, '%Y-%m-%d').date()

    # 1. Get asset, liability, and equity COA balances
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    query = text(f"""
        WITH coa_balances AS (
            SELECT 
                mcm.coa_id,
                SUM(
                    CASE
                        WHEN mcm.mapping_type = 'DEBIT' THEN t.amount
                        WHEN mcm.mapping_type = 'CREDIT' THEN -t.amount
                        ELSE 0
                    END
                ) as total_amount
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
            WHERE t.txn_date <= :as_of_date
                AND (:company_id IS NULL OR t.company_id = :company_id)
                {split_exclusion_clause}
            GROUP BY mcm.coa_id
        )
        SELECT
            coa.id,
            coa.code,
            coa.name,
            coa.category,
            coa.subcategory,
            COALESCE(b.total_amount, 0) as total_amount
        FROM chart_of_accounts coa
        LEFT JOIN coa_balances b ON b.coa_id = coa.id
        WHERE coa.category IN ('ASSET', 'LIABILITY', 'EQUITY')
            AND coa.is_active = TRUE
            AND COALESCE(b.total_amount, 0) != 0
        ORDER BY coa.code
    """)

    result = conn.execute(query, {
        'as_of_date': as_of_date,
        'company_id': company_id
    })

    asset_items = {}
    liabilities_current = []
    liabilities_non_current = []
    equity = []

    def add_or_update_asset_item(item_id, code, name, subcategory, amount, force_current=None):
        if abs(float(amount or 0)) < 0.000001:
            return

        code_key = str(code or '')
        existing = asset_items.get(code_key)

        if existing:
            existing['amount'] += float(amount or 0)
            if force_current is not None:
                existing['is_current'] = force_current
            elif not _is_current_asset(subcategory, code):
                existing['is_current'] = False
            return

        is_current = force_current if force_current is not None else _is_current_asset(subcategory, code)
        asset_items[code_key] = {
            'id': item_id,
            'code': code,
            'name': name,
            'subcategory': subcategory,
            'amount': float(amount or 0),
            'category': 'ASSET',
            'is_current': is_current
        }

    def add_or_update_liability_item(item_id, code, name, subcategory, amount, force_current=True):
        if abs(float(amount or 0)) < 0.000001:
            return

        target = liabilities_current if force_current else liabilities_non_current
        code_key = str(code or '')

        for item in target:
            if str(item.get('code') or '') == code_key:
                item['amount'] += float(amount or 0)
                return

        target.append({
            'id': item_id,
            'code': code,
            'name': name,
            'subcategory': subcategory,
            'amount': float(amount or 0),
            'category': 'LIABILITY'
        })

    for row in result:
        d = dict(row._mapping)
        amount = float(d['total_amount']) if d['total_amount'] else 0

        if d['category'] == 'ASSET':
            add_or_update_asset_item(
                d['id'],
                d['code'],
                d['name'],
                d.get('subcategory'),
                amount
            )
        elif d['category'] == 'LIABILITY':
            if d['code'] and d['code'].startswith('2'):
                add_or_update_liability_item(
                    d['id'],
                    d['code'],
                    d['name'],
                    d.get('subcategory'),
                    amount,
                    force_current=True
                )
            else:
                add_or_update_liability_item(
                    d['id'],
                    d['code'],
                    d['name'],
                    d.get('subcategory'),
                    amount,
                    force_current=False
                )
        elif d['category'] == 'EQUITY':
            equity.append({
                'id': d['id'],
                'code': d['code'],
                'name': d['name'],
                'subcategory': d['subcategory'],
                'amount': amount,
                'category': d['category']
            })

    service_tax_payable_computed = 0.0
    # 1.3 Bridge service withholding tax payable into liabilities.
    # This is computed from service transaction tax configuration when payment is deferred.
    try:
        service_tax_payable = _calculate_service_tax_payable_as_of(conn, as_of_date, company_id)
        service_tax_payable_computed = float(service_tax_payable or 0.0)
        if abs(service_tax_payable_computed) >= 0.000001:
            service_tax_coa = _resolve_service_tax_payable_account(conn, company_id)
            add_or_update_liability_item(
                service_tax_coa.get('id') or f'computed_service_tax_{as_of_date}_{company_id or "all"}',
                service_tax_coa.get('code') or '2191',
                service_tax_coa.get('name') or 'Utang PPh Jasa',
                service_tax_coa.get('subcategory') or 'Current Liabilities',
                service_tax_payable_computed,
                force_current=True
            )
    except Exception as e:
        logger.error(f"Failed to include service tax payable in balance sheet: {e}")

    # 1.4 Bridge rental PPh 4(2) tax payable into liabilities.
    # This is computed from rental contracts that have deferred tax payments.
    try:
        rental_tax_payable = _calculate_rental_tax_payable_as_of(conn, as_of_date, company_id)
        rental_tax_payable_computed = float(rental_tax_payable or 0.0)
        if abs(rental_tax_payable_computed) >= 0.000001:
            add_or_update_liability_item(
                f'computed_rental_tax_{as_of_date}_{company_id or "all"}',
                '2141',
                'Utang PPh Final Pasal 4(2)',
                'Current Liabilities',
                rental_tax_payable_computed,
                force_current=True
            )
    except Exception as e:
        logger.error(f"Failed to include rental tax payable (PPh 4(2)) in balance sheet: {e}")

    # 1.5 Bring current-year profit/loss into equity as "Laba/Rugi Tahun Berjalan".
    # This keeps balance sheet equity aligned with the income statement for the same year.
    current_year_net_income = 0.0
    try:
        year_start = as_of_date_obj.replace(month=1, day=1).strftime('%Y-%m-%d')
        income_statement_data = fetch_income_statement_data(conn, year_start, as_of_date, company_id)
        current_year_net_income = float(income_statement_data.get('net_income') or 0.0)

        if abs(current_year_net_income) >= 0.000001:
            equity.append({
                'id': f'computed_net_income_{as_of_date}_{company_id or "all"}',
                'code': '4800',
                'name': 'Laba/Rugi Tahun Berjalan',
                'subcategory': 'Current Year Earnings',
                'amount': current_year_net_income,
                'category': 'EQUITY',
                'is_computed': True
            })
    except Exception as e:
        logger.error(f"Failed to include current year net income in balance sheet equity: {e}")

    # 2. Add ending inventory from inventory_balances.
    try:
        inv_year = as_of_date_obj.year
        inv_query = text("""
            SELECT ending_inventory_amount
            FROM inventory_balances
            WHERE year = :year AND (:company_id IS NULL OR company_id = :company_id)
            LIMIT 1
        """)

        inv_result = conn.execute(inv_query, {'year': inv_year, 'company_id': company_id}).fetchone()
        if inv_result:
            ending_inv = float(inv_result.ending_inventory_amount or 0)
            if ending_inv > 0:
                add_or_update_asset_item(
                    f'inv_{inv_year}',
                    '1401',
                    'Persediaan (Ending)',
                    'Current Assets',
                    ending_inv,
                    force_current=True
                )
    except Exception as e:
        logger.error(f"Failed to fetch inventory: {e}")

    # 3. Bridge manual amortization items that have not been journalized yet.
    try:
        allow_partial_year = True
        allow_partial_query = text("""
            SELECT setting_value
            FROM amortization_settings
            WHERE setting_name = 'allow_partial_year'
              AND (company_id = :company_id OR company_id IS NULL)
            ORDER BY company_id ASC
        """)
        for row in conn.execute(allow_partial_query, {'company_id': company_id}):
            allow_partial_year = _parse_bool(row.setting_value)

        accumulated_code_by_type = {
            'Building': '1524',
            'Tangible': '1530',
            'LandRights': '1534',
            'Intangible': '1601'
        }

        settings_query = text("""
            SELECT setting_value
            FROM amortization_settings
            WHERE setting_name = 'accumulated_depreciation_coa_codes'
              AND (company_id = :company_id OR company_id IS NULL)
            ORDER BY company_id ASC
        """)
        for row in conn.execute(settings_query, {'company_id': company_id}):
            try:
                parsed = json.loads(row.setting_value)
                if isinstance(parsed, dict):
                    accumulated_code_by_type.update(parsed)
            except Exception:
                continue

        asset_code_by_type = {
            'Building': '1523',
            'Tangible': '1529',
            'LandRights': '1533',
            'Intangible': '1600'
        }

        journaled_descriptions = set()
        if company_id:
            journaled_desc_query = text("""
                SELECT DISTINCT TRIM(REPLACE(t.description, 'Manual Amortization - ', '')) AS item_description
                FROM transactions t
                WHERE t.source_file = 'manual_amortization_journal'
                  AND t.txn_date <= :as_of_date
                  AND t.company_id = :company_id
            """)
            journaled_descriptions = {
                (row.item_description or '').strip()
                for row in conn.execute(journaled_desc_query, {'as_of_date': as_of_date, 'company_id': company_id})
            }

        manual_query = text("""
            SELECT
                ai.id,
                ai.description,
                ai.amount,
                ai.amortization_date,
                ai.use_half_rate,
                ag.asset_type,
                ag.tarif_rate
            FROM amortization_items ai
            LEFT JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
            WHERE ai.is_manual = TRUE
              AND ai.asset_group_id IS NOT NULL
              AND ai.amount > 0
              AND ai.amortization_date IS NOT NULL
              AND ai.amortization_date <= :as_of_date
              AND (:company_id IS NULL OR ai.company_id = :company_id)
            ORDER BY ai.amortization_date ASC
        """)

        asset_totals = {}
        accum_totals = {}

        manual_result = conn.execute(manual_query, {'as_of_date': as_of_date, 'company_id': company_id})
        for row in manual_result:
            description = (row.description or '').strip()
            if company_id and description and description in journaled_descriptions:
                continue

            amount = float(row.amount or 0)
            start_date = _parse_date(row.amortization_date)
            if amount <= 0 or start_date is None:
                continue

            asset_type = row.asset_type or 'Tangible'
            asset_code = asset_code_by_type.get(asset_type, asset_code_by_type['Tangible'])
            accum_code = accumulated_code_by_type.get(asset_type, accumulated_code_by_type['Tangible'])
            rate = float(row.tarif_rate or 20)

            accumulated_amount = _calculate_accumulated_amortization(
                amount,
                rate,
                start_date,
                as_of_date_obj,
                use_half_rate=_parse_bool(row.use_half_rate),
                allow_partial_year=allow_partial_year
            )

            asset_totals[asset_code] = asset_totals.get(asset_code, 0.0) + amount
            accum_totals[accum_code] = accum_totals.get(accum_code, 0.0) - accumulated_amount

        all_codes = list(set(asset_totals.keys()) | set(accum_totals.keys()))
        coa_lookup = {}
        if all_codes:
            coa_query = text("""
                SELECT id, code, name, subcategory
                FROM chart_of_accounts
                WHERE code IN :codes
            """)
            for row in conn.execute(coa_query, {'codes': tuple(all_codes)}):
                coa_lookup[row.code] = dict(row._mapping)

        for code, amount in asset_totals.items():
            coa_info = coa_lookup.get(code, {})
            add_or_update_asset_item(
                coa_info.get('id', f'manual_{code}_asset'),
                code,
                coa_info.get('name', f'Manual Asset ({code})'),
                coa_info.get('subcategory', 'Non-Current Assets'),
                amount,
                force_current=False
            )

        for code, amount in accum_totals.items():
            if abs(amount) < 0.000001:
                continue
            coa_info = coa_lookup.get(code, {})
            add_or_update_asset_item(
                coa_info.get('id', f'manual_{code}_accum'),
                code,
                coa_info.get('name', f'Akumulasi Amortisasi ({code})'),
                coa_info.get('subcategory', 'Non-Current Assets'),
                amount,
                force_current=False
            )
    except Exception as e:
        logger.error(f"Failed to process manual amortization bridge data: {e}")

    # Build ordered asset sections.
    assets_current = []
    assets_non_current = []
    for item in sorted(asset_items.values(), key=lambda x: str(x.get('code') or '')):
        normalized_item = dict(item)
        is_current = normalized_item.pop('is_current', False)
        if is_current:
            assets_current.append(normalized_item)
        else:
            assets_non_current.append(normalized_item)

    # Calculate totals from arrays (more reliable than incremental calculation).
    calculated_assets_total = sum(item.get('amount', 0) for item in assets_current + assets_non_current)
    calculated_liabilities_total = sum(item.get('amount', 0) for item in liabilities_current + liabilities_non_current)
    calculated_equity_total = sum(item.get('amount', 0) for item in equity)
    
    # Also fix top-level totals for frontend compatibility
    total_assets = calculated_assets_total
    total_liabilities = calculated_liabilities_total
    total_equity = calculated_equity_total
    
    return {
        'as_of_date': as_of_date,
        'assets': {
            'current': assets_current,
            'non_current': assets_non_current,
            'total': calculated_assets_total
        },
        'liabilities': {
            'current': liabilities_current,
            'non_current': liabilities_non_current,
            'total': calculated_liabilities_total
        },
        'equity': {
            'items': equity,
            'total': calculated_equity_total
        },
        'current_year_net_income': current_year_net_income,
        'total_assets': total_assets,  # Top-level for frontend compatibility
        'total_liabilities': total_liabilities,  # Top-level for frontend compatibility
        'total_equity': total_equity,  # Top-level for frontend compatibility
        'computed_liabilities': {
            'service_tax_payable': service_tax_payable_computed
        },
        'total_liabilities_and_equity': total_liabilities + total_equity,
        'is_balanced': abs(calculated_assets_total - (calculated_liabilities_total + calculated_equity_total)) < 0.01
    }

def fetch_income_statement_data(conn, start_date, end_date, company_id=None):
    """
    Helper function to fetch income statement data.
    Returns calculated values and lists of items.
    """
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    query = text(f"""
        SELECT 
            coa.code,
            coa.name,
            coa.category,
            coa.subcategory,
            SUM(
                CASE 
                    -- Account posting sign from mapping: debit = +, credit = -
                    WHEN UPPER(COALESCE(mcm.mapping_type, '')) = 'DEBIT' THEN t.amount
                    WHEN UPPER(COALESCE(mcm.mapping_type, '')) = 'CREDIT' THEN -t.amount
                    WHEN t.db_cr = 'DB' THEN t.amount
                    WHEN t.db_cr = 'CR' THEN -t.amount
                    ELSE 0
                END
            ) as signed_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
            AND coa.category IN ('REVENUE', 'EXPENSE')
            AND (:company_id IS NULL OR t.company_id = :company_id)
            {split_exclusion_clause}
        GROUP BY coa.id, coa.code, coa.name, coa.category, coa.subcategory
        ORDER BY coa.code
    """)
    
    result = conn.execute(query, {
        'start_date': start_date,
        'end_date': end_date,
        'company_id': company_id
    })
    
    revenue = []
    expenses = []
    rent_expense_templates = {}
    total_revenue = 0
    total_expenses = 0
    fallback_5314_from_ledger = 0.0

    def merge_expense_item(item):
        for existing in expenses:
            if str(existing.get('code') or '') == str(item.get('code') or ''):
                existing['amount'] = _to_float(existing.get('amount'), 0.0) + _to_float(item.get('amount'), 0.0)
                return
        expenses.append(item)
    
    for row in result:
        d = dict(row._mapping)
        signed_amount = float(d['signed_amount']) if d['signed_amount'] else 0
        # Revenue effect is inverse of account posting sign; expense follows posting sign.
        amount = -signed_amount if d['category'] == 'REVENUE' else signed_amount
        
        item = {
            'code': d['code'],
            'name': d['name'],
            'subcategory': d['subcategory'],
            'amount': amount,
            'category': d['category'] 
        }
        
        if d['category'] == 'REVENUE':
            revenue.append(item)
            total_revenue += amount
        else:  # EXPENSE
            # Skip ledger 5314 in the expense list; we'll inject dynamic 5314 later.
            if d['code'] == '5314':
                fallback_5314_from_ledger += amount
                continue

            if d['code'] in RENT_EXPENSE_CODES:
                rent_expense_templates[d['code']] = {
                    'code': d['code'],
                    'name': d['name'],
                    'subcategory': d['subcategory'],
                    'amount': 0.0,
                    'category': 'EXPENSE'
                }
                continue

            merge_expense_item(item)
            total_expenses += amount

    # Rent expense (5315/5105) is not recognized from full payment amount.
    # For linked rental contracts, recognize only the prorated amount that overlaps the report period.
    for rent_item in _fetch_non_contract_rent_expense_items(conn, start_date, end_date, company_id):
        merge_expense_item(rent_item)
        total_expenses += _to_float(rent_item.get('amount'), 0.0)

    prorated_rent_expense = _calculate_prorated_contract_rent_expense(conn, start_date, end_date, company_id)
    if abs(prorated_rent_expense) >= 0.000001:
        rent_account = _resolve_rent_expense_account(conn, company_id, rent_expense_templates)
        rent_item = {
            'code': rent_account.get('code'),
            'name': rent_account.get('name'),
            'subcategory': rent_account.get('subcategory'),
            'amount': prorated_rent_expense,
            'category': 'EXPENSE'
        }
        merge_expense_item(rent_item)
        total_expenses += prorated_rent_expense
    
    # 2.5 Calculate 5314 (Beban Penyusutan dan Amortisasi) dynamically:
    # total = calculated amortization + manual amortization.
    amortization_breakdown = {
        'report_year': int(str(start_date)[:4]),
        'manual_total': 0.0,
        'calculated_total': 0.0,
        'total_5314': 0.0
    }
    dynamic_calc_ok = True
    try:
        amortization_breakdown = _calculate_dynamic_5314_total(conn, start_date, company_id)
    except Exception as e:
        dynamic_calc_ok = False
        logger.error(f"Failed to calculate dynamic 5314 amount: {e}")
    calculated_amort_total = _to_float(amortization_breakdown.get('calculated_total'), 0.0)
    manual_amort_total = _to_float(amortization_breakdown.get('manual_total'), 0.0)
    dynamic_5314_amount = _to_float(amortization_breakdown.get('total_5314'), 0.0)
    if not dynamic_calc_ok:
        dynamic_5314_amount = fallback_5314_from_ledger
    
    # 2. Handle COGS (HPP) with Manual Inventory Adjustments
    beginning_inv = 0
    ending_inv = 0
    
    # We use start_date's year for the inventory balance
    year = datetime.strptime(start_date, '%Y-%m-%d').year
    
    try:
        inv_balance = _get_inventory_balance_with_carry(conn, year, company_id)
        beginning_inv = _to_float(inv_balance.get('beginning_inventory_amount'), 0.0)
        ending_inv = _to_float(inv_balance.get('ending_inventory_amount'), 0.0)
    except Exception as e:
        logger.error(f"Failed to fetch inventory balances: {e}")

    # Identify 'Purchases' and 'Other COGS' from expenses.
    # Use robust COGS detection (subcategory normalization + 50xx code fallback).
    purchases = 0
    purchases_items = []
    other_cogs_items = []

    cogs_items = [e for e in expenses if _is_cogs_expense_item(e)]

    for item in cogs_items:
        item_code = str(item.get('code') or '').strip()
        if item_code == '5001':
            purchases += _to_float(item.get('amount'), 0.0)
            purchases_items.append(item)
        else:
            other_cogs_items.append(item)
    
    total_other_cogs = sum(item['amount'] for item in other_cogs_items)
    calculate_hpp = beginning_inv + purchases + total_other_cogs - ending_inv
    
    # Provide a specific breakdown for the UI
    cogs_breakdown = {
        'beginning_inventory': beginning_inv,
        'purchases': purchases,
        'purchases_items': purchases_items,
        'other_cogs_items': other_cogs_items,
        'total_other_cogs': total_other_cogs,
        'ending_inventory': ending_inv,
        'total_cogs': calculate_hpp,
        'year': year
    }

    # Filter out COGS items and inject dynamic 5314 amount.
    final_expenses = [
        e for e in expenses
        if not _is_cogs_expense_item(e) and str(e.get('code') or '') != '5314'
    ]
    final_expenses.append({
        'code': '5314',
        'name': 'Beban Penyusutan dan Amortisasi',
        'subcategory': 'Operating Expenses',
        'amount': dynamic_5314_amount,
        'category': 'EXPENSE'
    })
    
    # Calculate total_expenses as the sum of all items in final_expenses list
    # This includes operating expenses, 5314 (amortization), and 5315 (rent)
    # COGS items are handled separately in cogs_breakdown
    total_expenses_calculated = sum(e['amount'] for e in final_expenses)
    
    return {
        'revenue': revenue,
        'expenses': final_expenses,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses_calculated,
        'cogs_breakdown': cogs_breakdown,
        'net_income_components': {
            'formula': 'total_revenue - total_expenses - total_cogs',
            'total_revenue': total_revenue,
            'total_expenses': total_expenses_calculated,
            'total_cogs': calculate_hpp
        },
        'amortization_breakdown': {
            'manual_total': manual_amort_total,
            'calculated_total': calculated_amort_total,
            'total_5314': dynamic_5314_amount,
            'report_year': amortization_breakdown.get('report_year')
        },
        'net_income': total_revenue - total_expenses_calculated - calculate_hpp
    }

def fetch_monthly_revenue_data(conn, year, company_id=None):
    """
    Fetch total revenue grouped by month for a specific year.
    Used for Coretax summary.
    """
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    query = text(f"""
        SELECT 
            MONTH(t.txn_date) as month_num,
            SUM(
                CASE 
                    -- Revenue accounts (normal balance CREDIT, except contra-revenue like 4011)
                    WHEN coa.category = 'REVENUE' AND coa.normal_balance = 'CREDIT' THEN
                        CASE 
                            WHEN t.db_cr = 'CR' THEN t.amount
                            WHEN t.db_cr = 'DB' THEN -t.amount
                            ELSE 0
                        END
                    -- Contra-revenue accounts (normal balance DEBIT, like 4011)
                    WHEN coa.category = 'REVENUE' AND coa.normal_balance = 'DEBIT' THEN
                        CASE 
                            WHEN t.db_cr = 'DB' THEN t.amount
                            WHEN t.db_cr = 'CR' THEN -t.amount
                            ELSE 0
                        END
                    ELSE 0
                END
            ) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE YEAR(t.txn_date) = :year
            AND coa.category = 'REVENUE'
            AND (:company_id IS NULL OR t.company_id = :company_id)
            {split_exclusion_clause}
        GROUP BY MONTH(t.txn_date)
        ORDER BY month_num
    """)
    
    result = conn.execute(query, {
        'year': year,
        'company_id': company_id
    })
    
    # Initialize all months with 0
    monthly_data = {i: 0.0 for i in range(1, 13)}
    
    for row in result:
        d = dict(row._mapping)
        if d['month_num']:
            monthly_data[int(d['month_num'])] = float(d['total_amount']) if d['total_amount'] else 0.0
            
    # Convert to list of objects for easier frontend consumption
    return [
        {'month': m, 'revenue': monthly_data[m]} 
        for m in range(1, 13)
    ]


def fetch_payroll_salary_summary_data(conn, start_date, end_date, company_id=None):
    """
    Fetch payroll summary grouped by month -> employee -> salary component(mark).
    Respects report period and company filter.
    """
    mark_columns = _table_columns(conn, 'marks')
    if 'is_salary_component' not in mark_columns:
        return {
            'period': {'start_date': start_date, 'end_date': end_date},
            'months': [],
            'summary': {
                'total_amount': 0.0,
                'total_transactions': 0,
                'employee_count': 0,
                'month_count': 0
            },
            'message': 'Kolom is_salary_component belum tersedia. Jalankan migrasi terbaru.'
        }

    txn_columns = _table_columns(conn, 'transactions')
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    user_col_expr = "t.sagansa_user_id" if 'sagansa_user_id' in txn_columns else "NULL"
    effective_date_expr = "COALESCE(t.payroll_period_month, t.txn_date)" if 'payroll_period_month' in txn_columns else "t.txn_date"
    if conn.dialect.name == 'sqlite':
        month_key_expr = f"strftime('%Y-%m', {effective_date_expr})"
    else:
        month_key_expr = f"DATE_FORMAT({effective_date_expr}, '%Y-%m')"

    query = text(f"""
        SELECT
            {month_key_expr} AS month_key,
            {user_col_expr} AS sagansa_user_id,
            COALESCE(m.personal_use, m.internal_report, m.tax_report, '(Unnamed Salary Component)') AS mark_name,
            COUNT(t.id) AS transaction_count,
            COALESCE(SUM(ABS(t.amount)), 0) AS total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        WHERE COALESCE(m.is_salary_component, 0) = 1
          AND {effective_date_expr} BETWEEN :start_date AND :end_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion_clause}
        GROUP BY
            {month_key_expr},
            {user_col_expr},
            COALESCE(m.personal_use, m.internal_report, m.tax_report, '(Unnamed Salary Component)')
        ORDER BY
            {month_key_expr} ASC,
            {user_col_expr} ASC
    """)

    user_map = _fetch_sagansa_user_map()
    month_groups = {}
    employee_set = set()
    total_amount = 0.0
    total_transactions = 0

    rows = conn.execute(query, {
        'start_date': start_date,
        'end_date': end_date,
        'company_id': company_id
    })

    for row in rows:
        month_key = str(row.month_key or '').strip()
        if not month_key:
            continue

        user_id = str(row.sagansa_user_id or '').strip() or None
        user_name = user_map.get(user_id, {}).get('name') if user_id else None
        if user_id:
            employee_set.add(user_id)

        mark_name = str(row.mark_name or '').strip() or '(Unnamed Salary Component)'
        tx_count = int(row.transaction_count or 0)
        amount = _to_float(row.total_amount, 0.0)

        if month_key not in month_groups:
            try:
                month_label = datetime.strptime(f"{month_key}-01", '%Y-%m-%d').strftime('%B %Y')
            except Exception:
                month_label = month_key
            month_groups[month_key] = {
                'month_key': month_key,
                'month_label': month_label,
                'transaction_count': 0,
                'total_amount': 0.0,
                'rows': []
            }

        month_groups[month_key]['rows'].append({
            'sagansa_user_id': user_id,
            'sagansa_user_name': user_name or user_id or 'Unassigned',
            'mark_name': mark_name,
            'transaction_count': tx_count,
            'total_amount': amount
        })
        month_groups[month_key]['transaction_count'] += tx_count
        month_groups[month_key]['total_amount'] += amount
        total_transactions += tx_count
        total_amount += amount

    # Ensure each month in requested period exists in output, even without transactions.
    start_obj = _parse_date(start_date)
    end_obj = _parse_date(end_date)
    if start_obj and end_obj and end_obj >= start_obj:
        cursor = start_obj.replace(day=1)
        limit = end_obj.replace(day=1)
        while cursor <= limit:
            month_key = cursor.strftime('%Y-%m')
            if month_key not in month_groups:
                month_groups[month_key] = {
                    'month_key': month_key,
                    'month_label': cursor.strftime('%B %Y'),
                    'transaction_count': 0,
                    'total_amount': 0.0,
                    'rows': []
                }
            if cursor.month == 12:
                cursor = cursor.replace(year=cursor.year + 1, month=1, day=1)
            else:
                cursor = cursor.replace(month=cursor.month + 1, day=1)

    months = []
    for month_key in sorted(month_groups.keys()):
        group = month_groups[month_key]
        group['rows'] = sorted(
            group['rows'],
            key=lambda item: (item.get('sagansa_user_name') or '', item.get('mark_name') or '')
        )
        group['total_amount'] = round(_to_float(group['total_amount'], 0.0), 2)
        months.append(group)

    return {
        'period': {'start_date': start_date, 'end_date': end_date},
        'months': months,
        'summary': {
            'total_amount': round(_to_float(total_amount, 0.0), 2),
            'total_transactions': int(total_transactions),
            'employee_count': len(employee_set),
            'month_count': len(months)
        }
    }


def fetch_cash_flow_data(conn, start_date, end_date, company_id=None):
    """
    Fetch cash flow report using direct method from transaction cash movements.
    Classification heuristic:
      - operating: revenue/expense mappings
      - investing: non-current asset mappings
      - financing: liability/equity mappings
      - unclassified: no mapping signal
    """
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    section_names = {
        'operating': 'Operating Activities',
        'investing': 'Investing Activities',
        'financing': 'Financing Activities',
        'unclassified': 'Unclassified'
    }
    ordered_sections = ['operating', 'investing', 'financing', 'unclassified']

    transactions_query = text(f"""
        SELECT
            t.id,
            t.txn_date,
            t.description,
            t.amount,
            t.db_cr,
            t.company_id,
            c.name AS company_name,
            m.personal_use,
            m.internal_report,
            MAX(CASE WHEN coa.category IN ('REVENUE', 'EXPENSE') THEN 1 ELSE 0 END) AS operating_flag,
            MAX(CASE WHEN coa.category = 'ASSET'
                      AND NOT (
                        coa.code LIKE '11%%'
                        OR coa.code LIKE '12%%'
                        OR coa.code LIKE '13%%'
                        OR coa.code LIKE '14%%'
                      )
                     THEN 1 ELSE 0 END) AS investing_flag,
            MAX(CASE WHEN coa.category IN ('LIABILITY', 'EQUITY') THEN 1 ELSE 0 END) AS financing_flag
        FROM transactions t
        LEFT JOIN companies c ON t.company_id = c.id
        LEFT JOIN marks m ON t.mark_id = m.id
        LEFT JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        LEFT JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion_clause}
        GROUP BY
            t.id, t.txn_date, t.description, t.amount, t.db_cr,
            t.company_id, c.name, m.personal_use, m.internal_report
        ORDER BY t.txn_date ASC, t.id ASC
    """)

    rows = conn.execute(transactions_query, {
        'start_date': start_date,
        'end_date': end_date,
        'company_id': company_id
    })

    sections = {
        key: {
            'name': section_names[key],
            'inflow_total': 0.0,
            'outflow_total': 0.0,
            'net_cash': 0.0,
            'count': 0,
            'items': []
        }
        for key in ordered_sections
    }

    for row in rows:
        amount = abs(_to_float(row.amount, 0.0))
        db_cr = str(row.db_cr or '').upper().strip()
        signed_amount = amount if db_cr == 'DB' else (-amount if db_cr == 'CR' else 0.0)
        inflow = signed_amount if signed_amount > 0 else 0.0
        outflow = abs(signed_amount) if signed_amount < 0 else 0.0

        if int(row.investing_flag or 0) == 1:
            section_key = 'investing'
        elif int(row.financing_flag or 0) == 1:
            section_key = 'financing'
        elif int(row.operating_flag or 0) == 1:
            section_key = 'operating'
        else:
            section_key = 'unclassified'

        section = sections[section_key]
        section['inflow_total'] += inflow
        section['outflow_total'] += outflow
        section['count'] += 1
        section['items'].append({
            'id': str(row.id),
            'txn_date': row.txn_date.isoformat() if isinstance(row.txn_date, (datetime, date)) else str(row.txn_date or ''),
            'description': row.description,
            'amount': amount,
            'db_cr': db_cr,
            'signed_amount': signed_amount,
            'company_id': row.company_id,
            'company_name': row.company_name,
            'mark_name': row.personal_use or row.internal_report
        })

    for key in ordered_sections:
        section = sections[key]
        section['net_cash'] = section['inflow_total'] - section['outflow_total']
        section['inflow_total'] = round(section['inflow_total'], 2)
        section['outflow_total'] = round(section['outflow_total'], 2)
        section['net_cash'] = round(section['net_cash'], 2)

    opening_query = text(f"""
        SELECT
            COALESCE(SUM(
                CASE
                    WHEN t.db_cr = 'DB' THEN t.amount
                    WHEN t.db_cr = 'CR' THEN -t.amount
                    ELSE 0
                END
            ), 0) AS opening_cash
        FROM transactions t
        WHERE t.txn_date < :start_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion_clause}
    """)
    opening_row = conn.execute(opening_query, {'start_date': start_date, 'company_id': company_id}).fetchone()
    opening_cash = _to_float(opening_row.opening_cash if opening_row else 0.0, 0.0)

    closing_query = text(f"""
        SELECT
            COALESCE(SUM(
                CASE
                    WHEN t.db_cr = 'DB' THEN t.amount
                    WHEN t.db_cr = 'CR' THEN -t.amount
                    ELSE 0
                END
            ), 0) AS closing_cash
        FROM transactions t
        WHERE t.txn_date <= :end_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion_clause}
    """)
    closing_row = conn.execute(closing_query, {'end_date': end_date, 'company_id': company_id}).fetchone()
    closing_cash = _to_float(closing_row.closing_cash if closing_row else 0.0, 0.0)

    operating_net = sections['operating']['net_cash']
    investing_net = sections['investing']['net_cash']
    financing_net = sections['financing']['net_cash']
    unclassified_net = sections['unclassified']['net_cash']
    net_change_by_sections = operating_net + investing_net + financing_net + unclassified_net
    net_change_by_balance = closing_cash - opening_cash

    return {
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'sections': sections,
        'section_order': ordered_sections,
        'summary': {
            'opening_cash': round(opening_cash, 2),
            'operating_net': round(operating_net, 2),
            'investing_net': round(investing_net, 2),
            'financing_net': round(financing_net, 2),
            'unclassified_net': round(unclassified_net, 2),
            'net_change': round(net_change_by_sections, 2),
            'closing_cash': round(closing_cash, 2),
            'reconciliation_difference': round(net_change_by_balance - net_change_by_sections, 2)
        }
    }
