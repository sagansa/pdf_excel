import sys
from backend.db.session import get_db_engine
from backend.services.report_service import fetch_income_statement_data, _calculate_service_tax_adjustment_for_period

def diagnose():
    engine, _ = get_db_engine()
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    
    with engine.connect() as conn:
        print("Checking service tax adjustments directly...")
        adjs = _calculate_service_tax_adjustment_for_period(conn, start_date, end_date)
        print(f"Adjustments: {adjs}")
        total_adj = sum(a['amount'] for a in adjs)
        print(f"Total Adjustment: {total_adj}")

        print("\nFetching full Income Statement...")
        data = fetch_income_statement_data(conn, start_date, end_date)
        
        comps = data.get('net_income_components', {})
        print(f"\nNet Income Components:")
        print(f"  Revenue:  {comps.get('total_revenue')}")
        print(f"  Expenses: {comps.get('total_expenses')}")
        print(f"  COGS:     {comps.get('total_cogs')}")
        print(f"  Net Inc:  {data.get('net_income')}")
        
        # Check if 5003 is in COGS brake down
        cogs_items = data.get('cogs_breakdown', {}).get('other_cogs_items', [])
        found_5003 = [item for item in cogs_items if str(item.get('code')) == '5003']
        print(f"\nCOA 5003 in COGS items: {found_5003}")

if __name__ == "__main__":
    diagnose()
