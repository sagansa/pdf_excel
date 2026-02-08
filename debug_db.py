from sqlalchemy import create_engine, text
import os

DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', 'root')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_NAME = os.environ.get('DB_NAME', 'bank_converter')

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

with engine.connect() as conn:
    print("--- MARKS ---")
    marks = conn.execute(text("SELECT id, personal_use FROM marks LIMIT 5")).fetchall()
    for m in marks:
        print(m)
    
    print("\n--- MAPPINGS ---")
    mappings = conn.execute(text("SELECT * FROM mark_coa_mapping LIMIT 5")).fetchall()
    for mp in mappings:
        print(mp)
    
    print("\n--- COA ---")
    coa = conn.execute(text("SELECT id, code, name FROM chart_of_accounts LIMIT 5")).fetchall()
    for c in coa:
        print(c)
    
    print("\n--- JOINED MAPPINGS ---")
    query = text("""
        SELECT mcm.mark_id, mcm.mapping_type, coa.code, coa.name
        FROM mark_coa_mapping mcm
        JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
    """)
    joined = conn.execute(query).fetchall()
    for row in joined:
        print(row)
