from backend.db.session import get_db_engine
from sqlalchemy import text
import pprint

engine, _ = get_db_engine()
with engine.connect() as conn:
    print("\n--- Transactions Mapped to Asset COAs ---")
    items = conn.execute(text("""
        SELECT t.description, coa.code, coa.name
        FROM transactions t
        JOIN marks m ON t.mark_id = m.id
        JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE coa.category = 'ASSET' AND t.amount > 0 AND coa.code LIKE '15%'
        LIMIT 20
    """)).fetchall()
    
    if len(items) == 0:
        print("No matches")
    else:
        for i in items:
            print(i)
