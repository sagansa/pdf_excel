"""
Test script untuk memverifikasi kalkulasi kumulatif Laba Ditahan Tahun Sebelumnya
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_balance_sheet_data, fetch_income_statement_data

# Connect to database
engine = create_engine("sqlite:///database.db")

def test_cumulative_retained_earnings():
    """Test kalkulasi kumulatif Laba Ditahan Tahun Sebelumnya"""
    
    with engine.connect() as conn:
        # Get a company with data
        company_result = conn.execute(text("""
            SELECT DISTINCT company_id 
            FROM transactions 
            WHERE company_id IS NOT NULL 
            LIMIT 1
        """)).fetchone()
        
        if not company_result:
            print("❌ No company with transactions found")
            return
        
        company_id = company_result.company_id
        print(f"Testing with company_id: {company_id}")
        
        # Test 1: Check income statement for multiple years
        print("\n=== TEST 1: Income Statement per Year ===")
        test_years = [2023, 2024, 2025]
        yearly_incomes = {}
        
        for year in test_years:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            
            try:
                income_data = fetch_income_statement_data(
                    conn, start_date, end_date, company_id, 
                    report_type='real', comparative=False
                )
                net_income = income_data.get('net_income', 0.0)
                yearly_incomes[year] = net_income
                print(f"  {year}: Net Income = Rp {net_income:,.2f}")
            except Exception as e:
                print(f"  {year}: Error - {e}")
                yearly_incomes[year] = 0.0
        
        # Test 2: Check Balance Sheet for 2025
        print("\n=== TEST 2: Balance Sheet Equity Section (2025-12-31) ===")
        try:
            bs_data = fetch_balance_sheet_data(
                conn, "2025-12-31", company_id, report_type='real'
            )
            
            # Equity is returned as {'items': [...], 'total': ...}
            equity_data = bs_data.get('equity', {})
            equity_items = equity_data.get('items', []) if isinstance(equity_data, dict) else []
            
            print("\nEquity items:")
            
            retained_earnings_found = False
            for item in equity_items:
                if isinstance(item, dict):
                    name = item.get('name', '')
                    amount = item.get('amount', 0.0)
                    code = item.get('code', '')
                    
                    print(f"  {code}: {name} = Rp {amount:,.2f}")
                    
                    if 'Laba Ditahan' in name or 'Retained Earnings' in name:
                        retained_earnings_found = True
                        print(f"\n  >>> Laba Ditahan Tahun Sebelumnya: Rp {amount:,.2f}")
                        
                        # Calculate expected cumulative
                        expected_cumulative = sum(yearly_incomes.get(y, 0.0) for y in range(2023, 2025))
                        print(f"  >>> Expected (cumulative 2023-2024): Rp {expected_cumulative:,.2f}")
                        
                        if abs(amount - expected_cumulative) < 0.01:
                            print("  ✅ PASS: Laba Ditahan matches cumulative calculation!")
                        else:
                            print(f"  ⚠️  Difference: Rp {abs(amount - expected_cumulative):,.2f}")
            
            if not retained_earnings_found:
                print("\n  ⚠️  No Laba Ditahan item found in equity section")
                
        except Exception as e:
            print(f"Error fetching balance sheet: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 3: Manual calculation verification
        print("\n=== TEST 3: Manual Cumulative Calculation ===")
        cumulative = 0.0
        for year in range(2023, 2025):
            income = yearly_incomes.get(year, 0.0)
            cumulative += income
            print(f"  Cumulative after {year}: Rp {cumulative:,.2f}")
        
        print(f"\n  Total Cumulative Retained Earnings (2023-2024): Rp {cumulative:,.2f}")

if __name__ == "__main__":
    test_cumulative_retained_earnings()
    print("\n=== Test Complete ===")
