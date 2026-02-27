"""
Script untuk investigasi data Laba Ditahan
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_income_statement_data

engine = create_engine("sqlite:///database.db")

with engine.connect() as conn:
    # Cek data company yang ada
    print("=== Checking Companies ===")
    companies = conn.execute(text("""
        SELECT DISTINCT company_id FROM transactions WHERE company_id IS NOT NULL
    """)).fetchall()
    
    for comp in companies:
        company_id = comp.company_id
        print(f"\n=== Company: {company_id} ===")
        
        # Cek net income per tahun
        print("\n--- Net Income per Year ---")
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
        
        # Cek transaksi per tahun
        print("\n--- Transaction Summary ---")
        for year in [2023, 2024, 2025]:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as count,
                    COALESCE(SUM(amount), 0) as total_amount
                FROM transactions
                WHERE company_id = :company_id
                AND strftime('%Y', txn_date) = :year
            """), {'company_id': company_id, 'year': str(year)}).fetchone()
            
            print(f"  {year}: {result.count} transactions, Total Amount={result.total_amount:,.0f}")
