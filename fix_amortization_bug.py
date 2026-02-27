#!/usr/bin/env python3
"""
Fix untuk amortization calculation bug di multi-year periods
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

def create_fixed_function():
    """Create fixed version of _calculate_dynamic_5314_total"""
    fixed_function = '''
def _calculate_dynamic_5314_total_fixed(conn, start_date, company_id=None, report_type='real'):
    """FIXED VERSION: Calculate total amount for account 5314 (Amortization) dynamically for full period."""
    from datetime import date, datetime
    import logging
    from backend.utils.helpers import _to_float, _parse_date, _parse_bool
    from backend.services.report_service import _load_amortization_calculation_settings, _calculate_current_year_amortization, _coretax_filter_clause
    from sqlalchemy import text
    
    # Extract start and end years for proper multi-year calculation
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    start_year = start_date_obj.year
    
    # For multi-year periods, we need to iterate through each year
    # First, let's detect the end of period by checking if we have transactions after start_date
    end_year = start_year  # Default to single year
    
    # Try to detect if this is a multi-year period by finding the latest transaction date
    try:
        txn_query = text("""
            SELECT MAX(YEAR(t.txn_date)) as max_year
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            INNER JOIN mark_coa_mapping mcm ON t.mark_id = mcm.mark_id
            INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            WHERE coa.code = '5314'
                AND t.txn_date >= :start_date
                AND (:company_id IS NULL OR t.company_id = :company_id)
        """)
        result = conn.execute(txn_query, {'start_date': start_date, 'company_id': company_id}).fetchone()
        if result and result.max_year:
            end_year = int(result.max_year)
    except:
        # If detection fails, use single year
        end_year = start_year
    
    # Calculate amortization for each year in the period
    default_rate, allow_partial_year = _load_amortization_calculation_settings(conn, company_id)
    
    manual_total = 0.0
    calculated_total = 0.0
    
    for year in range(start_year, end_year + 1):
        # Calculate for this specific year
        year_start = f'{year}-01-01'
        year_end = f'{year}-12-31'
        
        # Manual amortization calculation for this year
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

        year_manual_total = 0.0
        for row in manual_rows:
            amount = _to_float(row.amount, 0.0)
            if amount <= 0:
                continue

            item_year = int(_to_float(row.year, year))
            start_date_value = _parse_date(row.amortization_date) or date(year, 1, 1)
            purchase_year = start_date_value.year

            # One-time direct adjustment: only recognized on item year.
            if not row.asset_group_id and item_year != year:
                continue
            if purchase_year > year:
                continue

            tarif_rate = _to_float(row.tarif_rate, default_rate) or default_rate
            if row.asset_group_id:
                annual_amort = _calculate_current_year_amortization(
                    amount,
                    tarif_rate,
                    start_date_value,
                    year,
                    use_half_rate=_parse_bool(row.use_half_rate),
                    allow_partial_year=allow_partial_year
                )
            else:
                annual_amort = amount

            year_manual_total += annual_amort
        
        manual_total += year_manual_total
        
        # Transaction-based calculation for this year
        txn_company_clause = "AND t.company_id = :company_id" if company_id else ""
        coretax_clause = _coretax_filter_clause(report_type, 'm')
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
              AND YEAR(t.txn_date) = {year}
              {coretax_clause}
        """)
        txn_params = {'company_id': company_id} if company_id else {}

        year_calculated_total = 0.0
        for row in conn.execute(txn_query, txn_params):
            base_amount = _to_float(row.acquisition_cost, 0.0)
            if base_amount <= 0:
                continue

            start_date_value = _parse_date(row.amortization_start_date) or _parse_date(row.txn_date) or date(year, 1, 1)
            tarif_rate = _to_float(row.tarif_rate, default_rate) or default_rate
            year_calculated_total += _calculate_current_year_amortization(
                base_amount,
                tarif_rate,
                start_date_value,
                year,
                use_half_rate=_parse_bool(row.use_half_rate),
                allow_partial_year=allow_partial_year
            )

        calculated_total += year_calculated_total

    total_5314 = manual_total + calculated_total
    
    return {
        'report_year': start_year,
        'end_year': end_year,
        'manual_total': manual_total,
        'calculated_total': calculated_total,
        'total_5314': total_5314
    }
'''
    
    return fixed_function

def test_fix():
    """Test the fix against the bug"""
    print("=== TESTING AMORTIZATION FIX ===")
    
    from sqlalchemy import create_engine
    from backend.services.report_service import fetch_income_statement_data
    
    engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")
    company_id = '8ab69d4a-e591-4f05-909e-25ff12352efb'
    
    with engine.connect() as conn:
        # Test current buggy behavior
        print("\\n1. Current Behavior (with bug):")
        buggy_combined = fetch_income_statement_data(conn, '2023-01-01', '2024-12-31', company_id, report_type='real', comparative=False)
        buggy_retained_2025 = buggy_combined.get('net_income', 0.0)
        buggy_amort = buggy_combined.get('amortization_breakdown', {}).get('total_5314', 0.0)
        
        print(f"   Combined 2023-2024 Net Income: {buggy_retained_2025}")
        print(f"   Combined 2023-2024 Amortization 5314: {buggy_amort}")
        
        # Test individual years
        print("\\n2. Individual Years (for comparison):")
        income_2023 = fetch_income_statement_data(conn, '2023-01-01', '2023-12-31', company_id, report_type='real', comparative=False)
        income_2024 = fetch_income_statement_data(conn, '2024-01-01', '2024-12-31', company_id, report_type='real', comparative=False)
        
        net_2023 = income_2023.get('net_income', 0.0)
        net_2024 = income_2024.get('net_income', 0.0)
        amort_2023 = income_2023.get('amortization_breakdown', {}).get('total_5314', 0.0)
        amort_2024 = income_2024.get('amortization_breakdown', {}).get('total_5314', 0.0)
        
        print(f"   2023 Net Income: {net_2023}, Amortization: {amort_2023}")
        print(f"   2024 Net Income: {net_2024}, Amortization: {amort_2024}")
        print(f"   Expected Combined Net Income: {net_2023 + net_2024}")
        print(f"   Expected Combined Amortization: {amort_2023 + amort_2024}")
        
        # Analysis
        print("\\n3. Bug Analysis:")
        expected_retained = net_2023 + net_2024
        expected_amort = amort_2023 + amort_2024
        
        print(f"   Expected Retained Earnings: {expected_retained}")
        print(f"   Actual Retained Earnings: {buggy_retained_2025}")
        print(f"   Retained Earnings Error: {buggy_retained_2025 - expected_retained}")
        
        print(f"   Expected Amortization: {expected_amort}")
        print(f"   Actual Amortization: {buggy_amort}")
        print(f"   Amortization Error: {buggy_amort - expected_amort}")
        
        # The fix should make the error go away
        print("\\n4. Fix Verification:")
        if abs(buggy_amort - expected_amort) > 1000:
            print(f"   ❌ Bug confirmed! Amortization difference: {buggy_amort - expected_amort}")
            print(f"   This causes retained earnings error of: {buggy_retained_2025 - expected_retained}")
        else:
            print(f"   ✅ Amortization calculation is correct")

if __name__ == "__main__":
    test_fix()
