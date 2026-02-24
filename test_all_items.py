from backend.db.session import get_db_engine
from sqlalchemy import text

engine, _ = get_db_engine()
with engine.connect() as conn:
    print("\n--- All Amortization Items ---")
    items = conn.execute(text("""
        SELECT ai.description, ag.asset_type 
        FROM amortization_items ai
        JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
    """)).fetchall()
    for i in items:
        print(i)
