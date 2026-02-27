"""
Script untuk mencari penyebab selisih di Balance Sheet
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_balance_sheet_data

# Koneksi ke MySQL
engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")

with engine.connect() as conn:
    company_id = "8ab69d4a-e591-4f05-909e-25ff12352efb"
    
    print("=" * 80)
    print("ANALISA SELISIH BALANCE SHEET 2024")
    print("=" * 80)
    
    # Cek Balance Sheet 2024
    bs_data = fetch_balance_sheet_data(
        conn, "2024-12-31", company_id, report_type='real'
    )
    
    assets = bs_data.get('assets', {})
    liabilities = bs_data.get('liabilities', {})
    equity = bs_data.get('equity', {})
    
    print("\n=== ASSETS DETAIL ===")
    assets_current = assets.get('current', [])
    assets_non_current = assets.get('non_current', [])
    
    total_assets_calc = 0
    for item in assets_current:
        if isinstance(item, dict):
            amount = item.get('amount', 0)
            print(f"  {item.get('code', '')}: {item.get('name', '')} = Rp {amount:>15,.0f}")
            total_assets_calc += amount
    
    for item in assets_non_current:
        if isinstance(item, dict):
            amount = item.get('amount', 0)
            print(f"  {item.get('code', '')}: {item.get('name', '')} = Rp {amount:>15,.0f}")
            total_assets_calc += amount
    
    print(f"  Calculated Total Assets: Rp {total_assets_calc:>15,.0f}")
    print(f"  Reported Total Assets:   Rp {assets.get('total', 0):>15,.0f}")
    
    print("\n=== LIABILITIES DETAIL ===")
    liabilities_current = liabilities.get('current', [])
    liabilities_non_current = liabilities.get('non_current', [])
    
    total_liabilities_calc = 0
    for item in liabilities_current:
        if isinstance(item, dict):
            amount = item.get('amount', 0)
            print(f"  {item.get('code', '')}: {item.get('name', '')} = Rp {amount:>15,.0f}")
            total_liabilities_calc += amount
    
    for item in liabilities_non_current:
        if isinstance(item, dict):
            amount = item.get('amount', 0)
            print(f"  {item.get('code', '')}: {item.get('name', '')} = Rp {amount:>15,.0f}")
            total_liabilities_calc += amount
    
    print(f"  Calculated Total Liabilities: Rp {total_liabilities_calc:>15,.0f}")
    print(f"  Reported Total Liabilities:   Rp {liabilities.get('total', 0):>15,.0f}")
    
    print("\n=== EQUITY DETAIL ===")
    equity_items = equity.get('items', [])
    
    total_equity_calc = 0
    for item in equity_items:
        if isinstance(item, dict):
            amount = item.get('amount', 0)
            print(f"  {item.get('code', '')}: {item.get('name', '')} = Rp {amount:>15,.0f}")
            total_equity_calc += amount
    
    print(f"  Calculated Total Equity: Rp {total_equity_calc:>15,.0f}")
    print(f"  Reported Total Equity:   Rp {equity.get('total', 0):>15,.0f}")
    
    print("\n=== BALANCE CHECK ===")
    print(f"  Total Assets:                  Rp {total_assets_calc:>15,.0f}")
    print(f"  Total Liabilities:             Rp {total_liabilities_calc:>15,.0f}")
    print(f"  Total Equity:                  Rp {total_equity_calc:>15,.0f}")
    print(f"  Liab + Equity:                 Rp {total_liabilities_calc + total_equity_calc:>15,.0f}")
    print(f"  DIFFERENCE (Assets - L - E):   Rp {total_assets_calc - (total_liabilities_calc + total_equity_calc):>15,.0f}")
    
    # Cek apakah ada masalah dengan transaksi 2022
    print("\n=== CEK TRANSAKSI 2022 ===")
    txn_2022 = conn.execute(text("""
        SELECT 
            COUNT(*) as count,
            SUM(amount) as total_amount
        FROM transactions
        WHERE company_id = :company_id
        AND YEAR(txn_date) = 2022
    """), {'company_id': company_id}).fetchone()
    
    print(f"  Transaksi 2022: {txn_2022.count} transaksi, Total: Rp {txn_2022.total_amount:,.0f}")
    
    # Cek Net Income 2022 detail
    print("\n=== CEK NET INCOME 2022 DETAIL ===")
    income_2022 = conn.execute(text("""
        SELECT 
            coa.code,
            coa.name,
            coa.type,
            SUM(CASE WHEN t.db_cr = 'DR' THEN t.amount ELSE 0 END) as debit,
            SUM(CASE WHEN t.db_cr = 'CR' THEN t.amount ELSE 0 END) as credit,
            SUM(CASE WHEN t.db_cr = 'DR' THEN t.amount ELSE -t.amount END) as net
        FROM transactions t
        JOIN marks m ON t.mark_id = m.id
        JOIN mark_coa_mappings mcm ON m.id = mcm.mark_id AND mcm.report_type = 'internal_report'
        JOIN coa ON mcm.coa_code = coa.code
        WHERE t.company_id = :company_id
        AND YEAR(t.txn_date) = 2022
        GROUP BY coa.code, coa.name, coa.type
        ORDER BY coa.code
    """), {'company_id': company_id}).fetchall()
    
    if income_2022:
        for row in income_2022:
            print(f"  {row.code}: {row.name} ({row.type}) - Dr: {row.debit:,.0f}, Cr: {row.credit:,.0f}, Net: {row.net:,.0f}")
    else:
        print("  Tidak ada data income 2022 dari mark_coa_mappings")
        
        # Cek marks yang digunakan di 2022
        print("\n  Marks yang digunakan di 2022:")
        marks_2022 = conn.execute(text("""
            SELECT 
                m.id,
                m.personal_use,
                m.internal_report,
                m.tax_report,
                COUNT(*) as count,
                SUM(t.amount) as total
            FROM transactions t
            JOIN marks m ON t.mark_id = m.id
            WHERE t.company_id = :company_id
            AND YEAR(t.txn_date) = 2022
            GROUP BY m.id, m.personal_use, m.internal_report, m.tax_report
        """), {'company_id': company_id}).fetchall()
        
        for row in marks_2022:
            print(f"    {row.id}: {row.personal_use} - {row.count} txn, Total: {row.total:,.0f}")
