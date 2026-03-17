#!/usr/bin/env python3
from sqlalchemy import text
from backend.db.session import get_db_engine
from backend.routes.reporting.report_queries import build_marks_summary_query
from backend.routes.accounting_utils import serialize_result_rows

engine, _ = get_db_engine()

print("=" * 100)
print("TEST: CoreTax Filter with is_coretax flag")
print("=" * 100)

with engine.connect() as conn:
    # Check which marks have is_coretax=1
    print("\n1. Marks with is_coretax=1:")
    result = conn.execute(text('''
        SELECT id, personal_use, is_coretax 
        FROM marks 
        WHERE is_coretax = 1
    '''))
    
    coretax_marks = []
    for row in result:
        mark_id = str(row._mapping['id'])[:8]
        name = row._mapping['personal_use'] or 'N/A'
        print(f"  {mark_id}: {name}")
        coretax_marks.append(row._mapping['id'])
    
    if not coretax_marks:
        print("  (No marks with is_coretax=1)")
    
    # Test CoreTax query
    print("\n2. CoreTax Marks Summary 2025:")
    query = build_marks_summary_query('coretax')
    result = conn.execute(query, {
        'start_date': '2025-01-01',
        'end_date': '2025-12-31',
        'company_id': None
    })
    
    rows = serialize_result_rows(result)
    print(f"  Total marks returned: {len(rows)}")
    
    for data in rows:
        mark_name = data['mark_name'] or 'Unnamed Mark'
        credit = data['total_credit'] or 0
        debit = data['total_debit'] or 0
        count = data['transaction_count']
        print(f"  - {mark_name}: Credit={credit:,.0f}, Debit={debit:,.0f}, Count={count}")
    
    # Test Real query for comparison
    print("\n3. Real Marks Summary 2025 (first 10):")
    query = build_marks_summary_query('real')
    result = conn.execute(query, {
        'start_date': '2025-01-01',
        'end_date': '2025-12-31',
        'company_id': None
    })
    
    rows = serialize_result_rows(result)
    print(f"  Total marks returned: {len(rows)}")
    
    for i, data in enumerate(rows[:10]):
        mark_name = data['mark_name'] or 'Unnamed Mark'
        credit = data['total_credit'] or 0
        debit = data['total_debit'] or 0
        count = data['transaction_count']
        print(f"  - {mark_name}: Credit={credit:,.0f}, Debit={debit:,.0f}, Count={count}")
    
    if len(rows) > 10:
        print(f"  ... and {len(rows) - 10} more marks")
