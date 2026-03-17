#!/usr/bin/env python3
from sqlalchemy import text
from backend.db.session import get_db_engine

engine, _ = get_db_engine()

with engine.begin() as conn:
    # Update PNBP mark to is_coretax=1
    result = conn.execute(text('''
        UPDATE marks 
        SET is_coretax = 1 
        WHERE LOWER(personal_use) LIKE '%pnbp%' OR LOWER(internal_report) LIKE '%pnbp%'
    '''))
    
    print(f'Updated {result.rowcount} mark(s) to is_coretax=1')
    
    # Verify
    result2 = conn.execute(text('''
        SELECT id, personal_use, internal_report, is_coretax
        FROM marks
        WHERE is_coretax = 1
    '''))
    
    print('\nMarks with is_coretax=1:')
    for row in result2:
        name = row._mapping['personal_use'] or row._mapping['internal_report']
        print(f'  - {name}')
