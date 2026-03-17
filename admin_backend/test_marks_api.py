#!/usr/bin/env python3
from sqlalchemy import text
from backend.db.session import get_db_engine
from backend.routes.reporting.report_queries import build_marks_summary_query

engine, _ = get_db_engine()

print("=" * 100)
print("TEST MARKS SUMMARY API - PNBP 2024 vs 2025")
print("=" * 100)

with engine.connect() as conn:
    # Test with 'real' report type
    print("\n1. MARKS SUMMARY - REAL (2024):")
    print("-" * 100)
    query_real_2024 = build_marks_summary_query('real')
    result = conn.execute(query_real_2024, {
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
        'company_id': None
    })
    
    for row in result:
        mark_id = str(row._mapping['mark_id'])[:8]
        mark_name = row._mapping['mark_name'] or 'N/A'
        debit = row._mapping['total_debit'] or 0
        credit = row._mapping['total_credit'] or 0
        count = row._mapping['transaction_count']
        
        if 'pnbp' in mark_name.lower():
            print(f"  Mark: {mark_name}, Debit={debit:,.0f}, Credit={credit:,.0f}, Count={count}")
    
    print("\n2. MARKS SUMMARY - REAL (2025):")
    print("-" * 100)
    query_real_2025 = build_marks_summary_query('real')
    result = conn.execute(query_real_2025, {
        'start_date': '2025-01-01',
        'end_date': '2025-12-31',
        'company_id': None
    })
    
    for row in result:
        mark_id = str(row._mapping['mark_id'])[:8]
        mark_name = row._mapping['mark_name'] or 'N/A'
        debit = row._mapping['total_debit'] or 0
        credit = row._mapping['total_credit'] or 0
        count = row._mapping['transaction_count']
        
        if 'pnbp' in mark_name.lower():
            print(f"  Mark: {mark_name}, Debit={debit:,.0f}, Credit={credit:,.0f}, Count={count}")
    
    print("\n3. MARKS SUMMARY - CORETAX (2024):")
    print("-" * 100)
    query_coretax_2024 = build_marks_summary_query('coretax')
    result = conn.execute(query_coretax_2024, {
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
        'company_id': None
    })
    
    for row in result:
        mark_id = str(row._mapping['mark_id'])[:8]
        mark_name = row._mapping['mark_name'] or 'N/A'
        debit = row._mapping['total_debit'] or 0
        credit = row._mapping['total_credit'] or 0
        count = row._mapping['transaction_count']
        
        if 'pnbp' in mark_name.lower():
            print(f"  Mark: {mark_name}, Debit={debit:,.0f}, Credit={credit:,.0f}, Count={count}")
    
    print("\n4. MARKS SUMMARY - CORETAX (2025):")
    print("-" * 100)
    query_coretax_2025 = build_marks_summary_query('coretax')
    result = conn.execute(query_coretax_2025, {
        'start_date': '2025-01-01',
        'end_date': '2025-12-31',
        'company_id': None
    })
    
    for row in result:
        mark_id = str(row._mapping['mark_id'])[:8]
        mark_name = row._mapping['mark_name'] or 'N/A'
        debit = row._mapping['total_debit'] or 0
        credit = row._mapping['total_credit'] or 0
        count = row._mapping['transaction_count']
        
        if 'pnbp' in mark_name.lower():
            print(f"  Mark: {mark_name}, Debit={debit:,.0f}, Credit={credit:,.0f}, Count={count}")
    
    print("\n5. DEBUG: Check split transactions for PNBP:")
    print("-" * 100)
    
    for year in [2024, 2025]:
        result = conn.execute(text(f'''
            SELECT 
                t.id,
                t.parent_id,
                t.mark_id,
                t.amount,
                t.db_cr,
                m.personal_use
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            WHERE YEAR(t.txn_date) = {year}
              AND (LOWER(m.personal_use) LIKE '%pnbp%')
            ORDER BY t.txn_date
        '''))
        
        print(f"\nYear {year} PNBP transactions:")
        for row in result:
            txn_id = str(row._mapping['id'])[:8]
            parent_id = str(row._mapping['parent_id'])[:8] if row._mapping['parent_id'] else 'NULL'
            mark_id = str(row._mapping['mark_id'])[:8]
            amount = row._mapping['amount'] or 0
            db_cr = row._mapping['db_cr']
            mark_name = row._mapping['personal_use'] or 'N/A'
            
            is_child = 'CHILD' if row._mapping['parent_id'] else 'PARENT/STANDALONE'
            print(f"  {txn_id} ({is_child:15}): parent={parent_id}, mark={mark_id}, {db_cr}, {amount:>,.0f}, mark='{mark_name}'")
