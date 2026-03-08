from backend.db.session import get_db_engine
from sqlalchemy import text

engine, _ = get_db_engine()
with engine.connect() as conn:
    print("--- Asset COAs ---")
    rows = conn.execute(text("SELECT code, name, subcategory FROM chart_of_accounts WHERE code LIKE '15%' OR code LIKE '16%' ORDER BY code")).fetchall()
    for row in rows:
        print(row)
