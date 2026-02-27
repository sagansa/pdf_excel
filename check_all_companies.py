"""
Script untuk mengecek semua company dan Balance Sheet-nya
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_balance_sheet_data

# Koneksi ke MySQL
engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")

with engine.connect() as conn:
    print("=" * 80)
    print("CEK SEMUA COMPANY DAN BALANCE SHEET")
    print("=" * 80)
    
    # Get unique companies dengan info lebih detail
    companies = conn.execute(text("""
        SELECT 
            t.company_id,
            COUNT(DISTINCT t.id) as txn_count,
            MIN(t.txn_date) as first_txn,
            MAX(t.txn_date) as last_txn,
            SUM(t.amount) as total_amount
        FROM transactions t
        WHERE t.company_id IS NOT NULL
        GROUP BY t.company_id
        ORDER BY first_txn
    """)).fetchall()
    
    print(f"\n{'Company ID':<40} | {'Txns':>6} | {'First':>12} | {'Last':>12} | {'Total Amount':>18}")
    print("-" * 40 + "-+-" + "-"*6 + "-+-" + "-"*12 + "-+-" + "-"*12 + "-+-" + "-"*18)
    
    for comp in companies:
        print(f"{comp.company_id:<40} | {comp.txn_count:>6} | {str(comp.first_txn):>12} | {str(comp.last_txn):>12} | {comp.total_amount:>18,.0f}")
    
    # Cek Balance Sheet untuk setiap company
    print(f"\n{'='*80}")
    print("BALANCE SHEET SUMMARY PER COMPANY")
    print(f"{'='*80}")
    
    for comp in companies:
        company_id = comp.company_id
        print(f"\n{'='*60}")
        print(f"Company: {company_id}")
        print(f"{'='*60}")
        
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
                
                print(f"  {year}: Assets={total_assets:>18,.0f} | Liab={total_liabilities:>12,.0f} | Equity={total_equity:>18,.0f} | {'✓' if is_balanced else '✗':>3}")
                
            except Exception as e:
                print(f"  {year}: ERROR - {str(e)[:50]}")
