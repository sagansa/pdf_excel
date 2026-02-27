"""
Script untuk mencari penyebab selisih Balance Sheet 2024 dan 2025
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_balance_sheet_data, fetch_income_statement_data

engine = create_engine('mysql+pymysql://root:root@127.0.0.1:3306/bank_converter')

with engine.connect() as conn:
    company_id = '8ab69d4a-e591-4f05-909e-25ff12352efb'
    
    print("=" * 80)
    print("ANALISA DETAIL SELISIH BALANCE SHEET 2024 & 2025")
    print("=" * 80)
    
    # 1. Cek Net Income per tahun
    print("\n=== 1. NET INCOME PER TAHUN ===")
    yearly_net_incomes = {}
    for year in [2023, 2024, 2025]:
        income = fetch_income_statement_data(conn, f'{year}-01-01', f'{year}-12-31', company_id, report_type='real', comparative=False)
        net_income = income.get('net_income', 0.0)
        yearly_net_incomes[year] = net_income
        print(f"  {year}: Rp {net_income:>15,.0f}")
    
    # 2. Hitung Laba Ditahan Kumulatif
    print("\n=== 2. LABA DITAHAN KUMULATIF ===")
    for year in [2023, 2024, 2025]:
        cumulative = sum(yearly_net_incomes.get(y, 0) for y in range(2023, year))
        print(f"  {year}: Rp {cumulative:>15,.0f} (akumulasi 2023-{year-1})")
    
    # 3. Cek Balance Sheet detail 2024
    print("\n=== 3. ANALISA BALANCE SHEET 2024 ===")
    bs_2024 = fetch_balance_sheet_data(conn, '2024-12-31', company_id, report_type='real')
    
    assets_2024 = bs_2024.get('assets', {})
    liabilities_2024 = bs_2024.get('liabilities', {})
    equity_2024 = bs_2024.get('equity', {})
    
    print("\n  ASSETS:")
    for item in assets_2024.get('current', []):
        if isinstance(item, dict):
            print(f"    {item.get('code')}: {item.get('name')} = Rp {item.get('amount'):>15,.0f}")
    for item in assets_2024.get('non_current', []):
        if isinstance(item, dict):
            print(f"    {item.get('code')}: {item.get('name')} = Rp {item.get('amount'):>15,.0f}")
    
    print("\n  LIABILITIES:")
    for item in liabilities_2024.get('current', []):
        if isinstance(item, dict):
            print(f"    {item.get('code')}: {item.get('name')} = Rp {item.get('amount'):>15,.0f}")
    
    print("\n  EQUITY:")
    for item in equity_2024.get('items', []):
        if isinstance(item, dict):
            print(f"    {item.get('code')}: {item.get('name')} = Rp {item.get('amount'):>15,.0f}")
    
    # Hitung manual
    total_assets_2024 = assets_2024.get('total', 0)
    total_liabilities_2024 = liabilities_2024.get('total', 0)
    total_equity_2024 = equity_2024.get('total', 0)
    
    print(f"\n  TOTALS:")
    print(f"    Assets:     Rp {total_assets_2024:>15,.0f}")
    print(f"    Liabilities:Rp {total_liabilities_2024:>15,.0f}")
    print(f"    Equity:     Rp {total_equity_2024:>15,.0f}")
    print(f"    Liab+Equity:Rp {total_liabilities_2024 + total_equity_2024:>15,.0f}")
    print(f"    DIFF:       Rp {total_assets_2024 - (total_liabilities_2024 + total_equity_2024):>15,.0f}")
    
    # 4. Cek transaksi per tahun
    print("\n=== 4. TRANSAKSI PER TAHUN ===")
    txn_summary = conn.execute(text("""
        SELECT 
            YEAR(txn_date) as year,
            COUNT(*) as count,
            SUM(amount) as total_amount
        FROM transactions
        WHERE company_id = :company_id
        GROUP BY YEAR(txn_date)
        ORDER BY year
    """), {'company_id': company_id}).fetchall()
    
    for row in txn_summary:
        print(f"  {row.year}: {row.count} transaksi, Total: Rp {row.total_amount:>15,.0f}")
    
    # 5. Cek COA mapping per kategori
    print("\n=== 5. SALDO PER KATEGORI COA (2024) ===")
    coa_balances = conn.execute(text("""
        SELECT 
            coa.category,
            SUM(CASE WHEN mcm.mapping_type = 'DEBIT' THEN t.amount
                     WHEN mcm.mapping_type = 'CREDIT' THEN -t.amount
                     ELSE 0 END) as balance
        FROM transactions t
        JOIN marks m ON t.mark_id = m.id
        JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.company_id = :company_id
        AND YEAR(t.txn_date) >= 2023
        GROUP BY coa.category
    """), {'company_id': company_id}).fetchall()
    
    for row in coa_balances:
        print(f"  {row.category}: Rp {row.balance:>15,.0f}")
    
    # 6. Cek Initial Capital
    print("\n=== 6. INITIAL CAPITAL ===")
    initial_capital = conn.execute(text("""
        SELECT amount, start_year, description
        FROM initial_capital_settings
        WHERE company_id = :company_id
    """), {'company_id': company_id}).fetchone()
    
    if initial_capital:
        print(f"  Amount: Rp {initial_capital.amount:>15,.0f}")
        print(f"  Start Year: {initial_capital.start_year}")
        print(f"  Description: {initial_capital.description}")
    else:
        print("  Tidak ada Initial Capital")
    
    # 7. Analisa selisih
    print("\n=== 7. ANALISA SELISIH ===")
    
    # Expected Equity 2024
    expected_equity_2024 = float(initial_capital.amount) + sum(yearly_net_incomes.get(y, 0) for y in [2023, 2024])
    print(f"\n  Expected Equity 2024:")
    print(f"    Initial Capital: Rp {float(initial_capital.amount):>15,.0f}")
    print(f"    + Net Income 2023: Rp {yearly_net_incomes.get(2023, 0):>15,.0f}")
    print(f"    + Net Income 2024: Rp {yearly_net_incomes.get(2024, 0):>15,.0f}")
    print(f"    = Expected Equity: Rp {expected_equity_2024:>15,.0f}")
    print(f"    Actual Equity:     Rp {total_equity_2024:>15,.0f}")
    print(f"    Diff:              Rp {expected_equity_2024 - total_equity_2024:>15,.0f}")
    
    # Expected Assets 2024
    print(f"\n  Expected Assets 2024:")
    print(f"    Liabilities: Rp {total_liabilities_2024:>15,.0f}")
    print(f"    + Expected Equity: Rp {expected_equity_2024:>15,.0f}")
    print(f"    = Expected Assets: Rp {total_liabilities_2024 + expected_equity_2024:>15,.0f}")
    print(f"    Actual Assets:     Rp {total_assets_2024:>15,.0f}")
    print(f"    Diff:              Rp {total_assets_2024 - (total_liabilities_2024 + expected_equity_2024):>15,.0f}")
    
    # 8. Cek apakah ada transaksi yang tidak ter-mapping
    print("\n=== 8. CEK TRANSAKSI TIDAK TER-MAPPING ===")
    unmapped = conn.execute(text("""
        SELECT 
            COUNT(*) as count,
            SUM(amount) as total
        FROM transactions t
        LEFT JOIN marks m ON t.mark_id = m.id
        LEFT JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        WHERE t.company_id = :company_id
        AND YEAR(t.txn_date) >= 2023
        AND (m.id IS NULL OR mcm.mark_id IS NULL)
    """), {'company_id': company_id}).fetchone()
    
    print(f"  Transaksi tanpa mapping: {unmapped.count}, Total: Rp {unmapped.total:,.0f}")
    
    # 9. Cek marks yang tidak punya mapping ke COA
    print("\n=== 9. MARKS TANPA MAPPING COA ===")
    marks_no_coa = conn.execute(text("""
        SELECT 
            m.id,
            m.personal_use,
            m.internal_report,
            COUNT(*) as count,
            SUM(t.amount) as total
        FROM transactions t
        JOIN marks m ON t.mark_id = m.id
        LEFT JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        WHERE t.company_id = :company_id
        AND YEAR(t.txn_date) >= 2023
        AND mcm.mark_id IS NULL
        GROUP BY m.id, m.personal_use, m.internal_report
        LIMIT 10
    """), {'company_id': company_id}).fetchall()
    
    if marks_no_coa:
        for row in marks_no_coa:
            print(f"  {row.id}: {row.personal_use} / {row.internal_report} - {row.count} txn, Rp {row.total:,.0f}")
    else:
        print("  (semua marks punya mapping COA)")
