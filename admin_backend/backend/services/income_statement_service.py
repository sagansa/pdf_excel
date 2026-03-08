import logging
from datetime import datetime

from sqlalchemy import text

from backend.services.report_adjustments import (
    _calculate_prorated_contract_rent_expense,
    _calculate_service_tax_adjustment_for_period,
    _fetch_non_contract_rent_expense_items,
    _resolve_rent_expense_account,
)
from backend.services.report_common import (
    RENT_EXPENSE_CODES,
    _calculate_dynamic_5314_total,
    _coretax_filter_clause,
    _get_inventory_balance_with_carry,
    _is_cogs_expense_item,
    _mark_coa_join_clause,
    _split_parent_exclusion_clause,
    _to_float,
)

logger = logging.getLogger(__name__)
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
        # Calculate previous year period
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        prev_start_date = start_date_obj.replace(year=start_date_obj.year - 1).strftime('%Y-%m-%d')
        prev_end_date = end_date_obj.replace(year=end_date_obj.year - 1).strftime('%Y-%m-%d')
        
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
        # Create lookup for previous year data
        prev_revenue_lookup = {item['code']: item['amount'] for item in previous_year_data['revenue']}
        prev_expenses_lookup = {item['code']: item['amount'] for item in previous_year_data['expenses']}
        
        # Create lookup for current year data
        curr_revenue_lookup = {item['code']: item for item in current_data['revenue']}
        curr_expenses_lookup = {item['code']: item for item in current_data['expenses']}
        
        logger.debug(
            "[Income Statement] Comparative revenue codes prev=%s curr=%s",
            list(prev_revenue_lookup.keys()),
            list(curr_revenue_lookup.keys())
        )
        
        # Merge revenue: include all codes from both years
        all_revenue_codes = set(prev_revenue_lookup.keys()) | set(curr_revenue_lookup.keys())
        merged_revenue = []
        
        for code in all_revenue_codes:
            if code in curr_revenue_lookup:
                item = curr_revenue_lookup[code].copy()
                item['previous_year_amount'] = prev_revenue_lookup.get(code, 0.0)
            else:
                # Only exists in previous year
                item = previous_year_data['revenue'][[i for i, x in enumerate(previous_year_data['revenue']) if x['code'] == code][0]].copy()
                item['amount'] = 0.0  # No current year amount
                item['previous_year_amount'] = prev_revenue_lookup.get(code, 0.0)
            merged_revenue.append(item)
        
        # Sort by code
        merged_revenue.sort(key=lambda x: x['code'])
        current_data['revenue'] = merged_revenue
        
        # Merge expenses: include all codes from both years
        all_expense_codes = set(prev_expenses_lookup.keys()) | set(curr_expenses_lookup.keys())
        merged_expenses = []
        
        for code in all_expense_codes:
            if code in curr_expenses_lookup:
                item = curr_expenses_lookup[code].copy()
                item['previous_year_amount'] = prev_expenses_lookup.get(code, 0.0)
            else:
                # Only exists in previous year
                item = previous_year_data['expenses'][[i for i, x in enumerate(previous_year_data['expenses']) if x['code'] == code][0]].copy()
                item['amount'] = 0.0  # No current year amount
                item['previous_year_amount'] = prev_expenses_lookup.get(code, 0.0)
            merged_expenses.append(item)
        
        # Sort by code
        merged_expenses.sort(key=lambda x: x['code'])
        current_data['expenses'] = merged_expenses
        
        # Add previous year totals
        current_data['previous_year_total_revenue'] = previous_year_data['total_revenue']
        current_data['previous_year_total_expenses'] = previous_year_data['total_expenses']
        current_data['previous_year_net_income'] = previous_year_data['net_income']
        
        # Add comparative values to COGS breakdown (both purchases and other COGS lines).
        if 'cogs_breakdown' in current_data and 'cogs_breakdown' in previous_year_data:
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

            # Keep total row consistent with the current-year side, which uses total_cogs.
            current_data['cogs_breakdown']['previous_year_purchases'] = _to_float(
                prev_cogs.get('total_cogs', prev_cogs.get('purchases', 0.0)), 0.0
            )
        
        logger.debug(
            "[Income Statement] Merged comparative data revenue_count=%s expense_count=%s",
            len(merged_revenue),
            len(merged_expenses)
        )
    
    # Build COGS detail items for frontend display
    cogs_detail_items = []
    if current_data.get('cogs_breakdown'):
        # Combine purchases_items and other_cogs_items for Purchase Breakdown display
        purchases_items = current_data.get('cogs_breakdown', {}).get('purchases_items', [])
        other_cogs_items = current_data.get('cogs_breakdown', {}).get('other_cogs_items', [])
        
        # Add all COGS items to purchases_items for unified display
        all_cogs_items = purchases_items + other_cogs_items
        
        # Update purchases_items in current_data for frontend Purchase Breakdown
        current_data['cogs_breakdown']['purchases_items'] = all_cogs_items
        current_data['cogs_breakdown']['purchases'] = current_data.get('cogs_breakdown', {}).get('total_cogs', 0.0)
        
        # Add inventory adjustment if applicable
        if current_data.get('cogs_breakdown', {}).get('beginning_inventory') and current_data.get('cogs_breakdown', {}).get('ending_inventory'):
            beginning_inv = current_data.get('cogs_breakdown', {}).get('beginning_inventory', 0.0)
            ending_inv = current_data.get('cogs_breakdown', {}).get('ending_inventory', 0.0)
            
            if beginning_inv != ending_inv:
                inventory_adjustment = beginning_inv - ending_inv
                cogs_detail_items.append({
                    'code': 'INV_ADJ',
                    'name': 'Penyesuaian Persediaan',
                    'subcategory': 'Inventory Adjustment',
                    'amount': float(inventory_adjustment),
                    'description': f'Perubahan persediaan: Awal Rp {beginning_inv:,.0f} - Akhir Rp {ending_inv:,.0f}',
                    'type': 'inventory_adjustment'
                })
    
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
    mark_coa_join = _mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='INNER')
    
    query = text(f"""
        SELECT 
            coa.code,
            coa.name,
            coa.category,
            coa.subcategory,
            SUM(
                CASE 
                    -- Account posting sign from mapping: debit = +, credit = -
                    -- Reversed when db_cr opposes mark's natural_direction
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
        INNER JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
            AND coa.category IN ('REVENUE', 'EXPENSE')
            AND (:company_id IS NULL OR t.company_id = :company_id)
            {split_exclusion_clause}
                {coretax_clause}
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
    for rent_item in _fetch_non_contract_rent_expense_items(conn, start_date, end_date, company_id, report_type):
        merge_expense_item(rent_item)
        total_expenses += _to_float(rent_item.get('amount'), 0.0)

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
        merge_expense_item(rent_item)
        total_expenses += prorated_rent_expense
    
    # 2.4.1 Calculate service withholding tax adjustments (gross-up).
    # Since transactions are recorded as Net payment, we must add the withheld tax back to expenses.
    try:
        service_tax_adjustments = _calculate_service_tax_adjustment_for_period(conn, start_date, end_date, company_id, report_type)
        for adj in service_tax_adjustments:
            merge_expense_item(adj)
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
    dynamic_calc_ok = True
    try:
        amortization_breakdown = _calculate_dynamic_5314_total(conn, start_date, end_date=end_date, company_id=company_id, report_type=report_type)
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
        inv_balance = _get_inventory_balance_with_carry(conn, year, company_id, report_type)
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
    
    # Note: product_cogs from hpp_batch_products is NOT included in COGS calculation
    # to avoid double counting, as the transactions are already captured in purchases (COA 5001)
    product_cogs = 0.0
    previous_year_purchases = 0.0
    
    # Provide a specific breakdown for the UI
    cogs_breakdown = {
        'beginning_inventory': beginning_inv,
        'purchases': purchases,
        'purchases_items': purchases_items,
        'other_cogs_items': other_cogs_items,
        'total_other_cogs': total_other_cogs,
        'product_cogs': product_cogs,
        'ending_inventory': ending_inv,
        'total_cogs': calculate_hpp,
        'year': year,
        'previous_year_purchases': previous_year_purchases
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

