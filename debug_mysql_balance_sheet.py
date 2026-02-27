#!/usr/bin/env python3
"""
Script untuk debug Balance Sheet dan Retained Earnings di MySQL
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_income_statement_data, fetch_balance_sheet_data

# Koneksi ke MySQL
engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")

with engine.connect() as conn:
    # Cek semua company yang ada
    print("=== Checking All Companies (MySQL) ===")
    companies = conn.execute(text("""
        SELECT DISTINCT company_id FROM transactions WHERE company_id IS NOT NULL
    """)).fetchall()
    
    if not companies:
        print("No companies found in database!")
        # Cek tabel companies
        companies_table = conn.execute(text("SHOW TABLES LIKE 'companies'")).fetchall()
        print(f"Companies table exists: {len(companies_table) > 0}")
        
        if companies_table:
            companies_data = conn.execute(text("SELECT * FROM companies")).fetchall()
            print(f"Companies in table: {companies_data}")
    
    for comp in companies:
        company_id = comp.company_id
        print(f"\n{'='*60}")
        print(f"Company: {company_id}")
        print(f"{'='*60}")
        
        # Cek apakah tabel initial_capital_settings ada
        print("\n--- Checking initial_capital_settings table ---")
        try:
            initial_capital = conn.execute(text("""
                SELECT * FROM initial_capital_settings WHERE company_id = :company_id
            """), {'company_id': company_id}).fetchall()
            print(f"initial_capital_settings rows: {len(initial_capital)}")
            for row in initial_capital:
                print(f"  {row}")
        except Exception as e:
            print(f"Error checking initial_capital_settings: {e}")
        
        # Cek net income per tahun (2023, 2024, 2025)
        print("\n--- Net Income per Year ---")
        yearly_net_incomes = {}
        for year in [2023, 2024, 2025]:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            
            try:
                income_data = fetch_income_statement_data(
                    conn, start_date, end_date, company_id, 
                    report_type='real', comparative=False
                )
                net_income = income_data.get('net_income', 0.0)
                yearly_net_incomes[year] = net_income
                
                print(f"  {year} Net Income: Rp {net_income:,.0f}")
            except Exception as e:
                print(f"  {year} Error: {e}")
                yearly_net_incomes[year] = 0.0
        
        # Hitung cumulative manually
        print("\n--- Manual Cumulative Calculation ---")
        cumulative = 0.0
        for year in sorted(yearly_net_incomes.keys()):
            cumulative += yearly_net_incomes[year]
            print(f"  After {year}: Cumulative = Rp {cumulative:,.0f}")
        
        # Cek Balance Sheet untuk setiap tahun
        print("\n--- Balance Sheet Equity Section ---")
        for year in [2023, 2024, 2025]:
            as_of_date = f"{year}-12-31"
            print(f"\n  As of {as_of_date}:")
            
            try:
                bs_data = fetch_balance_sheet_data(
                    conn, as_of_date, company_id, report_type='real'
                )
                
                print(f"  Total Assets: Rp {bs_data.get('assets', {}).get('total', 0):,.0f}")
                print(f"  Total Liabilities & Equity: Rp {bs_data.get('total_liabilities_and_equity', 0):,.0f}")
                print(f"  Is Balanced: {bs_data.get('is_balanced', False)}")
                
                equity_data = bs_data.get('equity', {})
                equity_items = equity_data.get('items', []) if isinstance(equity_data, dict) else []
                
                print(f"  Equity Items ({len(equity_items)}):")
                for item in equity_items:
                    if isinstance(item, dict):
                        name = item.get('name', '')
                        amount = item.get('amount', 0.0)
                        code = item.get('code', '')
                        is_computed = item.get('is_computed', False)
                        
                        print(f"    {code}: {name} = Rp {amount:,.0f} {'(computed)' if is_computed else ''}")
                
            except Exception as e:
                print(f"    Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Expected Retained Earnings untuk setiap tahun
        print("\n--- Expected Retained Earnings Logic ---")
        cumulative = 0.0
        for year in [2023, 2024, 2025]:
            # Retained earnings di tahun X adalah akumulasi dari tahun-tahun sebelumnya
            if year == 2023:
                expected_re = 0.0  # Tidak ada retained earnings di tahun pertama
            else:
                # Akumulasi dari semua tahun sebelumnya
                expected_re = sum(yearly_net_incomes.get(y, 0.0) for y in range(2023, year))
            
            print(f"  {year}-12-31: Expected Retained Earnings = Rp {expected_re:,.0f}")
            
            # Logika seharusnya di balance sheet
            print(f"    -> Current Year Earnings (4800): Rp {yearly_net_incomes.get(year, 0):,.0f}")
            print(f"    -> Previous Year Retained Earnings (3200): Rp {expected_re - yearly_net_incomes.get(year, 0):,.0f}")

print("\n=== Debug completed ===")
