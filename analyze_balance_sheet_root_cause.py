"""
Script untuk menganalisa kenapa Balance Sheet tidak balance
Fokus: Cek mapping marks ke COA dan struktur transaksi
"""
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///database.db")

with engine.connect() as conn:
    company_id = "demo-company"
    
    print("=" * 80)
    print("ANALISA BALANCE SHEET TIDAK BALANCE")
    print("=" * 80)
    
    # 1. Lihat semua marks yang digunakan
    print("\n=== 1. MARKS YANG DIGUNAKAN ===")
    marks = conn.execute(text("""
        SELECT DISTINCT m.id, m.personal_use, m.internal_report, m.tax_report, m.is_asset
        FROM marks m
        INNER JOIN transactions t ON m.id = t.mark_id
        WHERE t.company_id = :company_id
    """), {'company_id': company_id}).fetchall()
    
    for mark in marks:
        print(f"  {mark.id}: {mark.personal_use} | Asset: {mark.is_asset}")
    
    # 2. Lihat COA mapping untuk marks
    print("\n=== 2. COA MAPPING (mark_coa_mappings) ===")
    try:
        mapping_exists = conn.execute(text("""
            SELECT name FROM sqlite_master WHERE type='table' AND name='mark_coa_mappings'
        """)).fetchone()
        
        if mapping_exists:
            mappings = conn.execute(text("""
                SELECT mcm.mark_id, mcm.report_type, mcm.coa_code, c.name as coa_name, c.type as coa_type
                FROM mark_coa_mappings mcm
                LEFT JOIN coa c ON mcm.coa_code = c.code
                WHERE mcm.mark_id IN :mark_ids
                ORDER BY mcm.mark_id, mcm.report_type
            """), {'mark_ids': tuple(m.id for m in marks)}).fetchall()
            
            for mapping in mappings:
                print(f"  {mapping.mark_id} | {mapping.report_type}: {mapping.coa_code} ({mapping.coa_name}) - Type: {mapping.coa_type}")
        else:
            print("  Tabel mark_coa_mappings tidak ada")
    except Exception as e:
        print(f"  Error: {e}")
    
    # 3. Lihat transaksi per mark
    print("\n=== 3. TRANSAKSI PER MARK ===")
    txns = conn.execute(text("""
        SELECT m.id as mark_id, m.personal_use, COUNT(*) as count, SUM(t.amount) as total
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        WHERE t.company_id = :company_id
        GROUP BY m.id, m.personal_use
        ORDER BY m.id
    """), {'company_id': company_id}).fetchall()
    
    for txn in txns:
        print(f"  {txn.mark_id} ({txn.personal_use}): {txn.count} transaksi, Total: Rp {txn.total:,.0f}")
    
    # 4. Cek apakah ada transaksi dengan db_cr = DR (Debit)
    print("\n=== 4. TRANSAKSI BERDASARKAN DB_CR ===")
    dbcr_summary = conn.execute(text("""
        SELECT db_cr, COUNT(*) as count, SUM(amount) as total
        FROM transactions
        WHERE company_id = :company_id
        GROUP BY db_cr
    """), {'company_id': company_id}).fetchall()
    
    for row in dbcr_summary:
        print(f"  {row.db_cr}: {row.count} transaksi, Total: Rp {row.total:,.0f}")
    
    # 5. Lihat COA yang ada
    print("\n=== 5. COA MASTER (sample) ===")
    coas = conn.execute(text("""
        SELECT code, name, type
        FROM coa
        WHERE type IN ('ASSET', 'LIABILITY', 'EQUITY', 'EXPENSE')
        ORDER BY code
        LIMIT 20
    """)).fetchall()
    
    for coa in coas:
        print(f"  {coa.code}: {coa.name} ({coa.type})")
    
    print("\n" + "=" * 80)
    print("KESIMPULAN MASALAH")
    print("=" * 80)
    print("""
MASALAH UTAMA:

1. Transaksi hanya memiliki SATU SIDES (CR saja)
   - Semua transaksi adalah Credit (CR)
   - Tidak ada transaksi Debit (DR) yang membalance
   
2. Dalam sistem double-entry, setiap transaksi harus balance:
   - DR: Beban (5xxx) 108.000.000
   - CR: Kas/Bank (1xxx) 108.000.000
   
3. Di sistem ini, transaksi hanya mencatat satu sisi (CR saja):
   - CR: Beban 108.000.000
   - Tidak ada DR yang tercatat!

4. Balance Sheet tidak balance karena:
   - Assets = Rp 0 (tidak ada pengurangan Kas)
   - Equity = -Rp 108.000.000 (Beban mengurangi laba)
   - Assets ≠ Liabilities + Equity
   - Selisih: Rp 108.000.000

SOLUSI:

Sistem ini sepertinya menggunakan pendekatan "single-entry" untuk transaksi
operasional, di mana:
- Hanya mencatat sisi beban (CR)
- Sisi Kas/Bank (DR) tidak dicatat secara eksplisit

Untuk membuat Balance Sheet balance, perlu:
1. Mencatat transaksi Kas Masuk/Keluar secara terpisah
2. ATAU menambahkan transaksi balancing otomatis
3. ATAU menggunakan sistem double-entry lengkap dengan DR/CR

Contoh transaksi yang seharusnya:
- DR: Kas Awal 108.000.000 (modal awal)
- CR: Beban Listrik 1.500.000
- CR: Beban Sewa 10.000.000
- CR: Beban Lainnya ...

Dengan demikian:
- Assets (Kas) = 108.000.000 - 108.000.000 = 0
- Equity (Laba/Rugi) = -108.000.000
- Tapi perlu Modal Awal di Equity untuk balance!
""")
