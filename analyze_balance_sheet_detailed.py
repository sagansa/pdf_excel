"""
Script untuk melihat detail transaksi dan kenapa Balance Sheet tidak balance
"""
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///database.db")

with engine.connect() as conn:
    company_id = "demo-company"
    
    print("=" * 80)
    print("ANALISA TRANSAKSI DAN AKUN")
    print("=" * 80)
    
    # Lihat semua transaksi
    print("\n--- SEMUA TRANSAKSI ---")
    txns = conn.execute(text("""
        SELECT id, txn_date, code, debit, credit, amount, description, parent_id
        FROM transactions
        WHERE company_id = :company_id
        ORDER BY txn_date, created_at
    """), {'company_id': company_id}).fetchall()
    
    for txn in txns:
        parent_info = "(parent)" if not txn.parent_id else f"(child of {txn.parent_id})"
        print(f"  {txn.txn_date} | {txn.code} | Dr: {txn.debit:,.0f} | Cr: {txn.credit:,.0f} | Amt: {txn.amount:,.0f} | {txn.description[:30]} | {parent_info}")
    
    # Lihat COA yang digunakan
    print("\n--- COA DIGUNAKAN DI TRANSAKSI ---")
    coa_usage = conn.execute(text("""
        SELECT code, COUNT(*) as count, SUM(amount) as total_amount
        FROM transactions
        WHERE company_id = :company_id
        GROUP BY code
        ORDER BY code
    """), {'company_id': company_id}).fetchall()
    
    for coa in coa_usage:
        print(f"  {coa.code}: {coa.count} transaksi, Total: {coa.total_amount:,.0f}")
    
    # Lihat COA master
    print("\n--- COA MASTER LIST ---")
    coas = conn.execute(text("""
        SELECT code, name, type, category_code
        FROM coa
        ORDER BY code
    """)).fetchall()
    
    for coa in coas:
        print(f"  {coA.code}: {coA.name} | Type: {coA.type} | Category: {coA.category_code}")
    
    # Cek transaksi dengan parent_id
    print("\n--- CEK TRANSAKSI DENGAN PARENT_ID ---")
    parent_txns = conn.execute(text("""
        SELECT id, txn_date, code, debit, credit, amount, description
        FROM transactions
        WHERE company_id = :company_id AND parent_id IS NOT NULL
        ORDER BY txn_date
    """), {'company_id': company_id}).fetchall()
    
    if parent_txns:
        for txn in parent_txns:
            print(f"  {txn.id} | {txn.txn_date} | {txn.code} | Dr: {txn.debit:,.0f} | Cr: {txn.credit:,.0f} | Amt: {txn.amount:,.0f}")
    else:
        print("  (tidak ada)")
    
    # Cek apakah ada transaksi yang seharusnya di-exclude karena punya parent
    print("\n--- CEK PARENT TRANSACTIONS ---")
    parents = conn.execute(text("""
        SELECT id, txn_date, code, debit, credit, amount, description
        FROM transactions
        WHERE company_id = :company_id AND parent_id IS NULL
        ORDER BY txn_date
    """), {'company_id': company_id}).fetchall()
    
    for parent in parents:
        children = conn.execute(text("""
            SELECT COUNT(*) as count, SUM(amount) as total_amt
            FROM transactions
            WHERE parent_id = :parent_id
        """), {'parent_id': parent.id}).fetchone()
        
        if children.count > 0:
            print(f"  PARENT {parent.id}: {children.count} children, Total amt: {children.total_amt:,.0f}")
            print(f"    Parent amount: {parent.amount:,.0f}")
            print(f"    Difference: {parent.amount - (children.total_amt or 0):,.0f}")
    
    print("\n" + "=" * 80)
    print("KESIMPULAN MASALAH BALANCE SHEET")
    print("=" * 80)
    print("""
MASALAH DITEMUKAN:

1. Total Assets = Rp 0 (tidak ada aset sama sekali!)
2. Total Equity = Rp -108,000,000 (hanya ada Laba/Rugi atau Laba Ditahan)
3. Tidak ada transaksi yang masuk ke akun Assets (kode 1xxx)

PENYEBAB:
- Transaksi yang ada hanya masuk ke kode 5xxx (Beban)
- Tidak ada transaksi balancing yang masuk ke Assets (Kas/Bank) atau Liabilities (Utang)
- Dalam akuntansi, setiap beban harus ada lawannya (Kas berkurang atau Utang bertambah)

SOLUSI:
- Pastikan setiap transaksi beban memiliki pasangan di akun Assets atau Liabilities
- Contoh: Beban 108.000.000 harusnya:
  * Debit: 5xxx (Beban) 108.000.000
  * Kredit: 1xxx (Kas/Bank) 108.000.000
  ATAU
  * Kredit: 2xxx (Utang) 108.000.000

Dengan demikian:
  Assets = 108.000.000 (Kas berkurang) atau Liabilities = 108.000.000 (Utang bertambah)
  Equity = -108.000.000 (Laba rugi)
  Assets = Liabilities + Equity ✓ BALANCE
""")
