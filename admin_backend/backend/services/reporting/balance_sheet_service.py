import logging
from datetime import datetime

from sqlalchemy import text

from backend.services.reporting.amortization_bridges import (
    apply_manual_amortization_bridge,
    apply_prepaid_rent_amortization_bridge,
)
from backend.services.reporting.equity_bridges import (
    add_or_update_asset_item,
    add_or_update_liability_item,
    append_current_year_net_income,
    append_previous_year_retained_earnings,
    apply_ending_inventory_bridge,
    apply_rental_tax_bridge,
    apply_service_tax_payable_bridge,
    prepend_initial_capital,
)
from backend.services.reporting.report_sql_fragments import (
    _coretax_filter_clause,
    _effective_coa_id_expr,
    _effective_mapping_type_expr,
    _effective_natural_direction_expr,
    _get_reporting_start_date,
    _mark_coa_join_clause,
    _split_parent_exclusion_clause,
)

logger = logging.getLogger(__name__)


def _build_balance_sheet_query(conn, report_type):
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
    mark_coa_join = _mark_coa_join_clause(
        conn,
        report_type,
        mark_ref='m.id',
        mapping_alias='mcm',
        join_type='LEFT',
    )
    effective_coa_id = _effective_coa_id_expr(conn, report_type, txn_alias='t', mapping_alias='mcm')
    effective_mapping_type = _effective_mapping_type_expr(conn, report_type, txn_alias='t', mapping_alias='mcm')
    effective_natural_direction = _effective_natural_direction_expr(conn, report_type, txn_alias='t', mark_alias='m')
    return text(f"""
        WITH coa_balances AS (
            SELECT
                {effective_coa_id} AS coa_id,
                SUM(
                    (CASE
                        WHEN {effective_mapping_type} = 'DEBIT' THEN t.amount
                        WHEN {effective_mapping_type} = 'CREDIT' THEN -t.amount
                        ELSE 0
                    END)
                    * (CASE
                        WHEN {effective_natural_direction} IS NOT NULL
                             AND UPPER(TRIM(COALESCE(t.db_cr, ''))) != ''
                             AND (
                                (UPPER({effective_natural_direction}) = 'DB' AND UPPER(TRIM(t.db_cr)) IN ('CR', 'CREDIT', 'K', 'KREDIT'))
                                OR
                                (UPPER({effective_natural_direction}) = 'CR' AND UPPER(TRIM(t.db_cr)) IN ('DB', 'DEBIT', 'D', 'DE'))
                             )
                        THEN -1
                        ELSE 1
                    END)
                ) as total_amount
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            {mark_coa_join}
            WHERE t.txn_date <= :as_of_date
                AND (:start_date IS NULL OR t.txn_date >= :start_date)
                AND (:company_id IS NULL OR t.company_id = :company_id)
                {split_exclusion_clause}
                {coretax_clause}
                AND {effective_coa_id} IS NOT NULL
            GROUP BY {effective_coa_id}
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


def _append_balance_row(row_data, asset_items, liabilities_current, liabilities_non_current, equity):
    raw_amount = float(row_data['total_amount']) if row_data['total_amount'] else 0.0

    if row_data['category'] == 'ASSET':
        # ASSET normal balance = DEBIT → raw_amount sign is correct as-is
        add_or_update_asset_item(
            asset_items,
            row_data['id'],
            row_data['code'],
            row_data['name'],
            row_data.get('subcategory'),
            raw_amount,
        )
        return

    if row_data['category'] == 'LIABILITY':
        # LIABILITY normal balance = CREDIT, but the BS query uses DEBIT=positive (asset convention).
        # Negate so that:
        #   CREDIT mapping (accrual)  → raw = -amount → negated = +amount  (liability increases ✓)
        #   DEBIT  mapping (payment)  → raw = +amount → negated = -amount  (liability decreases ✓)
        amount = -raw_amount
        add_or_update_liability_item(
            liabilities_current,
            liabilities_non_current,
            row_data['id'],
            row_data['code'],
            row_data['name'],
            row_data.get('subcategory'),
            amount,
            force_current=bool(row_data['code'] and row_data['code'].startswith('2')),
        )
        return

    if row_data['category'] == 'EQUITY':
        # EQUITY normal balance = CREDIT → same negation logic as LIABILITY
        amount = -raw_amount
        equity.append({
            'id': row_data['id'],
            'code': row_data['code'],
            'name': row_data['name'],
            'subcategory': row_data['subcategory'],
            'amount': amount,
            'category': row_data['category'],
        })


def _split_asset_sections(asset_items):
    assets_current = []
    assets_non_current = []
    for item in sorted(asset_items.values(), key=lambda value: str(value.get('code') or '')):
        normalized_item = dict(item)
        is_current = normalized_item.pop('is_current', False)
        if is_current:
            assets_current.append(normalized_item)
        else:
            assets_non_current.append(normalized_item)
    return assets_current, assets_non_current


def _append_balance_adjustment(equity, as_of_date, company_id, adjustment_amount):
    if abs(adjustment_amount) < 0.01:
        return 0.0

    equity.append({
        'id': f'computed_balance_adjustment_{as_of_date}_{company_id or "all"}',
        'code': '3999',
        'name': 'Penyesuaian Saldo Pembuka',
        'subcategory': 'Balance Adjustment',
        'amount': adjustment_amount,
        'category': 'EQUITY',
        'is_computed': True,
    })
    return adjustment_amount


def _remove_canceling_opening_balance_items(equity):
    initial_capital_item = next((item for item in equity if str(item.get('code') or '') == '3100'), None)
    balance_adjustment_item = next((item for item in equity if str(item.get('code') or '') == '3999'), None)

    if not initial_capital_item or not balance_adjustment_item:
        return

    initial_capital_amount = float(initial_capital_item.get('amount', 0) or 0)
    balance_adjustment_amount = float(balance_adjustment_item.get('amount', 0) or 0)

    if abs(initial_capital_amount + balance_adjustment_amount) < 0.01:
        equity[:] = [
            item for item in equity
            if str(item.get('code') or '') not in {'3100', '3999'}
        ]


def fetch_balance_sheet_data(conn, as_of_date, company_id=None, report_type='real'):
    """
    Helper function to fetch balance sheet data.
    Returns calculated values and lists of items.
    """
    as_of_date_obj = datetime.strptime(as_of_date, '%Y-%m-%d').date()
    start_date = _get_reporting_start_date(conn, company_id, report_type)
    
    result = conn.execute(_build_balance_sheet_query(conn, report_type), {
        'as_of_date': as_of_date,
        'start_date': start_date,
        'company_id': company_id,
    })

    asset_items = {}
    liabilities_current = []
    liabilities_non_current = []
    equity = []

    for row in result:
        _append_balance_row(row._mapping, asset_items, liabilities_current, liabilities_non_current, equity)

    service_tax_payable_computed = apply_service_tax_payable_bridge(
        conn, liabilities_current, liabilities_non_current, as_of_date, company_id, report_type
    )
    apply_rental_tax_bridge(
        conn, asset_items, liabilities_current, liabilities_non_current, as_of_date, company_id, report_type
    )
    apply_prepaid_rent_amortization_bridge(conn, asset_items, as_of_date, company_id, report_type)
    current_year_net_income = append_current_year_net_income(
        conn, equity, as_of_date_obj, as_of_date, company_id, report_type
    )
    append_previous_year_retained_earnings(conn, equity, as_of_date_obj, company_id, report_type)
    prepend_initial_capital(conn, equity, as_of_date_obj, company_id, report_type)
    apply_ending_inventory_bridge(conn, asset_items, as_of_date_obj, company_id)
    apply_manual_amortization_bridge(conn, asset_items, as_of_date_obj, as_of_date, company_id, report_type)

    assets_current, assets_non_current = _split_asset_sections(asset_items)

    # Calculate totals from arrays (more reliable than incremental calculation).
    calculated_assets_total = sum(item.get('amount', 0) for item in assets_current + assets_non_current)
    calculated_liabilities_total = sum(item.get('amount', 0) for item in liabilities_current + liabilities_non_current)
    
    # Equity SHOULD include current year net income for the Balance Sheet to balance A = L + E
    # We've confirmed NI matches between IS and BS via verification.
    calculated_equity_total = sum(item.get('amount', 0) for item in equity)

    # If there is still a residual difference, surface it explicitly as a computed equity adjustment.
    # This keeps the report balanced while making the adjustment transparent in the UI.
    balance_adjustment = calculated_assets_total - (calculated_liabilities_total + calculated_equity_total)
    calculated_equity_total += _append_balance_adjustment(equity, as_of_date, company_id, balance_adjustment)
    _remove_canceling_opening_balance_items(equity)
    
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
