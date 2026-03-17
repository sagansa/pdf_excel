#!/usr/bin/env python3
from sqlalchemy import text
from backend.db.session import get_db_engine

engine, _ = get_db_engine()

print("=" * 100)
print("COMPARISON: PNBP EXPENSE 2024 vs 2025")
print("=" * 100)

with engine.connect() as conn:
    # Check PNBP mark for both years
    result = conn.execute(text('''
        SELECT 
            YEAR(t.txn_date) as year,
            m.id as mark_id,
            m.personal_use,
            m.internal_report,
            m.is_coretax,
            COUNT(DISTINCT t.id) as txn_count,
            SUM(t.amount) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        WHERE (LOWER(m.personal_use) LIKE '%pnbp%' OR LOWER(m.internal_report) LIKE '%pnbp%')
          AND YEAR(t.txn_date) IN (2024, 2025)
        GROUP BY YEAR(t.txn_date), m.id, m.personal_use, m.internal_report, m.is_coretax
        ORDER BY year DESC
    '''))
    
    print("\n1. PNBP MARK TRANSACTIONS:")
    print("-" * 100)
    for row in result:
        year = row._mapping['year']
        mark_name = row._mapping['personal_use'] or row._mapping['internal_report']
        count = row._mapping['txn_count']
        amount = row._mapping['total_amount'] or 0
        is_coretax = row._mapping['is_coretax']
        print(f"Year {year}: Mark='{mark_name}', Count={count}, Amount={amount:,.0f}, is_coretax={is_coretax}")
    
    # Check COA mappings for PNBP mark
    print("\n2. PNBP MARK - COA MAPPINGS:")
    print("-" * 100)
    result2 = conn.execute(text('''
        SELECT 
            m.personal_use,
            mcm.report_type,
            coa.code,
            coa.name as coa_name,
            coa.category,
            mcm.mapping_type
        FROM marks m
        INNER JOIN mark_coa_mapping mcm ON mcm.mark_id = m.id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE LOWER(m.personal_use) LIKE '%pnbp%'
        ORDER BY mcm.report_type, coa.code
    '''))
    
    for row in result2:
        mark = row._mapping['personal_use']
        rtype = row._mapping['report_type']
        code = row._mapping['code']
        name = row._mapping['coa_name']
        category = row._mapping['category']
        mtype = row._mapping['mapping_type']
        print(f"  Mark='{mark}', Type={rtype}, COA={code} ({name}), Category={category}, Side={mtype}")
    
    # Check actual expense transactions by year
    print("\n3. PNBP EXPENSE TRANSACTIONS (COA 5xxx) BY YEAR:")
    print("-" * 100)
    result3 = conn.execute(text('''
        SELECT 
            YEAR(t.txn_date) as year,
            coa.code,
            coa.name,
            COUNT(DISTINCT t.id) as txn_count,
            SUM(t.amount) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON mcm.mark_id = m.id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE (LOWER(m.personal_use) LIKE '%pnbp%' OR LOWER(m.internal_report) LIKE '%pnbp%')
          AND coa.category = 'EXPENSE'
          AND YEAR(t.txn_date) IN (2024, 2025)
        GROUP BY YEAR(t.txn_date), coa.code, coa.name
        ORDER BY year DESC
    '''))
    
    for row in result3:
        year = row._mapping['year']
        code = row._mapping['code']
        name = row._mapping['name']
        count = row._mapping['txn_count']
        amount = row._mapping['total_amount'] or 0
        print(f"Year {year}: COA={code} ({name}), Count={count}, Amount={amount:,.0f}")
    
    # Check if there are differences in mark_coa_mapping between years
    print("\n4. CHECK: Are there transactions in 2025 without proper mapping?")
    print("-" * 100)
    
    for year in [2024, 2025]:
        result4 = conn.execute(text(f'''
            SELECT 
                COUNT(DISTINCT t.id) as total_txns,
                COUNT(DISTINCT CASE WHEN mcm.id IS NOT NULL THEN t.id END) as with_mapping,
                COUNT(DISTINCT CASE WHEN mcm.id IS NULL THEN t.id END) as without_mapping
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            LEFT JOIN mark_coa_mapping mcm ON mcm.mark_id = m.id
            WHERE (LOWER(m.personal_use) LIKE '%pnbp%' OR LOWER(m.internal_report) LIKE '%pnbp%')
              AND YEAR(t.txn_date) = {year}
        '''))
        
        row = result4.fetchone()
        total = row._mapping['total_txns']
        with_map = row._mapping['with_mapping']
        without = row._mapping['without_mapping']
        print(f"Year {year}: Total={total}, With Mapping={with_map}, Without Mapping={without}")
    
    # Test actual API query for CoreTax 2024 vs 2025
    print("\n5. ACTUAL CORETAX INCOME STATEMENT RESULTS:")
    print("-" * 100)
    
    from backend.services.reporting.report_sql_fragments import (
        _mark_coa_join_clause, 
        _split_parent_exclusion_clause, 
        _coretax_filter_clause
    )
    
    for year in [2024, 2025]:
        mark_coa_join = _mark_coa_join_clause(conn, 'coretax', mark_ref='m.id', mapping_alias='mcm', join_type='INNER')
        split_exclusion = _split_parent_exclusion_clause(conn, 't')
        coretax_clause = _coretax_filter_clause(conn, 'coretax', 'm')
        
        query = f'''
            SELECT
                coa.code,
                coa.name,
                coa.category,
                SUM(
                    CASE
                        WHEN UPPER(COALESCE(mcm.mapping_type, '')) = 'DEBIT' THEN t.amount
                        WHEN UPPER(COALESCE(mcm.mapping_type, '')) = 'CREDIT' THEN -t.amount
                        WHEN t.db_cr = 'DB' THEN t.amount
                        WHEN t.db_cr = 'CR' THEN -t.amount
                        ELSE 0
                    END
                ) as signed_amount
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            {mark_coa_join}
            INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            WHERE YEAR(t.txn_date) = {year}
                AND coa.category IN ('REVENUE', 'EXPENSE')
                {split_exclusion}
                {coretax_clause}
            GROUP BY coa.id, coa.code, coa.name, coa.category
            ORDER BY coa.code
        '''
        
        result5 = conn.execute(text(query))
        
        print(f"\nCoreTax {year} - Expense/Revenue from PNBP:")
        pnbp_found = False
        for row in result5:
            code = row._mapping['code']
            name = row._mapping['name']
            category = row._mapping['category']
            amount = row._mapping['signed_amount'] or 0
            
            if code == '5003' or 'PNBP' in name.upper():
                print(f"  {code} ({category}): {name} = {amount:,.0f}")
                pnbp_found = True
        
        if not pnbp_found:
            print(f"  No PNBP expense found in CoreTax {year}")
