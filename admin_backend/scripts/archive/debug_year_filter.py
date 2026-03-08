"""
Script untuk debug filter tahun di Balance Sheet
"""
from sqlalchemy import create_engine, text

# Koneksi ke MySQL
engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")

with engine.connect() as conn:
    company_id = "8ab69d4a-e591-4f05-909e-25ff12352efb"
    
    print("=" * 80)
    print("DEBUG FILTER TAHUN DI BALANCE SHEET")
    print("=" * 80)
    
    # 1. Cek Initial Capital
    print("\n=== 1. INITIAL CAPITAL ===")
    initial_capital = conn.execute(text("""
        SELECT amount, start_year, description
        FROM initial_capital_settings
        WHERE company_id = :company_id
    """), {'company_id': company_id}).fetchone()
    
    if initial_capital:
        print(f"  Amount: Rp {initial_capital.amount:,.0f}")
        print(f"  Start Year: {initial_capital.start_year}")
    else:
        print("  Tidak ada")
    
    # 2. Cek transaksi per tahun
    print("\n=== 2. TRANSAKSI PER TAHUN ===")
    txn_per_year = conn.execute(text("""
        SELECT 
            YEAR(txn_date) as year,
            COUNT(*) as count,
            SUM(amount) as total
        FROM transactions
        WHERE company_id = :company_id
        GROUP BY YEAR(txn_date)
        ORDER BY year
    """), {'company_id': company_id}).fetchall()
    
    for row in txn_per_year:
        print(f"  {row.year}: {row.count} transaksi, Total: Rp {row.total:,.0f}")
    
    # 3. Cek Equity dari transaksi (mark_coa_mapping) per tahun
    print("\n=== 3. EQUITY DARI TRANSAKSI (per tahun) ===")
    equity_per_year = conn.execute(text("""
        SELECT 
            YEAR(t.txn_date) as year,
            coa.category,
            SUM(CASE WHEN mcm.mapping_type = 'DEBIT' THEN t.amount 
                     WHEN mcm.mapping_type = 'CREDIT' THEN -t.amount 
                     ELSE 0 END) as total
        FROM transactions t
        JOIN marks m ON t.mark_id = m.id
        JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.company_id = :company_id
        AND coa.category = 'EQUITY'
        GROUP BY YEAR(t.txn_date), coa.category
        ORDER BY year
    """), {'company_id': company_id}).fetchall()
    
    for row in equity_per_year:
        print(f"  {row.year} - {row.category}: Rp {row.total:,.0f}")
    
    # 4. Hitung manual Balance Sheet 2024
    print("\n=== 4. HITUNG MANUAL BALANCE SHEET 2024 ===")
    
    # Assets dari transaksi 2023+2024
    assets = conn.execute(text("""
        SELECT 
            SUM(CASE WHEN mcm.mapping_type = 'DEBIT' THEN t.amount 
                     WHEN mcm.mapping_type = 'CREDIT' THEN -t.amount 
                     ELSE 0 END) as total
        FROM transactions t
        JOIN marks m ON t.mark_id = m.id
        JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.company_id = :company_id
        AND t.txn_date <= '2024-12-31'
        AND YEAR(t.txn_date) >= 2023
        AND coa.category = 'ASSET'
    """), {'company_id': company_id}).fetchone()
    
    print(f"  Assets (2023+2024): Rp {assets.total:,.0f}")
    
    # Liabilities dari transaksi 2023+2024
    liabilities = conn.execute(text("""
        SELECT 
            SUM(CASE WHEN mcm.mapping_type = 'DEBIT' THEN t.amount 
                     WHEN mcm.mapping_type = 'CREDIT' THEN -t.amount 
                     ELSE 0 END) as total
        FROM transactions t
        JOIN marks m ON t.mark_id = m.id
        JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.company_id = :company_id
        AND t.txn_date <= '2024-12-31'
        AND YEAR(t.txn_date) >= 2023
        AND coa.category = 'LIABILITY'
    """), {'company_id': company_id}).fetchone()
    
    print(f"  Liabilities (2023+2024): Rp {liabilities.total:,.0f}")
    
    # Equity dari transaksi 2023+2024
    equity_txn = conn.execute(text("""
        SELECT 
            SUM(CASE WHEN mcm.mapping_type = 'DEBIT' THEN t.amount 
                     WHEN mcm.mapping_type = 'CREDIT' THEN -t.amount 
                     ELSE 0 END) as total
        FROM transactions t
        JOIN marks m ON t.mark_id = m.id
        JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.company_id = :company_id
        AND t.txn_date <= '2024-12-31'
        AND YEAR(t.txn_date) >= 2023
        AND coa.category = 'EQUITY'
    """), {'company_id': company_id}).fetchone()
    
    print(f"  Equity dari transaksi (2023+2024): Rp {equity_txn.total:,.0f}")
    
    # Initial Capital
    print(f"  Initial Capital: Rp {initial_capital.amount:,.0f}")
    
    # Total Equity
    total_equity = float(initial_capital.amount) + (equity_txn.total if equity_txn.total else 0)
    print(f"  Total Equity (Initial + Txn): Rp {total_equity:,.0f}")
    
    # Liab + Equity
    liab_plus_equity = (liabilities.total if liabilities.total else 0) + total_equity
    print(f"  Liab + Equity: Rp {liab_plus_equity:,.0f}")
    
    # Difference
    diff = (assets.total if assets.total else 0) - liab_plus_equity
    print(f"  Assets - (Liab + Equity): Rp {diff:,.0f}")
