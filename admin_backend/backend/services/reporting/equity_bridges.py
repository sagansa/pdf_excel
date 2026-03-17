import logging

from sqlalchemy import text

from backend.db.schema import get_table_columns
from backend.services.reporting.income_statement_service import fetch_income_statement_data
from backend.services.reporting.rental_adjustments import _calculate_rental_tax_breakdown
from backend.services.reporting.report_value_utils import _is_current_asset
from backend.services.reporting.service_tax_adjustments import (
    _calculate_service_tax_payable_as_of,
    _resolve_service_tax_payable_account,
)

logger = logging.getLogger(__name__)


def add_or_update_asset_item(asset_items, item_id, code, name, subcategory, amount, force_current=None):
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
        'is_current': is_current,
    }


def add_or_update_liability_item(liabilities_current, liabilities_non_current, item_id, code, name, subcategory, amount, force_current=True):
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
        'category': 'LIABILITY',
    })


def apply_service_tax_payable_bridge(conn, liabilities_current, liabilities_non_current, as_of_date, company_id, report_type):
    service_tax_payable_computed = 0.0
    try:
        service_tax_payable = _calculate_service_tax_payable_as_of(conn, as_of_date, company_id, report_type)
        service_tax_payable_computed = float(service_tax_payable or 0.0)
        if abs(service_tax_payable_computed) >= 0.000001:
            service_tax_coa = _resolve_service_tax_payable_account(
                conn, company_id, preferred_setting='service_tax_payable_coa'
            )
            add_or_update_liability_item(
                liabilities_current,
                liabilities_non_current,
                service_tax_coa.get('id') or f'computed_service_tax_{as_of_date}_{company_id or "all"}',
                service_tax_coa.get('code') or '2191',
                service_tax_coa.get('name') or 'Utang PPh Jasa',
                service_tax_coa.get('subcategory') or 'Current Liabilities',
                service_tax_payable_computed,
                force_current=True,
            )
    except Exception as exc:
        logger.error('Failed to include service tax payable in balance sheet: %s', exc)
    return service_tax_payable_computed


def resolve_prepaid_asset_code(conn, company_id):
    prepaid_code = '1421'
    try:
        if get_table_columns(conn, 'amortization_settings'):
            setting_row = conn.execute(text("""
                SELECT setting_value
                FROM amortization_settings
                WHERE setting_name = 'prepaid_prepaid_asset_coa'
                  AND (company_id = :company_id OR company_id IS NULL)
                ORDER BY company_id DESC
                LIMIT 1
            """), {'company_id': company_id}).fetchone()
            if setting_row and setting_row[0]:
                prepaid_code = str(setting_row[0]).strip()
    except Exception:
        pass
    return prepaid_code


def apply_rental_tax_bridge(conn, asset_items, liabilities_current, liabilities_non_current, as_of_date, company_id, report_type):
    try:
        tax_breakdown = _calculate_rental_tax_breakdown(conn, as_of_date, company_id, report_type)
        total_tax = float(tax_breakdown.get('total_tax', 0.0))
        unpaid_tax = float(tax_breakdown.get('unpaid_tax', 0.0))
        paid_tax = float(tax_breakdown.get('paid_tax', 0.0))
        prepaid_code = resolve_prepaid_asset_code(conn, company_id)
        cash_code = '1101'

        if abs(total_tax) >= 0.000001:
            if prepaid_code in asset_items:
                asset_items[prepaid_code]['amount'] += total_tax
            else:
                add_or_update_asset_item(
                    asset_items,
                    f'computed_prepaid_tax_{as_of_date}_{company_id or "all"}',
                    prepaid_code,
                    'Biaya Dibayar di Muka',
                    'Prepaid Expenses',
                    total_tax,
                    force_current=True,
                )

        if abs(unpaid_tax) >= 0.000001:
            rental_tax_coa = _resolve_service_tax_payable_account(
                conn, company_id, preferred_setting='prepaid_tax_payable_coa'
            )
            add_or_update_liability_item(
                liabilities_current,
                liabilities_non_current,
                f'computed_rental_tax_{as_of_date}_{company_id or "all"}',
                rental_tax_coa.get('code') or '2191',
                rental_tax_coa.get('name') or 'Utang PPh Final Pasal 4(2)',
                rental_tax_coa.get('subcategory') or 'Current Liabilities',
                unpaid_tax,
                force_current=True,
            )

        if abs(paid_tax) >= 0.000001 and cash_code in asset_items:
            asset_items[cash_code]['amount'] -= paid_tax
    except Exception as exc:
        logger.error('Failed to include rental tax bridging in balance sheet: %s', exc)


def append_current_year_net_income(conn, equity, as_of_date_obj, as_of_date, company_id, report_type):
    current_year_net_income = 0.0
    try:
        year_start = as_of_date_obj.replace(month=1, day=1).strftime('%Y-%m-%d')
        income_statement_data = fetch_income_statement_data(
            conn, year_start, as_of_date, company_id, report_type, comparative=False
        )
        current_year_net_income = float(income_statement_data.get('net_income') or 0.0)
        if abs(current_year_net_income) >= 0.000001:
            equity.append({
                'id': f'computed_net_income_{as_of_date}_{company_id or "all"}',
                'code': '4800',
                'name': 'Laba/Rugi Tahun Berjalan',
                'subcategory': 'Current Year Earnings',
                'amount': current_year_net_income,
                'category': 'EQUITY',
                'is_computed': True,
            })
    except Exception as exc:
        logger.error('Failed to include current year net income in balance sheet equity: %s', exc)
    return current_year_net_income


def append_previous_year_retained_earnings(conn, equity, as_of_date_obj, company_id, report_type):
    try:
        report_year = as_of_date_obj.year
        company_start_year = report_year - 1
        configured_previous_retained_earnings = 0.0
        start_year_result = conn.execute(text("""
            SELECT MIN(start_year) AS min_start_year,
                   COALESCE(SUM(previous_retained_earnings_amount), 0) AS configured_previous_retained_earnings
            FROM initial_capital_settings
            WHERE company_id = :company_id AND report_type = :report_type
        """), {'company_id': company_id, 'report_type': report_type}).fetchone()
        if start_year_result and start_year_result.min_start_year:
            company_start_year = int(start_year_result.min_start_year)
            configured_previous_retained_earnings = float(
                start_year_result.configured_previous_retained_earnings or 0.0
            )

        if report_year <= company_start_year:
            previous_year_retained_earnings = configured_previous_retained_earnings
        else:
            previous_year_retained_earnings = configured_previous_retained_earnings
            for year in range(company_start_year, report_year):
                year_income_statement = fetch_income_statement_data(
                    conn,
                    f'{year}-01-01',
                    f'{year}-12-31',
                    company_id,
                    report_type,
                    comparative=False,
                )
                previous_year_retained_earnings += float(year_income_statement.get('net_income') or 0.0)

        if abs(previous_year_retained_earnings) >= 0.000001:
            equity.append({
                'id': f'computed_prev_retained_earnings_{as_of_date_obj}_{company_id or "all"}',
                'code': '3200',
                'name': 'Laba Ditahan Tahun Sebelumnya',
                'subcategory': 'Retained Earnings',
                'amount': previous_year_retained_earnings,
                'category': 'EQUITY',
                'is_computed': True,
            })
    except Exception as exc:
        logger.error('Failed to include previous year retained earnings in balance sheet equity: %s', exc)


def prepend_initial_capital(conn, equity, as_of_date_obj, company_id, report_type='real'):
    try:
        initial_capital_result = conn.execute(text("""
            SELECT amount, start_year, description
            FROM initial_capital_settings
            WHERE company_id = :company_id AND report_type = :report_type
        """), {'company_id': company_id, 'report_type': report_type}).fetchone()
        if not initial_capital_result:
            return

        initial_capital_amount = float(initial_capital_result.amount or 0)
        start_year = int(initial_capital_result.start_year or 0)
        description = initial_capital_result.description or 'Modal Setor di Awal'

        if as_of_date_obj.year >= start_year and abs(initial_capital_amount) >= 0.000001:
            equity.insert(0, {
                'id': f'initial_capital_{company_id}',
                'code': '3100',
                'name': description,
                'subcategory': 'Paid-in Capital',
                'amount': initial_capital_amount,
                'category': 'EQUITY',
                'is_computed': False,
            })
    except Exception as exc:
        logger.error('Failed to include initial capital in balance sheet equity: %s', exc)


def apply_ending_inventory_bridge(conn, asset_items, as_of_date_obj, company_id):
    try:
        inv_result = conn.execute(text("""
            SELECT ending_inventory_amount
            FROM inventory_balances
            WHERE year = :year AND (:company_id IS NULL OR company_id = :company_id)
            LIMIT 1
        """), {'year': as_of_date_obj.year, 'company_id': company_id}).fetchone()
        if not inv_result:
            return

        ending_inv = float(inv_result.ending_inventory_amount or 0)
        if ending_inv > 0:
            add_or_update_asset_item(
                asset_items,
                f'inv_{as_of_date_obj.year}',
                '1401',
                'Persediaan (Ending)',
                'Current Assets',
                ending_inv,
                force_current=True,
            )
    except Exception as exc:
        logger.error('Failed to fetch inventory: %s', exc)
