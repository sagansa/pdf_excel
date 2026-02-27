"""
Script untuk mengecek Balance Sheet yang sebenarnya dari MySQL
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_balance_sheet_data

# Koneksi ke MySQL
engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")

with engine.connect() as conn:
    print("=" * 80)
    print("CEK DATA BALANCE SHEET YANG SEBENARNYA")
    print("=" * 80)
    
    # Cek semua companies
    print("\n=== COMPANIES YANG ADA ===")
    companies = conn.execute(text("""
        SELECT DISTINCT company_id, created_at 
        FROM transactions 
        WHERE company_id IS NOT NULL 
        ORDER BY created_at
    """)).fetchall()
    
    for comp in companies:
        print(f"  - {comp.company_id}")
    
    # Test untuk company pertama
    if companies:
        company_id = companies[0].company_id
        print(f"\n{'='*80}")
        print(f"ANALISA DETAIL: {company_id}")
        print(f"{'='*80}")
        
        for year in [2023, 2024, 2025]:
            as_of_date = f"{year}-12-31"
            print(f"\n{'='*60}")
            print(f"TAHUN {year} ({as_of_date})")
            print(f"{'='*60}")
            
            try:
                bs_data = fetch_balance_sheet_data(
                    conn, as_of_date, company_id, report_type='real'
                )
                
                assets = bs_data.get('assets', {})
                liabilities = bs_data.get('liabilities', {})
                equity = bs_data.get('equity', {})
                
                total_assets = assets.get('total', 0)
                total_liabilities = liabilities.get('total', 0)
                total_equity = equity.get('total', 0)
                
                print(f"\n--- TOTALS ---")
                print(f"  Total Assets:              Rp {total_assets:>15,.0f}")
                print(f"  Total Liabilities:         Rp {total_liabilities:>15,.0f}")
                print(f"  Total Equity:              Rp {total_equity:>15,.0f}")
                print(f"  Liabilities + Equity:      Rp {total_liabilities + total_equity:>15,.0f}")
                
                difference = total_assets - (total_liabilities + total_equity)
                print(f"\n  DIFFERENCE:                Rp {difference:>15,.0f}")
                print(f"  IS BALANCED:               {abs(difference) < 0.01}")
                
                # Assets detail
                print(f"\n--- ASSETS DETAIL ---")
                assets_current = assets.get('current', [])
                assets_non_current = assets.get('non_current', [])
                
                print(f"  Current Assets ({len(assets_current)} items):")
                for item in assets_current:
                    if isinstance(item, dict):
                        print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):>15,.0f}")
                
                print(f"  Non-Current Assets ({len(assets_non_current)} items):")
                for item in assets_non_current:
                    if isinstance(item, dict):
                        print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):>15,.0f}")
                
                # Liabilities detail
                print(f"\n--- LIABILITIES DETAIL ---")
                liabilities_current = liabilities.get('current', [])
                liabilities_non_current = liabilities.get('non_current', [])
                
                if liabilities_current:
                    print(f"  Current Liabilities ({len(liabilities_current)} items):")
                    for item in liabilities_current:
                        if isinstance(item, dict):
                            print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):>15,.0f}")
                
                if liabilities_non_current:
                    print(f"  Non-Current Liabilities ({len(liabilities_non_current)} items):")
                    for item in liabilities_non_current:
                        if isinstance(item, dict):
                            print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):>15,.0f}")
                
                if not liabilities_current and not liabilities_non_current:
                    print(f"  (tidak ada)")
                
                # Equity detail
                print(f"\n--- EQUITY DETAIL ---")
                equity_items = equity.get('items', [])
                for item in equity_items:
                    if isinstance(item, dict):
                        print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):>15,.0f}")
                
            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()
        
        # Summary per tahun
        print(f"\n{'='*80}")
        print("RINGKASAN BALANCE SHEET PER TAHUN")
        print(f"{'='*80}")
        print(f"{'Tahun':<10} | {'Assets':>18} | {'Liabilities':>18} | {'Equity':>18} | {'Balance?':>10}")
        print(f"{'-'*10}-+-{'-'*18}-+-{'-'*18}-+-{'-'*18}-+-{'-'*10}")
        
        for year in [2023, 2024, 2025]:
            as_of_date = f"{year}-12-31"
            try:
                bs_data = fetch_balance_sheet_data(
                    conn, as_of_date, company_id, report_type='real'
                )
                
                total_assets = bs_data.get('assets', {}).get('total', 0)
                total_liabilities = bs_data.get('liabilities', {}).get('total', 0)
                total_equity = bs_data.get('equity', {}).get('total', 0)
                
                is_balanced = abs(total_assets - (total_liabilities + total_equity)) < 0.01
                
                print(f"{year:<10} | {total_assets:>18,.0f} | {total_liabilities:>18,.0f} | {total_equity:>18,.0f} | {str(is_balanced):>10}")
            except Exception as e:
                print(f"{year:<10} | {'ERROR':>18} | {'ERROR':>18} | {'ERROR':>18} | {'ERROR':>10}")
