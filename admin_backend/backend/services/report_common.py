import logging
import json
import os
import re
from datetime import datetime, date, timedelta
from sqlalchemy import text
from backend.db.session import get_sagansa_engine
from backend.db.schema import get_table_columns

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

def _split_parent_exclusion_clause(conn, alias='t'):
    txn_columns = get_table_columns(conn, 'transactions')
    if 'parent_id' not in txn_columns:
        return ''
    return f" AND NOT EXISTS (SELECT 1 FROM transactions t_child WHERE t_child.parent_id = {alias}.id)"


def _coretax_filter_clause(conn, report_type='real', alias='m'):
    if str(report_type).strip().lower() != 'coretax':
        return ""

    mark_columns = get_table_columns(conn, 'marks')
    if 'is_coretax' in mark_columns:
        if conn.dialect.name == 'sqlite':
            return f" AND LOWER(COALESCE(CAST({alias}.is_coretax AS TEXT), '0')) IN ('1', 'true', 'yes', 'y')"
        return f" AND LOWER(COALESCE(CAST({alias}.is_coretax AS CHAR), '0')) IN ('1', 'true', 'yes', 'y')"

    return f" AND ({alias}.tax_report IS NOT NULL AND TRIM({alias}.tax_report) != '')"


def _mapping_report_type_expr(conn, alias, fallback='real'):
    if conn.dialect.name == 'sqlite':
        return f"LOWER(COALESCE(CAST({alias}.report_type AS TEXT), '{fallback}'))"
    return f"LOWER(COALESCE(CAST({alias}.report_type AS CHAR), '{fallback}'))"


def _mark_coa_join_clause(conn, report_type='real', mark_ref='m.id', mapping_alias='mcm', join_type='INNER'):
    mapping_columns = get_table_columns(conn, 'mark_coa_mapping')
    normalized_report_type = str(report_type or 'real').strip().lower()
    if normalized_report_type != 'coretax':
        normalized_report_type = 'real'

    if 'report_type' not in mapping_columns:
        return f"{join_type} JOIN mark_coa_mapping {mapping_alias} ON {mapping_alias}.mark_id = {mark_ref}"

    mapping_scope_expr = _mapping_report_type_expr(conn, mapping_alias, 'real')

    if normalized_report_type == 'coretax':
        fallback_alias = f"{mapping_alias}_coretax"
        fallback_scope_expr = _mapping_report_type_expr(conn, fallback_alias, 'real')
        return f"""
        {join_type} JOIN mark_coa_mapping {mapping_alias}
            ON {mapping_alias}.mark_id = {mark_ref}
           AND (
                {mapping_scope_expr} = 'coretax'
                OR (
                    {mapping_scope_expr} = 'real'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM mark_coa_mapping {fallback_alias}
                        WHERE {fallback_alias}.mark_id = {mark_ref}
                          AND {fallback_scope_expr} = 'coretax'
                          AND UPPER(COALESCE({fallback_alias}.mapping_type, '')) = UPPER(COALESCE({mapping_alias}.mapping_type, ''))
                    )
                )
           )
        """

    return f"""
    {join_type} JOIN mark_coa_mapping {mapping_alias}
        ON {mapping_alias}.mark_id = {mark_ref}
       AND {mapping_scope_expr} = 'real'
    """


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
    if amount == 0 or rate <= 0 or start_date is None or start_date > as_of_date:
        return 0.0

    is_negative = amount < 0
    abs_amount = abs(amount)

    annual_base = abs_amount * (rate / 100.0)
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

        remaining = max(abs_amount - accumulated, 0.0)
        if remaining <= 0:
            break
        accumulated += min(year_amort, remaining)

    final_accumulated = max(0.0, min(accumulated, abs_amount))
    return -final_accumulated if is_negative else final_accumulated


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
    use_mark_based_amortization = False

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
        elif setting_name == 'use_mark_based_amortization':
            use_mark_based_amortization = _parse_bool(setting_value)

    return default_rate, allow_partial_year, use_mark_based_amortization


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
    if amount == 0 or rate <= 0:
        return 0.0

    start_date = _parse_date(start_date_value)
    if start_date is None:
        start_date = date(report_year, 1, 1)

    acquisition_year = start_date.year
    if acquisition_year > report_year:
        return 0.0

    is_negative = amount < 0
    abs_amount = abs(amount)

    annual_amort_base = abs_amount * (rate / 100.0)
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

        remaining = abs_amount - accumulated_prev
        year_amort = min(year_amort, max(remaining, 0.0))

        if year < report_year:
            accumulated_prev += year_amort
        else:
            current_year_amort = year_amort

    final_current = max(current_year_amort, 0.0)
    return -final_current if is_negative else final_current


def _calculate_dynamic_5314_total(conn, start_date, end_date=None, company_id=None, report_type='real'):
    report_year = int(str(start_date)[:4])
    default_rate, allow_partial_year, use_mark_based_amortization = _load_amortization_calculation_settings(conn, company_id)

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
    if str(report_type).strip().lower() != 'coretax':
        manual_rows = conn.execute(manual_query, company_params)
    else:
        manual_rows = []

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

    calculated_total = 0.0

    # Calculate from transactions directly only if enabled
    if use_mark_based_amortization:
        # Check if we're dealing with a multi-year income statement by analyzing the call context
        # This is called from income statement with date range start_date to end_date
        # We'll use a safer approach that covers the full period
        if conn.dialect.name == 'sqlite':
            txn_year_clause = "CAST(strftime('%Y', t.txn_date) AS INTEGER) <= YEAR(DATE(:start_date, '+3 year'))"
        else:
            txn_year_clause = "YEAR(t.txn_date) <= :report_year"
    
        txn_company_clause = "AND t.company_id = :company_id" if company_id else ""
        coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
        mark_coa_join = _mark_coa_join_clause(
            conn,
            report_type,
            mark_ref='t.mark_id',
            mapping_alias='mcm',
            join_type='INNER'
        )
        txn_query = text(f"""
            SELECT DISTINCT
                t.id,
                CASE WHEN t.db_cr = 'CR' THEN -t.amount ELSE t.amount END AS acquisition_cost,
                t.amortization_start_date,
                t.txn_date,
                t.use_half_rate,
                ag.tarif_rate
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            {mark_coa_join}
            INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            LEFT JOIN amortization_asset_groups ag ON t.amortization_asset_group_id = ag.id
            WHERE coa.code = '5314'
              {txn_company_clause}
              AND {txn_year_clause}
              {coretax_clause}
        """)
        txn_params = {'report_year': report_year}
        if company_id:
            txn_params['company_id'] = company_id
    
        for row in conn.execute(txn_query, txn_params):
            base_amount = _to_float(row.acquisition_cost, 0.0)
            if base_amount == 0:
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
    
    if str(report_type).strip().lower() != 'coretax':
        asset_rows = conn.execute(assets_query, asset_params)
    else:
        asset_rows = []

    for row in asset_rows:
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


def _get_inventory_balance_with_carry(conn, year, company_id=None, report_type='real'):
    # Inventory balances are shared manual adjustments (not split by report_type),
    # so Coretax should reuse the same values as Real.
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


