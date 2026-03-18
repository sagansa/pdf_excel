import logging
from datetime import datetime

from sqlalchemy import text

from backend.db.schema import get_table_columns
from backend.services.reporting.rental_adjustments import (
    _calculate_prorated_contract_rent_expense,
    _fetch_non_contract_rent_expense_items,
    _resolve_rent_expense_account,
)
from backend.services.reporting.report_amortization_common import _calculate_dynamic_5314_total
from backend.services.reporting.report_inventory_common import _get_inventory_balance_with_carry
from backend.services.reporting.report_sql_fragments import (
    _coretax_filter_clause,
    _mark_coa_join_clause,
    _split_parent_exclusion_clause,
)
from backend.services.reporting.report_value_utils import (
    RENT_EXPENSE_CODES,
    _is_cogs_expense_item,
    _to_float,
)
from backend.services.reporting.service_tax_adjustments import _calculate_service_tax_adjustment_for_period

logger = logging.getLogger(__name__)


def _is_coa_mapped_for_report(conn, coa_code, report_type):
    """
    Checks if a COA code is explicitly mapped in mark_coa_mapping for a given report_type.
    'real' report_type is always considered mapped.
    """
    if report_type == 'real':
        return True
        
    query = text("""
        SELECT COUNT(*) 
        FROM mark_coa_mapping mcm
        JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE coa.code = :code AND mcm.report_type = :report_type
    """)
    result = conn.execute(query, {'code': coa_code, 'report_type': report_type}).scalar()
    return (result or 0) > 0


def _previous_period(start_date, end_date):
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    return (
        start_date_obj.replace(year=start_date_obj.year - 1).strftime('%Y-%m-%d'),
        end_date_obj.replace(year=end_date_obj.year - 1).strftime('%Y-%m-%d'),
    )


def _merge_comparative_items(current_items, previous_items):
    prev_lookup = {item['code']: item['amount'] for item in previous_items}
    curr_lookup = {item['code']: item for item in current_items}
    previous_item_lookup = {item['code']: item for item in previous_items}

    merged_items = []
    for code in sorted(set(prev_lookup.keys()) | set(curr_lookup.keys())):
        if code in curr_lookup:
            item = curr_lookup[code].copy()
            item['previous_year_amount'] = prev_lookup.get(code, 0.0)
        else:
            item = previous_item_lookup[code].copy()
            item['amount'] = 0.0
            item['previous_year_amount'] = prev_lookup.get(code, 0.0)
        merged_items.append(item)
    return merged_items


def _merge_comparative_cogs(current_data, previous_year_data):
    if 'cogs_breakdown' not in current_data or 'cogs_breakdown' not in previous_year_data:
        return

    prev_cogs = previous_year_data['cogs_breakdown']
    prev_items = (prev_cogs.get('purchases_items', []) or []) + (prev_cogs.get('other_cogs_items', []) or [])

    prev_cogs_lookup = {}
    for item in prev_items:
        code = str(item.get('code') or '').strip()
        if not code:
            continue
        prev_cogs_lookup[code] = prev_cogs_lookup.get(code, 0.0) + _to_float(item.get('amount'), 0.0)

    for list_key in ('purchases_items', 'other_cogs_items'):
        for item in current_data['cogs_breakdown'].get(list_key, []) or []:
            code = str(item.get('code') or '').strip()
            item['previous_year_amount'] = prev_cogs_lookup.get(code, 0.0)

    current_data['cogs_breakdown']['previous_year_purchases'] = _to_float(
        prev_cogs.get('total_cogs', prev_cogs.get('purchases', 0.0)), 0.0
    )


def _apply_comparative_data(current_data, previous_year_data):
    current_data['revenue'] = _merge_comparative_items(current_data['revenue'], previous_year_data['revenue'])
    current_data['expenses'] = _merge_comparative_items(current_data['expenses'], previous_year_data['expenses'])
    current_data['previous_year_total_revenue'] = previous_year_data['total_revenue']
    current_data['previous_year_total_expenses'] = previous_year_data['total_expenses']
    current_data['previous_year_net_income'] = previous_year_data['net_income']
    _merge_comparative_cogs(current_data, previous_year_data)
    logger.debug(
        "[Income Statement] Merged comparative data revenue_count=%s expense_count=%s",
        len(current_data['revenue']),
        len(current_data['expenses']),
    )


def _build_income_statement_query(conn, report_type, split_exclusion_clause, coretax_clause):
    txn_columns = get_table_columns(conn, 'transactions')
    parent_join = ""
    company_ref = "t.company_id"
    def normalize_mark_ref(expr):
        if conn.dialect.name == 'sqlite':
            return f"NULLIF(TRIM(CAST({expr} AS TEXT)), '')"
        return f"NULLIF(TRIM(CAST({expr} AS CHAR)), '')"

    if 'parent_id' in txn_columns:
        # Join parent to get company_id for child transactions
        parent_join = "LEFT JOIN transactions t_parent ON t.parent_id = t_parent.id"
        # Use transaction's own mark_id (for both parent and child transactions)
        # Child transactions have their own mark_id, parent transactions use their own mark_id
        mark_ref = normalize_mark_ref('t.mark_id')
        # Use parent's company_id if this is a child transaction
        company_ref = "COALESCE(t.company_id, t_parent.company_id)"
    else:
        mark_ref = normalize_mark_ref('t.mark_id')
    mark_coa_join = _mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='INNER')
    return text(f"""
        SELECT
            coa.code,
            coa.name,
            coa.category,
            coa.subcategory,
            coa.fiscal_category,
            SUM(
                CASE
                    WHEN UPPER(COALESCE(mcm.mapping_type, '')) = 'DEBIT' THEN
                        t.amount * (CASE
                            WHEN m.natural_direction IS NOT NULL
                                 AND UPPER(TRIM(COALESCE(t.db_cr, ''))) != ''
                                 AND (
                                    (UPPER(m.natural_direction) = 'DB' AND UPPER(TRIM(t.db_cr)) IN ('CR', 'CREDIT', 'K', 'KREDIT'))
                                    OR
                                    (UPPER(m.natural_direction) = 'CR' AND UPPER(TRIM(t.db_cr)) IN ('DB', 'DEBIT', 'D', 'DE'))
                                 )
                            THEN -1 ELSE 1 END)
                    WHEN UPPER(COALESCE(mcm.mapping_type, '')) = 'CREDIT' THEN
                        -t.amount * (CASE
                            WHEN m.natural_direction IS NOT NULL
                                 AND UPPER(TRIM(COALESCE(t.db_cr, ''))) != ''
                                 AND (
                                    (UPPER(m.natural_direction) = 'DB' AND UPPER(TRIM(t.db_cr)) IN ('CR', 'CREDIT', 'K', 'KREDIT'))
                                    OR
                                    (UPPER(m.natural_direction) = 'CR' AND UPPER(TRIM(t.db_cr)) IN ('DB', 'DEBIT', 'D', 'DE'))
                                 )
                            THEN -1 ELSE 1 END)
                    WHEN t.db_cr = 'DB' THEN t.amount
                    WHEN t.db_cr = 'CR' THEN -t.amount
                    ELSE 0
                END
            ) as signed_amount
        FROM transactions t
        {parent_join}
        INNER JOIN marks m ON {mark_ref} = m.id
        {mark_coa_join}
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
            AND coa.category IN ('REVENUE', 'EXPENSE')
            AND (:company_id IS NULL OR {company_ref} = :company_id)
            {split_exclusion_clause}
                {coretax_clause}
        GROUP BY coa.id, coa.code, coa.name, coa.category, coa.subcategory, coa.fiscal_category
        ORDER BY coa.code
    """)


def _merge_expense_item(expenses, item):
    for existing in expenses:
        if str(existing.get('code') or '') == str(item.get('code') or ''):
            existing['amount'] = _to_float(existing.get('amount'), 0.0) + _to_float(item.get('amount'), 0.0)
            return
    expenses.append(item)


def _process_income_statement_rows(result):
    revenue = []
    expenses = []
    rent_expense_templates = {}
    total_revenue = 0.0
    total_expenses = 0.0
    fallback_5314_from_ledger = 0.0

    for row in result:
        d = row._mapping
        signed_amount = float(d['signed_amount']) if d['signed_amount'] else 0.0
        amount = -signed_amount if d['category'] == 'REVENUE' else signed_amount

        item = {
            'code': d['code'],
            'name': d['name'],
            'subcategory': d['subcategory'],
            'amount': amount,
            'category': d['category'],
            'fiscal_category': d.get('fiscal_category', 'DEDUCTIBLE'),
        }

        if d['category'] == 'REVENUE':
            revenue.append(item)
            total_revenue += amount
            continue

        if d['code'] == '5314':
            fallback_5314_from_ledger += amount
            continue

        if d['code'] in RENT_EXPENSE_CODES:
            rent_expense_templates[d['code']] = {
                'code': d['code'],
                'name': d['name'],
                'subcategory': d['subcategory'],
                'amount': 0.0,
                'category': 'EXPENSE',
            }
            continue

        _merge_expense_item(expenses, item)
        total_expenses += amount

    return {
        'revenue': revenue,
        'expenses': expenses,
        'rent_expense_templates': rent_expense_templates,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'fallback_5314_from_ledger': fallback_5314_from_ledger,
    }


def _build_cogs_breakdown(expenses, start_date, beginning_inv, ending_inv):
    purchases = 0.0
    purchases_items = []
    other_cogs_items = []

    cogs_items = [expense for expense in expenses if _is_cogs_expense_item(expense)]
    for item in cogs_items:
        item_code = str(item.get('code') or '').strip()
        if item_code == '5001':
            purchases += _to_float(item.get('amount'), 0.0)
            purchases_items.append(item)
        else:
            other_cogs_items.append(item)

    total_other_cogs = sum(item['amount'] for item in other_cogs_items)
    total_cogs = beginning_inv + purchases + total_other_cogs - ending_inv

    return {
        'beginning_inventory': beginning_inv,
        'purchases': purchases,
        'purchases_items': purchases_items,
        'other_cogs_items': other_cogs_items,
        'total_other_cogs': total_other_cogs,
        'product_cogs': 0.0,
        'ending_inventory': ending_inv,
        'total_cogs': total_cogs,
        'year': datetime.strptime(start_date, '%Y-%m-%d').year,
        'previous_year_purchases': 0.0,
    }


def _build_cogs_detail_items(cogs_breakdown):
    cogs_detail_items = []
    purchases_items = cogs_breakdown.get('purchases_items', [])
    other_cogs_items = cogs_breakdown.get('other_cogs_items', [])
    cogs_breakdown['purchases_items'] = purchases_items + other_cogs_items
    cogs_breakdown['purchases'] = cogs_breakdown.get('total_cogs', 0.0)

    beginning_inv = cogs_breakdown.get('beginning_inventory', 0.0)
    ending_inv = cogs_breakdown.get('ending_inventory', 0.0)
    if beginning_inv and ending_inv and beginning_inv != ending_inv:
        inventory_adjustment = beginning_inv - ending_inv
        cogs_detail_items.append({
            'code': 'INV_ADJ',
            'name': 'Penyesuaian Persediaan',
            'subcategory': 'Inventory Adjustment',
            'amount': float(inventory_adjustment),
            'description': f'Perubahan persediaan: Awal Rp {beginning_inv:,.0f} - Akhir Rp {ending_inv:,.0f}',
            'type': 'inventory_adjustment',
        })
    return cogs_detail_items
def fetch_income_statement_data(conn, start_date, end_date, company_id=None, report_type='real', comparative=False):
    """
    Helper function to fetch income statement data.
    Returns calculated values and lists of items.
    If comparative=True, returns data for current period and previous year period.
    """
    logger.debug(
        "[Income Statement] Fetching data start=%s end=%s comparative=%s",
        start_date,
        end_date,
        comparative
    )
    
    # For comparative, also fetch previous year data
    previous_year_data = None
    if comparative:
        prev_start_date, prev_end_date = _previous_period(start_date, end_date)
        logger.debug(
            "[Income Statement] Fetching previous year start=%s end=%s",
            prev_start_date,
            prev_end_date
        )
        
        previous_year_data = _fetch_income_statement_data_internal(
            conn, prev_start_date, prev_end_date, company_id, report_type,
            split_exclusion_clause=None, coretax_clause=None
        )
        
        logger.debug(
            "[Income Statement] Previous year totals revenue=%s expenses=%s",
            previous_year_data.get('total_revenue', 0),
            previous_year_data.get('total_expenses', 0)
        )
    
    # Get current period data
    current_data = _fetch_income_statement_data_internal(
        conn, start_date, end_date, company_id, report_type,
        split_exclusion_clause=None, coretax_clause=None
    )
    
    logger.debug(
        "[Income Statement] Current year totals revenue=%s expenses=%s",
        current_data.get('total_revenue', 0),
        current_data.get('total_expenses', 0)
    )
    
    # If comparative, merge the data
    if comparative and previous_year_data:
        _apply_comparative_data(current_data, previous_year_data)
    
    # Build COGS detail items for frontend display
    if current_data.get('cogs_breakdown'):
        cogs_detail_items = _build_cogs_detail_items(current_data['cogs_breakdown'])
    else:
        cogs_detail_items = []
    
    # Add COGS detail to current data
    current_data['cogs_detail'] = cogs_detail_items
    
    # Fix total_cogs to use calculate_hpp from cogs_breakdown
    if current_data.get('cogs_breakdown') and 'total_cogs' in current_data['cogs_breakdown']:
        current_data['total_cogs'] = current_data['cogs_breakdown']['total_cogs']
    elif 'total_cogs' in current_data:
        # Keep existing total_cogs if available
        pass
    else:
        # Fallback: calculate from cogs_detail
        current_data['total_cogs'] = sum(item.get('amount', 0) for item in cogs_detail_items)
    
    return current_data

def _fetch_income_statement_data_internal(conn, start_date, end_date, company_id, report_type, split_exclusion_clause=None, coretax_clause=None):
    """Internal function to fetch income statement data for a specific period."""
    if split_exclusion_clause is None:
        split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    if coretax_clause is None:
        coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
    result = conn.execute(_build_income_statement_query(conn, report_type, split_exclusion_clause, coretax_clause), {
        'start_date': start_date,
        'end_date': end_date,
        'company_id': company_id
    })
    parsed = _process_income_statement_rows(result)
    revenue = parsed['revenue']
    expenses = parsed['expenses']
    rent_expense_templates = parsed['rent_expense_templates']
    total_revenue = parsed['total_revenue']
    total_expenses = parsed['total_expenses']
    fallback_5314_from_ledger = parsed['fallback_5314_from_ledger']

    # Rent expense (5315/5105) is not recognized from full payment amount.
    # For linked rental contracts, recognize only the prorated amount that overlaps the report period.
    for rent_item in _fetch_non_contract_rent_expense_items(conn, start_date, end_date, company_id, report_type):
        _merge_expense_item(expenses, rent_item)
        total_expenses += _to_float(rent_item.get('amount'), 0.0)

    # 5315 check
    if _is_coa_mapped_for_report(conn, '5315', report_type) or _is_coa_mapped_for_report(conn, '5105', report_type):
        prorated_rent_expense = _calculate_prorated_contract_rent_expense(conn, start_date, end_date, company_id, report_type)
        if abs(prorated_rent_expense) >= 0.000001:
            rent_account = _resolve_rent_expense_account(conn, company_id, rent_expense_templates)
            rent_item = {
                'code': rent_account.get('code'),
                'name': rent_account.get('name'),
                'subcategory': rent_account.get('subcategory'),
                'amount': prorated_rent_expense,
                'category': 'EXPENSE'
            }
            _merge_expense_item(expenses, rent_item)
            total_expenses += prorated_rent_expense
    
    # 2.4.1 Calculate service withholding tax adjustments (gross-up).
    # Since transactions are recorded as Net payment, we must add the withheld tax back to expenses.
    try:
        service_tax_adjustments = _calculate_service_tax_adjustment_for_period(conn, start_date, end_date, company_id, report_type)
        for adj in service_tax_adjustments:
            _merge_expense_item(expenses, adj)
            total_expenses += _to_float(adj.get('amount'), 0.0)
    except Exception as e:
        logger.error(f"Failed to calculate service tax adjustments: {e}")
    
    # 2.5 Calculate 5314 (Beban Penyusutan dan Amortisasi) dynamically:
    # total = calculated amortization + manual amortization.
    amortization_breakdown = {
        'report_year': int(str(start_date)[:4]),
        'manual_total': 0.0,
        'calculated_total': 0.0,
        'total_5314': 0.0
    }
    dynamic_calc_ok = False
    dynamic_5314_amount = 0.0
    
    if _is_coa_mapped_for_report(conn, '5314', report_type):
        dynamic_calc_ok = True
        try:
            amortization_breakdown = _calculate_dynamic_5314_total(conn, start_date, end_date=end_date, company_id=company_id, report_type=report_type)
            dynamic_5314_amount = _to_float(amortization_breakdown.get('total_5314'), 0.0)
        except Exception as e:
            dynamic_calc_ok = False
            logger.error(f"Failed to calculate dynamic 5314 amount: {e}")
            dynamic_5314_amount = fallback_5314_from_ledger
    
    calculated_amort_total = _to_float(amortization_breakdown.get('calculated_total'), 0.0)
    manual_amort_total = _to_float(amortization_breakdown.get('manual_total'), 0.0)
    
    # 2. Handle COGS (HPP) with Manual Inventory Adjustments
    beginning_inv = 0
    ending_inv = 0
    
    # We use start_date's year for the inventory balance
    year = datetime.strptime(start_date, '%Y-%m-%d').year
    
    try:
        inv_balance = _get_inventory_balance_with_carry(conn, year, company_id, report_type)
        beginning_inv = _to_float(inv_balance.get('beginning_inventory_amount'), 0.0)
        ending_inv = _to_float(inv_balance.get('ending_inventory_amount'), 0.0)
    except Exception as e:
        logger.error(f"Failed to fetch inventory balances: {e}")

    # Identify 'Purchases' and 'Other COGS' from expenses.
    # Use robust COGS detection (subcategory normalization + 50xx code fallback).
    cogs_breakdown = _build_cogs_breakdown(expenses, start_date, beginning_inv, ending_inv)
    calculate_hpp = cogs_breakdown['total_cogs']

    # Filter out COGS items and inject dynamic 5314 amount if mapped.
    final_expenses = [
        e for e in expenses
        if not _is_cogs_expense_item(e) and str(e.get('code') or '') != '5314'
    ]
    
    if _is_coa_mapped_for_report(conn, '5314', report_type):
        final_expenses.append({
            'code': '5314',
            'name': 'Beban Penyusutan dan Amortisasi',
            'subcategory': 'Operating Expenses',
            'amount': dynamic_5314_amount,
            'category': 'EXPENSE',
            'fiscal_category': 'DEDUCTIBLE' # Amortization usually deductible unless specifically marked
        })
    
    # Calculate total_expenses as the sum of all items in final_expenses list
    total_expenses_calculated = sum(e['amount'] for e in final_expenses)
    
    # --- FISCAL RECONCILIATION LOGIC ---
    positive_corrections = []
    negative_corrections = []
    
    # Check expenses for non-deductible items
    for exp in final_expenses:
        f_cat = exp.get('fiscal_category', 'DEDUCTIBLE')
        if f_cat in ('NON_DEDUCTIBLE_PERMANENT', 'NON_DEDUCTIBLE_TEMPORARY'):
            positive_corrections.append({
                'code': exp['code'],
                'name': exp['name'],
                'amount': exp['amount'],
                'fiscal_category': f_cat
            })
            
    # Check COGS for non-deductible items
    for cogs_item in cogs_breakdown.get('purchases_items', []) + cogs_breakdown.get('other_cogs_items', []):
        f_cat = cogs_item.get('fiscal_category', 'DEDUCTIBLE')
        if f_cat in ('NON_DEDUCTIBLE_PERMANENT', 'NON_DEDUCTIBLE_TEMPORARY'):
             positive_corrections.append({
                'code': cogs_item['code'],
                'name': cogs_item['name'],
                'amount': cogs_item['amount'],
                'fiscal_category': f_cat
            })

    # Check revenue for non-taxable income
    for rev in revenue:
        f_cat = rev.get('fiscal_category', 'DEDUCTIBLE')
        if f_cat == 'NON_TAXABLE_INCOME':
            negative_corrections.append({
                'code': rev['code'],
                'name': rev['name'],
                'amount': rev['amount'],
                'fiscal_category': f_cat
            })

    total_positive_correction = sum(c['amount'] for c in positive_corrections)
    total_negative_correction = sum(c['amount'] for c in negative_corrections)
    commercial_net_income = total_revenue - total_expenses_calculated - calculate_hpp
    fiscal_net_income = commercial_net_income + total_positive_correction - total_negative_correction

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
        'net_income': commercial_net_income,
        'fiscal_reconciliation': {
            'commercial_net_income': commercial_net_income,
            'positive_corrections': positive_corrections,
            'negative_corrections': negative_corrections,
            'total_positive_correction': total_positive_correction,
            'total_negative_correction': total_negative_correction,
            'fiscal_net_income': fiscal_net_income
        }
    }
