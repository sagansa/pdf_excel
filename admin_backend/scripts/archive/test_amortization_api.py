import sys
sys.path.append('backend')
from db.session import get_db_engine
from sqlalchemy import text
import json

def test_amortization_api():
    """Test the amortization API endpoint logic"""
    engine, _ = get_db_engine()
    
    with engine.connect() as conn:
        company_id = None
        year = 2025
        
        # First, find a company if none provided
        if not company_id:
            first_comp = conn.execute(text("SELECT id FROM companies LIMIT 1")).fetchone()
            if first_comp:
                company_id = first_comp[0]
                print(f"Using company_id: {company_id}")
            else:
                print("No company found in database")
                return
        
        # Test settings
        print("\n=== AMORTIZATION SETTINGS ===")
        settings_query = text("""
            SELECT setting_name, setting_value, setting_type 
            FROM amortization_settings 
            WHERE company_id = :company_id OR company_id IS NULL
            ORDER BY company_id ASC
        """)
        settings_result = conn.execute(settings_query, {'company_id': company_id})
        
        use_mark_based = False
        asset_marks = []
        
        for row in settings_result:
            if row.setting_name == 'use_mark_based_amortization':
                use_mark_based = row.setting_value.lower() == 'true'
            elif row.setting_name == 'amortization_asset_marks':
                try:
                    asset_marks = json.loads(row.setting_value)
                except:
                    asset_marks = []
        
        print(f"use_mark_based: {use_mark_based}")
        print(f"asset_marks: {asset_marks}")
        
        # Test mark condition
        if use_mark_based and asset_marks:
            # Always include 5314, AND include amortizable transactions with matching marks
            mark_condition = "coa.code = '5314' OR (t.is_amortizable = TRUE AND m.personal_use IN :asset_marks) OR t.amortization_asset_group_id IS NOT NULL"
            query_params['asset_marks'] = asset_marks
        else:
            # Include all amortizable transactions
            mark_condition = "coa.code = '5314' OR t.is_amortizable = TRUE OR t.amortization_asset_group_id IS NOT NULL"
        
        print(f"\nMark condition: {mark_condition}")
        print(f"Query params: {query_params}")
        
        # Test the actual query
        print("\n=== TESTING TRANSACTION QUERY ===")
        txn_query = text(f"""
            SELECT 
                t.id as asset_id, t.txn_date, t.description,
                t.amount as acquisition_cost, t.amortization_asset_group_id as asset_group_id,
                t.amortization_start_date, t.use_half_rate, t.amortization_notes as notes,
                ag.group_name, ag.tarif_rate, ag.useful_life_years, ag.asset_type,
                m.personal_use as mark_name,
                coa.code as coa_code, coa.name as coa_name
            FROM transactions t
            INNER JOIN mark_coa_mapping mcm ON t.mark_id = mcm.mark_id
            INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            LEFT JOIN amortization_asset_groups ag ON t.amortization_asset_group_id = ag.id
            LEFT JOIN marks m ON t.mark_id = m.id
            WHERE ({mark_condition})
            AND (t.company_id = :company_id OR :company_id IS NULL)
            AND YEAR(t.txn_date) <= :year
            ORDER BY t.txn_date DESC
        """)
        
        txn_result = conn.execute(txn_query, query_params)
        transaction_count = 0
        
        for row in txn_result:
            d = dict(row._mapping)
            transaction_count += 1
            print(f"Transaction {transaction_count}: {d['coa_code']} - {d['description'][:50]} - {d['acquisition_cost']:,.0f}")
        
        print(f"\nTotal transactions found: {transaction_count}")
        
        # Test manual items
        print("\n=== TESTING MANUAL ITEMS ===")
        manual_query = text("""
            SELECT 
                ai.id, ai.company_id, ai.year, ai.coa_id,
                coa.code as coa_code, coa.name as coa_name,
                ai.description, ai.amount, ai.amortization_date,
                ai.asset_group_id, ai.use_half_rate, ai.notes, ai.is_manual,
                ai.created_at, ai.updated_at,
                ag.group_name, ag.tarif_rate, ag.useful_life_years, ag.asset_type
            FROM amortization_items ai
            LEFT JOIN chart_of_accounts coa ON ai.coa_id = coa.id
            LEFT JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
            WHERE ai.company_id = :company_id
            ORDER BY ai.amortization_date DESC, ai.created_at DESC
        """)
        
        manual_result = conn.execute(manual_query, {'company_id': company_id})
        manual_count = 0
        
        for row in manual_result:
            d = dict(row._mapping)
            manual_count += 1
            print(f"Manual {manual_count}: {d['coa_code']} - {d['description'][:50]} - {d['amount']:,.0f}")
        
        print(f"\nTotal manual items found: {manual_count}")
        print(f"\nTotal items expected in API: {transaction_count + manual_count}")

if __name__ == "__main__":
    test_amortization_api()
