from backend.db.session import get_db_engine
from sqlalchemy import text
import pandas as pd

engine, _ = get_db_engine()
with engine.connect() as conn:
    query = text("""
        SELECT t.id, t.txn_date, t.amount, t.description, t.source_file, coa.code
        FROM transactions t
        JOIN marks m ON t.mark_id = m.id
        JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE coa.code = '1530'
        LIMIT 5
    """)
    rows = conn.execute(query).fetchall()
    for r in rows:
        print(r)
