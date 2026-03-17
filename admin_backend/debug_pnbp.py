#!/usr/bin/env python3
from sqlalchemy import text
from backend.db.session import get_db_engine

engine, _ = get_db_engine()

print("=" * 100)
print("DEBUG: PNBP MARK MAPPINGS AND TRANSACTIONS")
print("=" * 100)

with engine.connect() as conn:
    # Check mark_coa_mapping for PNBP
    print("\n1. PNBP MARK COA MAPPINGS:")
    print("-" * 100)
    result = conn.execute(text('''
        SELECT 
            m.id as mark_id,
            m.personal_use,
            mcm.id as mapping_id,
            mcm.report_type,
            coa.code,
            coa.name as coa_name
        FROM marks m
        INNER JOIN mark_coa_mapping mcm ON mcm.mark_id = m.id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE LOWER(m.personal_use) LIKE '%pnbp%'
        ORDER BY mcm.report_type, coa.code
    '''))
    
    for row in result:
        mark_id = str(row._mapping['mark_id'])[:8]
        mark_name = row._mapping['personal_use']
        mapping_id = str(row._mapping['mapping_id'])[:8]
        rtype = row._mapping['report_type']
        code = row._mapping['code']
        name = row._mapping['coa_name']
        print(f"  Mark {mark_id} ({mark_name}): Mapping {mapping_id}, Type={rtype}, COA={code} ({name})")
    
    # Check transactions with their mappings
    print("\n2. PNBP TRANSACTIONS WITH MAPPINGS (2025):")
    print("-" * 100)
    result = conn.execute(text('''
        SELECT 
            t.id as txn_id,
            t.parent_id,
            t.mark_id,
            t.amount,
            t.db_cr,
            m.id as mark_id,
            m.personal_use,
            mcm.report_type,
            coa.code,
            coa.category
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON mcm.mark_id = m.id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE YEAR(t.txn_date) = 2025
          AND LOWER(m.personal_use) LIKE '%pnbp%'
        ORDER BY mcm.report_type, t.txn_date
    '''))
    
    coretax_count = 0
    coretax_amount = 0
    real_count = 0
    real_amount = 0
    
    for row in result:
        txn_id = str(row._mapping['txn_id'])[:8]
        parent_id = str(row._mapping['parent_id'])[:8] if row._mapping['parent_id'] else 'NULL'
        mark_id = str(row._mapping['mark_id'])[:8]
        amount = row._mapping['amount'] or 0
        db_cr = row._mapping['db_cr']
        mark_name = row._mapping['personal_use']
        rtype = row._mapping['report_type']
        code = row._mapping['code']
        category = row._mapping['category']
        
        is_child = 'CHILD' if row._mapping['parent_id'] else 'PARENT'
        
        if rtype == 'coretax':
            coretax_count += 1
            coretax_amount += amount
        elif rtype == 'real':
            real_count += 1
            real_amount += amount
        
        print(f"  {txn_id} ({is_child:5}): mark={mark_id}, {db_cr}, {amount:>,.0f}, Type={rtype}, COA={code} ({category})")
    
    print(f"\n  Summary:")
    print(f"    REAL: count={real_count}, amount={real_amount:,.0f}")
    print(f"    CORETAX: count={coretax_count}, amount={coretax_amount:,.0f}")
    
    # Check the marks summary query logic
    print("\n3. DEBUG MARKS SUMMARY QUERY LOGIC:")
    print("-" * 100)
    
    # Simulate the query without split exclusion
    result = conn.execute(text('''
        SELECT 
            m.id as mark_id,
            m.personal_use,
            COUNT(t.id) as txn_count,
            SUM(t.amount) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON mcm.mark_id = m.id
        WHERE YEAR(t.txn_date) = 2025
          AND LOWER(m.personal_use) LIKE '%pnbp%'
          AND mcm.report_type = 'coretax'
        GROUP BY m.id, m.personal_use
    '''))
    
    for row in result:
        mark_id = str(row._mapping['mark_id'])[:8]
        mark_name = row._mapping['personal_use']
        count = row._mapping['txn_count']
        amount = row._mapping['total_amount'] or 0
        print(f"  WITHOUT split exclusion: Mark={mark_name}, Count={count}, Amount={amount:,.0f}")
    
    # With split exclusion
    result2 = conn.execute(text('''
        SELECT 
            m.id as mark_id,
            m.personal_use,
            COUNT(t.id) as txn_count,
            SUM(t.amount) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON mcm.mark_id = m.id
        WHERE YEAR(t.txn_date) = 2025
          AND LOWER(m.personal_use) LIKE '%pnbp%'
          AND mcm.report_type = 'coretax'
          AND NOT EXISTS (
              SELECT 1 FROM transactions t_child 
              WHERE t_child.parent_id = t.id 
              AND t_child.mark_id IS NOT NULL
          )
        GROUP BY m.id, m.personal_use
    '''))
    
    for row in result2:
        mark_id = str(row._mapping['mark_id'])[:8]
        mark_name = row._mapping['personal_use']
        count = row._mapping['txn_count']
        amount = row._mapping['total_amount'] or 0
        print(f"  WITH split exclusion: Mark={mark_name}, Count={count}, Amount={amount:,.0f}")
