"""
Test langsung implementasi Laba Ditahan dengan MySQL
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_balance_sheet_data

# Koneksi ke MySQL
engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")

with engine.connect() as conn:
    company_id = "40e70c5f-43ef-49aa-b73e-7f83d326b301"
    
    print("=" * 80)
    print("TEST IMPLEMENTASI LABA DITAHAN KUMULATIF - MYSQL")
    print("=" * 80)
    
    # Test Balance Sheet 2025
    print("\n--- Balance Sheet 2025-12-31 ---")
    bs_data = fetch_balance_sheet_data(
        conn, "2025-12-31", company_id, report_type='real'
    )
    
    assets = bs_data.get('assets', {})
    equity = bs_data.get('equity', {})
    
    total_assets = assets.get('total', 0)
    total_equity = equity.get('total', 0)
    
    equity_items = equity.get('items', [])
    
    print(f"\nTotal Assets:  Rp {total_assets:,.0f}")
    print(f"Total Equity:  Rp {total_equity:,.0f}")
    print(f"Difference:    Rp {total_assets - total_equity:,.0f}")
    print(f"Balance:       {'✓ YES' if abs(total_assets - total_equity) < 0.01 else '✗ NO'}")
    
    print("\nEquity Items:")
    for item in equity_items:
        if isinstance(item, dict):
            print(f"  {item.get('code')}: {item.get('name')} = Rp {item.get('amount'):,.0f}")
    
    # Hitung manual
    print("\n--- Manual Calculation ---")
    from backend.services.report_service import fetch_income_statement_data
    
    cumulative = 0
    for year in [2022, 2023, 2024]:
        income_data = fetch_income_statement_data(
            conn, f"{year}-01-01", f"{year}-12-31", company_id,
            report_type='real', comparative=False
        )
        net_income = income_data.get('net_income', 0.0)
        cumulative += net_income
        print(f"  {year} Net Income: Rp {net_income:,.0f}")
    
    print(f"\nCumulative (Expected Laba Ditahan 2025): Rp {cumulative:,.0f}")
    
    actual = next((item.get('amount', 0) for item in equity_items 
                   if isinstance(item, dict) and 'Laba Ditahan' in item.get('name', '')), 0)
    
    print(f"Actual (from Balance Sheet):               Rp {actual:,.0f}")
    print(f"Match: {'✓ YES' if abs(cumulative - actual) < 0.01 else '✗ NO'}")
