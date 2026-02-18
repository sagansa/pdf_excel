import pymysql
import json
from datetime import datetime, date
from decimal import Decimal

# Connect to database
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='root',
    database='bank_converter',
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with conn.cursor() as cursor:
        # Check what the API would return for manual amortization items
        cursor.execute("""
            SELECT 
                ai.id,
                ai.company_id,
                ai.year,
                ai.coa_id,
                coa.code as coa_code,
                coa.name as coa_name,
                ai.description,
                ai.amount,
                ai.notes,
                ai.is_manual,
                ai.created_at,
                ai.updated_at,
                ai.amortization_date,
                ai.asset_group_id,
                ai.use_half_rate
            FROM amortization_items ai
            INNER JOIN chart_of_accounts coa ON ai.coa_id = coa.id
            WHERE ai.year = 2025
            AND (ai.asset_group_id IS NULL OR ai.asset_group_id = '')
            ORDER BY ai.amortization_date DESC, ai.created_at DESC
            LIMIT 5
        """)
        items = cursor.fetchall()
        
        print("Raw Database Results:")
        print("=" * 80)
        for item in items:
            print(f"\nID: {item['id']}")
            print(f"Description: {item['description']}")
            print(f"Amount: {item['amount']}")
            print(f"Amortization Date (raw): {item['amortization_date']} (type: {type(item['amortization_date'])})")
            print(f"Asset Group ID: {item['asset_group_id']}")
            print(f"Use Half Rate: {item['use_half_rate']}")
            print(f"Created At: {item['created_at']}")
            
        print("\n" + "=" * 80)
        print("\nFormatted for API Response (simulating server.py logic):")
        print("=" * 80)
        
        formatted_items = []
        for row in items:
            d = dict(row)
            # Convert Decimals to floats
            for key, value in d.items():
                if isinstance(value, Decimal):
                    d[key] = float(value)
                elif isinstance(value, (datetime, date)) and key == 'amortization_date':
                    d[key] = value.strftime('%Y-%m-%d')
                elif isinstance(value, (datetime, date)):
                    try:
                        d[key] = value.strftime('%Y-%m-%d')
                    except: 
                        pass
            formatted_items.append(d)
        
        print(json.dumps(formatted_items, indent=2, default=str))
        
        # Check asset groups
        print("\n" + "=" * 80)
        print("Asset Groups:")
        print("=" * 80)
        cursor.execute("SELECT id, group_name, group_number, asset_type, tarif_rate FROM amortization_asset_groups LIMIT 10")
        groups = cursor.fetchall()
        print(json.dumps(groups, indent=2, default=str))
        
finally:
    conn.close()
