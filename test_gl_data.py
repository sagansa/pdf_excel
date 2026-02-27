"""
Test script untuk cek General Ledger data
"""
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@127.0.0.1:3306/bank_converter')

with engine.connect() as conn:
    company_id = '8ab69d4a-e591-4f05-909e-25ff12352efb'
    
    # Cek satu transaksi dan COA mappings-nya
    print("=== CEK TRANSAKSI DAN COA MAPPINGS ===")
    result = conn.execute(text("""
        SELECT 
            t.id as txn_id,
            t.txn_date,
            t.description,
            t.amount,
            t.db_cr,
            m.personal_use as mark_name,
            coa.code as coa_code,
            coa.name as coa_name,
            mcm.mapping_type
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.company_id = :company_id
        ORDER BY t.txn_date
        LIMIT 10
    """), {'company_id': company_id}).fetchall()
    
    current_txn = None
    for row in result:
        if row.txn_id != current_txn:
            if current_txn:
                print()
            current_txn = row.txn_id
            print(f"\nTransaksi {row.txn_id}:")
            print(f"  Tanggal: {row.txn_date}")
            print(f"  Deskripsi: {row.description}")
            print(f"  Amount: {row.amount} ({row.db_cr})")
            print(f"  Mark: {row.mark_name}")
            print(f"  COA Mappings:")
        
        print(f"    - {row.coa_code} ({row.coa_name}) - {row.mapping_type}")
