#!/usr/bin/env python3
"""
Simulate the exact API call from MarksReport.vue frontend
"""
from sqlalchemy import text
from backend.db.session import get_db_engine
from backend.routes.reporting.report_queries import build_marks_summary_query
from backend.routes.accounting_utils import serialize_result_rows

engine, _ = get_db_engine()

print("=" * 100)
print("SIMULATE FRONTEND API CALL - MarksReport.vue")
print("=" * 100)

# Simulate frontend filters
test_cases = [
    {
        'name': 'CoreTax 2025 (Full Year)',
        'start_date': '2025-01-01',
        'end_date': '2025-12-31',
        'company_id': None,
        'report_type': 'coretax'
    },
    {
        'name': 'Real 2025 (Full Year)',
        'start_date': '2025-01-01',
        'end_date': '2025-12-31',
        'company_id': None,
        'report_type': 'real'
    },
    {
        'name': 'CoreTax 2024 (Full Year)',
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
        'company_id': None,
        'report_type': 'coretax'
    },
]

with engine.connect() as conn:
    for tc in test_cases:
        print(f"\n{tc['name']}:")
        print("-" * 100)
        
        query = build_marks_summary_query(tc['report_type'])
        params = {
            'start_date': tc['start_date'],
            'end_date': tc['end_date'],
            'company_id': tc['company_id']
        }
        
        result = conn.execute(query, params)
        rows = serialize_result_rows(result)
        
        # Process like the API does
        marks = []
        total_debit_all = 0.0
        total_credit_all = 0.0
        
        for data in rows:
            total_debit = float(data['total_debit'] or 0)
            total_credit = float(data['total_credit'] or 0)
            total_debit_all += total_debit
            total_credit_all += total_credit
            
            mark_name = data['mark_name'] or 'Unnamed Mark'
            
            # Show PNBP or high-value marks
            if 'pnbp' in mark_name.lower() or total_credit > 10000:
                marks.append({
                    'mark_name': mark_name,
                    'total_debit': total_debit,
                    'total_credit': total_credit,
                    'net_amount': total_debit - total_credit,
                    'transaction_count': data['transaction_count']
                })
        
        # Print results
        if marks:
            print(f"  {'Mark Name':<40} {'Debit':>12} {'Credit':>12} {'Net':>12} {'Count':>8}")
            print(f"  {'-'*40} {'-'*12} {'-'*12} {'-'*12} {'-'*8}")
            for mark in marks:
                print(f"  {mark['mark_name']:<40} {mark['total_debit']:>12,.0f} {mark['total_credit']:>12,.0f} {mark['net_amount']:>12,.0f} {mark['transaction_count']:>8}")
        else:
            print(f"  No marks found")
        
        print(f"\n  TOTALS: Debit={total_debit_all:,.0f}, Credit={total_credit_all:,.0f}, Net={total_debit_all - total_credit_all:,.0f}")

print("\n" + "=" * 100)
print("CHECK: Is PNBP mark being filtered out?")
print("=" * 100)

with engine.connect() as conn:
    # Check if PNBP transactions exist in 2025
    result = conn.execute(text('''
        SELECT 
            m.id,
            m.personal_use,
            m.is_coretax,
            COUNT(DISTINCT t.id) as txn_count,
            SUM(t.amount) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        WHERE YEAR(t.txn_date) = 2025
          AND (LOWER(m.personal_use) LIKE '%pnbp%' OR LOWER(m.internal_report) LIKE '%pnbp%')
        GROUP BY m.id, m.personal_use, m.is_coretax
    '''))
    
    print("\nPNBP marks in 2025 database:")
    for row in result:
        mark_id = str(row._mapping['id'])[:8]
        mark_name = row._mapping['personal_use'] or 'N/A'
        is_coretax = row._mapping['is_coretax']
        count = row._mapping['txn_count']
        amount = row._mapping['total_amount'] or 0
        print(f"  Mark {mark_id} ({mark_name}): is_coretax={is_coretax}, Count={count}, Amount={amount:,.0f}")
    
    # Check split exclusion
    print("\nSplit exclusion check for PNBP 2025:")
    result2 = conn.execute(text('''
        SELECT 
            t.id as txn_id,
            t.parent_id,
            t.mark_id,
            t.amount,
            EXISTS(
                SELECT 1 FROM transactions t_child 
                WHERE t_child.parent_id = t.id 
                AND t_child.mark_id IS NOT NULL
            ) as has_children_with_mark
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        WHERE YEAR(t.txn_date) = 2025
          AND (LOWER(m.personal_use) LIKE '%pnbp%' OR LOWER(m.internal_report) LIKE '%pnbp%')
    '''))
    
    for row in result2:
        txn_id = str(row._mapping['txn_id'])[:8]
        parent_id = str(row._mapping['parent_id'])[:8] if row._mapping['parent_id'] else 'NULL'
        amount = row._mapping['amount'] or 0
        has_children = row._mapping['has_children_with_mark']
        status = 'EXCLUDED' if has_children else 'INCLUDED'
        print(f"  Txn {txn_id} (parent={parent_id}): {amount:>,.0f} -> {status}")
