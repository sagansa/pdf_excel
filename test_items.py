from backend.db.session import get_db_engine
from sqlalchemy import text
import pprint

engine, _ = get_db_engine()
with engine.connect() as conn:
    print("\n--- Amortization Items with Asset Types ---")
    items = conn.execute(text("""
        SELECT ai.description, ai.amount, ag.group_name, ag.asset_type
        FROM amortization_items ai
        JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
    """)).fetchall()
    for i in items:
        print(i)
