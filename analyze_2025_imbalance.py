"""
Script untuk analisa detail kenapa 2025 tidak balance
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_balance_sheet_data, fetch_income_statement_data

# Koneksi ke MySQL
engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")

with engine.connect() as conn:
    # Gunakan company pertama
    company_id = "40e70c5f-43ef-49aa-b73e-7f83d326b301"
    
    print("=" * 80)
    print("ANALISA DETAIL KENAPA 2025 TIDAK BALANCE")
    print("=" * 80)
    
    # 1. Cek Net Income per tahun
    print("\n=== 1. NET INCOME PER TAHUN ===")
    yearly_net_incomes = {}
    for year in [2022, 2023, 2024, 2025]:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        income_data = fetch_income_statement_data(
            conn, start_date, end_date, company_id, 
            report_type='real', comparative=False
        )
        
        net_income = income_data.get('net_income', 0.0)
        yearly_net_incomes[year] = net_income
        print(f"  {year}: Rp {net_income:,.0f}")
    
    # 2. Hitung Laba Ditahan yang seharusnya
    print("\n=== 2. LABA DITAHAN YANG SEHARUSNYA ===")
    for report_year in [2023, 2024, 2025]:
        cumulative = sum(yearly_net_incomes.get(y, 0) for y in range(2022, report_year))
        print(f"  {report_year}-12-31: Laba Ditahan = Rp {cumulative:,.0f}")
        if report_year > 2022:
            breakdown = [f"{y}={yearly_net_incomes.get(y, 0):,.0f}" for y in range(2022, report_year)]
            print(f"           = {' + '.join(breakdown)}")
    
    # 3. Cek Balance Sheet 2025 detail
    print("\n=== 3. BALANCE SHEET 2025 DETAIL ===")
    bs_data = fetch_balance_sheet_data(
        conn, "2025-12-31", company_id, report_type='real'
    )
    
    assets = bs_data.get('assets', {})
    liabilities = bs_data.get('liabilities', {})
    equity = bs_data.get('equity', {})
    
    print("\n  ASSETS:")
    assets_current = assets.get('current', [])
    assets_non_current = assets.get('non_current', [])
    
    for item in assets_current:
        if isinstance(item, dict):
            print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):,.0f}")
    
    for item in assets_non_current:
        if isinstance(item, dict):
            print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):,.0f}")
    
    print(f"\n  TOTAL ASSETS: Rp {assets.get('total', 0):,.0f}")
    
    print("\n  LIABILITIES:")
    liabilities_current = liabilities.get('current', [])
    liabilities_non_current = liabilities.get('non_current', [])
    
    for item in liabilities_current:
        if isinstance(item, dict):
            print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):,.0f}")
    
    for item in liabilities_non_current:
        if isinstance(item, dict):
            print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):,.0f}")
    
    print(f"\n  TOTAL LIABILITIES: Rp {liabilities.get('total', 0):,.0f}")
    
    print("\n  EQUITY:")
    equity_items = equity.get('items', [])
    for item in equity_items:
        if isinstance(item, dict):
            print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):,.0f}")
    
    print(f"\n  TOTAL EQUITY: Rp {equity.get('total', 0):,.0f}")
    
    # 4. Analisa masalah
    print("\n" + "=" * 80)
    print("ANALISA MASALAH")
    print("=" * 80)
    
    total_assets = assets.get('total', 0)
    total_liabilities = liabilities.get('total', 0)
    total_equity = equity.get('total', 0)
    
    print(f"""
  Total Assets:     Rp {total_assets:,.0f}
  Total Liabilities: Rp {total_liabilities:,.0f}
  Total Equity:     Rp {total_equity:,.0f}
  
  Liab + Equity:    Rp {total_liabilities + total_equity:,.0f}
  DIFFERENCE:       Rp {total_assets - (total_liabilities + total_equity):,.0f}
  
  EXPECTED Laba Ditahan (2022+2023+2024):
    = {yearly_net_incomes.get(2022, 0):,.0f} + {yearly_net_incomes.get(2023, 0):,.0f} + {yearly_net_incomes.get(2024, 0):,.0f}
    = {sum(yearly_net_incomes.get(y, 0) for y in [2022, 2023, 2024]):,.0f}
  
  ACTUAL Laba Ditahan di Balance Sheet:
    = {next((item.get('amount', 0) for item in equity_items if isinstance(item, dict) and 'Laba Ditahan' in item.get('name', '')), 0):,.0f}
  
  Laba/Rugi Tahun Berjalan 2025:
    = {yearly_net_incomes.get(2025, 0):,.0f}
""")
    
    # 5. Cek apakah ada masalah dengan initial capital
    print("\n=== 4. CEK INITIAL CAPITAL ===")
    try:
        initial_capital = conn.execute(text("""
            SELECT amount, start_year, description
            FROM initial_capital_settings
            WHERE company_id = :company_id
        """), {'company_id': company_id}).fetchone()
        
        if initial_capital:
            print(f"  Initial Capital: Rp {initial_capital.amount:,.0f}")
            print(f"  Start Year: {initial_capital.start_year}")
            print(f"  Description: {initial_capital.description}")
        else:
            print("  Tidak ada Initial Capital setting")
    except Exception as e:
        print(f"  Error: {e}")
    
    # 6. Cek Assets detail
    print("\n=== 5. CEK ASSETS DETAIL ===")
    print("  Apakah ada Kas/Bank yang seharusnya tercatat?")
    
    # Cek transaksi yang mungkin masuk ke Assets
    asset_txns = conn.execute(text("""
        SELECT 
            m.personal_use,
            COUNT(*) as count,
            SUM(t.amount) as total
        FROM transactions t
        LEFT JOIN marks m ON t.mark_id = m.id
        WHERE t.company_id = :company_id
        AND m.is_asset = 1
        GROUP BY m.personal_use
    """), {'company_id': company_id}).fetchall()
    
    if asset_txns:
        for row in asset_txns:
            print(f"  {row.personal_use}: {row.count} transaksi, Total: Rp {row.total:,.0f}")
    else:
        print("  Tidak ada transaksi dengan mark is_asset=1")
