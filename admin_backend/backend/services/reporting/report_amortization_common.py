from datetime import date

from sqlalchemy import text

from backend.services.reporting.report_sql_fragments import (
    _coretax_filter_clause,
    _mark_coa_join_clause,
)
from backend.services.reporting.report_value_utils import (
    _parse_bool,
    _parse_date,
    _to_float,
)


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


def _calculate_current_year_amortization(
    base_amount,
    tarif_rate,
    start_date_value,
    report_year,
    use_half_rate=False,
    allow_partial_year=True,
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
                allow_partial_year=allow_partial_year,
            )
        else:
            annual_amort = amount

        manual_total += annual_amort

    calculated_total = 0.0
    if use_mark_based_amortization:
        if conn.dialect.name == 'sqlite':
            txn_year_clause = "CAST(strftime('%Y', t.txn_date) AS INTEGER) <= YEAR(DATE(:start_date, '+3 year'))"
        else:
            txn_year_clause = "YEAR(t.txn_date) <= :report_year"

        txn_company_clause = "AND t.company_id = :company_id" if company_id else ""
        coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
        mark_coa_join = _mark_coa_join_clause(conn, report_type, mark_ref='t.mark_id', mapping_alias='mcm', join_type='INNER')
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
                allow_partial_year=allow_partial_year,
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
            allow_partial_year=allow_partial_year,
        )

    total_5314 = manual_total + calculated_total
    return {
        'report_year': report_year,
        'manual_total': manual_total,
        'calculated_total': calculated_total,
        'total_5314': total_5314,
    }
