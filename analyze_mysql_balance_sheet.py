"""
Script untuk analisa Balance Sheet menggunakan MySQL database yang sebenarnya
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_balance_sheet_data, fetch_income_statement_data

# Koneksi ke MySQL
engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")

with engine.connect() as conn:
    # Cek companies yang ada
    print("=" * 80)
    print("ANALISA BALANCE SHEET - MYSQL DATABASE")
    print("=" * 80)
    
    print("\n=== COMPANIES YANG ADA ===")
    companies = conn.execute(text("""
        SELECT DISTINCT company_id FROM transactions WHERE company_id IS NOT NULL
    """)).fetchall()
    
    for comp in companies:
        company_id = comp.company_id
        print(f"  - {company_id}")
    
    # Pilih company pertama untuk analisa
    if companies:
        company_id = companies[0].company_id
        
        print(f"\n{'='*80}")
        print(f"ANALISA UNTUK COMPANY: {company_id}")
        print(f"{'='*80}")
        
        for year in [2023, 2024, 2025]:
            as_of_date = f"{year}-12-31"
            print(f"\n--- TAHUN {year} ({as_of_date}) ---")
            
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
                
                print(f"  Total Assets:     Rp {total_assets:,.0f}")
                print(f"  Total Liabilities: Rp {total_liabilities:,.0f}")
                print(f"  Total Equity:     Rp {total_equity:,.0f}")
                print(f"  Liab + Equity:    Rp {total_liabilities + total_equity:,.0f}")
                
                difference = total_assets - (total_liabilities + total_equity)
                print(f"  DIFFERENCE:       Rp {difference:,.0f}")
                print(f"  IS BALANCED:      {abs(difference) < 0.01}")
                
                # Equity items
                equity_items = equity.get('items', [])
                if equity_items:
                    print(f"  Equity Items:")
                    for item in equity_items:
                        if isinstance(item, dict):
                            print(f"    {item.get('code', '')}: {item.get('name', '')} = Rp {item.get('amount', 0):,.0f}")
                
            except Exception as e:
                print(f"  ERROR: {e}")
        
        # Cek transaksi summary
        print(f"\n=== TRANSAKSI SUMMARY ===")
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
            print(f"  {row.year}: {row.count} transaksi, Total: Rp {row.total_amount:,.0f}")
        
        # Cek Net Income per tahun
        print(f"\n=== NET INCOME PER TAHUN ===")
        for year in [2023, 2024, 2025]:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            
            income_data = fetch_income_statement_data(
                conn, start_date, end_date, company_id, 
                report_type='real', comparative=False
            )
            
            net_income = income_data.get('net_income', 0.0)
            revenue = income_data.get('total_revenue', 0.0)
            expenses = income_data.get('total_expenses', 0.0)
            
            print(f"  {year}: Revenue={revenue:,.0f}, Expenses={expenses:,.0f}, Net Income={net_income:,.0f}")
