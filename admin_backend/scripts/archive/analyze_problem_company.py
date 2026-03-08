"""
Script untuk analisa detail company 8ab69d4a-e591-4f05-909e-25ff12352efb yang tidak balance
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_balance_sheet_data, fetch_income_statement_data

# Koneksi ke MySQL
engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")

with engine.connect() as conn:
    company_id = "8ab69d4a-e591-4f05-909e-25ff12352efb"
    
    print("=" * 80)
    print(f"ANALISA DETAIL: {company_id}")
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
        revenue = income_data.get('total_revenue', 0.0)
        expenses = income_data.get('total_expenses', 0.0)
        yearly_net_incomes[year] = net_income
        
        print(f"  {year}: Revenue={revenue:>15,.0f}, Expenses={expenses:>15,.0f}, Net Income={net_income:>15,.0f}")
    
    # 2. Hitung Laba Ditahan yang seharusnya
    print("\n=== 2. LABA DITAHAN YANG SEHARUSNYA ===")
    for report_year in [2023, 2024, 2025]:
        cumulative = sum(yearly_net_incomes.get(y, 0) for y in range(2022, report_year))
        print(f"  {report_year}-12-31: Laba Ditahan = Rp {cumulative:,.0f}")
        if report_year > 2022:
            breakdown = [f"{y}={yearly_net_incomes.get(y, 0):,.0f}" for y in range(2022, report_year)]
            print(f"           = {' + '.join(breakdown)}")
    
    # 3. Cek Balance Sheet detail untuk 2024
    print("\n=== 3. BALANCE SHEET 2024 DETAIL ===")
    bs_data = fetch_balance_sheet_data(
        conn, "2024-12-31", company_id, report_type='real'
    )
    
    assets = bs_data.get('assets', {})
    liabilities = bs_data.get('liabilities', {})
    equity = bs_data.get('equity', {})
    
    total_assets = assets.get('total', 0)
    total_liabilities = liabilities.get('total', 0)
    total_equity = equity.get('total', 0)
    
    print(f"\n  Total Assets:     Rp {total_assets:>15,.0f}")
    print(f"  Total Liabilities: Rp {total_liabilities:>15,.0f}")
    print(f"  Total Equity:     Rp {total_equity:>15,.0f}")
    print(f"  Liab + Equity:    Rp {total_liabilities + total_equity:>15,.0f}")
    print(f"  DIFFERENCE:       Rp {total_assets - (total_liabilities + total_equity):>15,.0f}")
    
    # Equity items
    print(f"\n  EQUITY ITEMS:")
    equity_items = equity.get('items', [])
    for item in equity_items:
        if isinstance(item, dict):
            print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):>15,.0f}")
    
    # Cek apakah Laba Ditahan sudah benar
    actual_retained_earnings = next((item.get('amount', 0) for item in equity_items 
                                     if isinstance(item, dict) and 'Laba Ditahan' in item.get('name', '')), 0)
    
    expected_retained_earnings = sum(yearly_net_incomes.get(y, 0) for y in range(2022, 2024))
    
    print(f"\n  Laba Ditahan Actual:   Rp {actual_retained_earnings:>15,.0f}")
    print(f"  Laba Ditahan Expected: Rp {expected_retained_earnings:>15,.0f}")
    print(f"  Difference:            Rp {actual_retained_earnings - expected_retained_earnings:>15,.0f}")
    
    # 4. Cek Initial Capital
    print(f"\n=== 4. CEK INITIAL CAPITAL ===")
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
    
    # 5. Cek tahun pertama transaksi
    print(f"\n=== 5. TAHUN PERTAMA TRANSAKSI ===")
    first_year = conn.execute(text("""
        SELECT MIN(YEAR(txn_date)) as first_year
        FROM transactions
        WHERE company_id = :company_id
    """), {'company_id': company_id}).fetchone()
    
    if first_year and first_year.first_year:
        print(f"  Tahun transaksi pertama: {first_year.first_year}")
    
    # 6. Analisa masalah
    print(f"\n{'='*80}")
    print("KESIMPULAN MASALAH")
    print(f"{'='*80}")
    
    print(f"""
  Untuk tahun 2024:
  - Assets:           Rp {total_assets:>15,.0f}
  - Liabilities:      Rp {total_liabilities:>15,.0f}
  - Equity:           Rp {total_equity:>15,.0f}
  
  - Liab + Equity:    Rp {total_liabilities + total_equity:>15,.0f}
  - Selisih:          Rp {total_assets - (total_liabilities + total_equity):>15,.0f}
  
  Kemungkinan penyebab:
  1. Laba Ditahan tidak menghitung semua tahun sebelumnya
  2. Ada item Equity yang hilang
  3. Ada transaksi yang tidak terklasifikasi dengan benar
""")
