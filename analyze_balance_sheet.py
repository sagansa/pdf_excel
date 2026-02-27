"""
Script untuk menganalisa kenapa Balance Sheet tidak balance di tahun 2024 dan 2025
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_balance_sheet_data, fetch_income_statement_data

engine = create_engine("sqlite:///database.db")

with engine.connect() as conn:
    company_id = "demo-company"
    
    print("=" * 80)
    print("ANALISA BALANCE SHEET - CHECKING BALANCE PER TAHUN")
    print("=" * 80)
    
    for year in [2023, 2024, 2025]:
        as_of_date = f"{year}-12-31"
        print(f"\n{'='*80}")
        print(f"TAHUN {year} - As of {as_of_date}")
        print(f"{'='*80}")
        
        try:
            bs_data = fetch_balance_sheet_data(
                conn, as_of_date, company_id, report_type='real'
            )
            
            # Extract data
            assets = bs_data.get('assets', {})
            liabilities = bs_data.get('liabilities', {})
            equity = bs_data.get('equity', {})
            
            total_assets = assets.get('total', 0)
            total_liabilities = liabilities.get('total', 0)
            total_equity = equity.get('total', 0)
            
            assets_current = assets.get('current', [])
            assets_non_current = assets.get('non_current', [])
            liabilities_current = liabilities.get('current', [])
            liabilities_non_current = liabilities.get('non_current', [])
            equity_items = equity.get('items', [])
            
            print(f"\n--- TOTALS ---")
            print(f"  Total Assets:     Rp {total_assets:,.0f}")
            print(f"  Total Liabilities: Rp {total_liabilities:,.0f}")
            print(f"  Total Equity:     Rp {total_equity:,.0f}")
            print(f"  Liabilities + Equity: Rp {total_liabilities + total_equity:,.0f}")
            
            difference = total_assets - (total_liabilities + total_equity)
            print(f"\n  DIFFERENCE (Assets - Liab - Equity): Rp {difference:,.0f}")
            print(f"  IS BALANCED: {abs(difference) < 0.01}")
            
            print(f"\n--- ASSETS DETAIL ---")
            print(f"  Current Assets ({len(assets_current)} items):")
            for item in assets_current:
                if isinstance(item, dict):
                    print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):,.0f}")
            
            print(f"  Non-Current Assets ({len(assets_non_current)} items):")
            for item in assets_non_current:
                if isinstance(item, dict):
                    print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):,.0f}")
            
            print(f"\n--- LIABILITIES DETAIL ---")
            print(f"  Current Liabilities ({len(liabilities_current)} items):")
            for item in liabilities_current:
                if isinstance(item, dict):
                    print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):,.0f}")
            
            print(f"  Non-Current Liabilities ({len(liabilities_non_current)} items):")
            for item in liabilities_non_current:
                if isinstance(item, dict):
                    print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):,.0f}")
            
            print(f"\n--- EQUITY DETAIL ---")
            for item in equity_items:
                if isinstance(item, dict):
                    print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):,.0f}")
            
            # Check income statement for the year
            print(f"\n--- INCOME STATEMENT CHECK ---")
            year_start = f"{year}-01-01"
            year_end = f"{year}-12-31"
            
            income_data = fetch_income_statement_data(
                conn, year_start, year_end, company_id, 
                report_type='real', comparative=False
            )
            
            net_income = income_data.get('net_income', 0.0)
            print(f"  Net Income {year}: Rp {net_income:,.0f}")
            
            # Check if "Laba/Rugi Tahun Berjalan" is in equity
            current_year_in_equity = None
            for item in equity_items:
                if isinstance(item, dict) and 'Laba/Rugi Tahun Berjalan' in item.get('name', ''):
                    current_year_in_equity = item.get('amount', 0)
                    break
            
            print(f"  Laba/Rugi Tahun Berjalan in Equity: Rp {current_year_in_equity:,.0f}" if current_year_in_equity else "  Laba/Rugi Tahun Berjalan in Equity: NOT FOUND")
            
            # Check previous year retained earnings
            prev_re = None
            for item in equity_items:
                if isinstance(item, dict) and 'Laba Ditahan' in item.get('name', ''):
                    prev_re = item.get('amount', 0)
                    break
            
            if prev_re is not None:
                print(f"  Laba Ditahan Tahun Sebelumnya: Rp {prev_re:,.0f}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("KESIMPULAN")
    print(f"{'='*80}")
    print("""
Kemungkinan penyebab Balance Sheet tidak balance:

1. Laba Ditahan Tahun Sebelumnya tidak diperhitungkan dengan benar
   - Sebelum fix: hanya mengambil 1 tahun sebelumnya
   - Setelah fix: mengambil akumulasi semua tahun sebelumnya

2. Laba/Rugi Tahun Berjalan tidak masuk ke Equity dengan benar

3. Ada transaksi yang tidak terklasifikasi dengan benar

4. Ada perhitungan amortisasi/depresiasi yang belum ter-update

Cek perbedaan antara:
  - Net Income di Income Statement
  - Laba/Rugi Tahun Berjalan di Balance Sheet Equity
""")
