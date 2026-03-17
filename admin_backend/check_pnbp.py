#!/usr/bin/env python3
from sqlalchemy import text
from backend.db.session import get_db_engine

engine, _ = get_db_engine()

with engine.connect() as conn:
    # Check actual PNBP transactions
    result = conn.execute(text('''
        SELECT 
            t.id,
            t.txn_date,
            t.description,
            t.amount,
            t.db_cr,
            m.personal_use,
            m.internal_report
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        WHERE YEAR(t.txn_date) = 2025
          AND (
              LOWER(m.personal_use) LIKE '%pnbp%' 
              OR LOWER(m.internal_report) LIKE '%pnbp%'
          )
        ORDER BY t.txn_date
    '''))
    
    print('PNBP Transactions 2025 (from transactions table):')
    print('=' * 120)
    
    total = 0
    for row in result:
        date = str(row._mapping['txn_date'])
        desc = row._mapping['description'] or row._mapping['personal_use'] or row._mapping['internal_report']
        amount = row._mapping['amount'] or 0
        db_cr = row._mapping['db_cr']
        mark = row._mapping['personal_use'] or row._mapping['internal_report']
        total += amount
        
        print(f'Date: {date} | Amount: {amount:,.0f} | {db_cr} | Mark: {mark} | Desc: {desc}')
    
    print('-' * 120)
    print(f'Total PNBP transactions: {total:,.0f}')
