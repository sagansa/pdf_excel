from backend.db.session import get_db_engine
from sqlalchemy import text
import pprint

engine, _ = get_db_engine()
with engine.connect() as conn:
    print("--- Amortization Groups ---")
    groups = conn.execute(text("SELECT id, group_name, asset_type FROM amortization_asset_groups")).fetchall()
    for g in groups:
        print(g)

    print("\n--- Amortization Items ---")
    items = conn.execute(text("SELECT id, description, amount, asset_group_id FROM amortization_items LIMIT 5")).fetchall()
    for i in items:
        print(i)

    print("\n--- Amortization Assets ---")
    assets = conn.execute(text("SELECT id, asset_name, asset_group_id FROM amortization_assets LIMIT 5")).fetchall()
    for a in assets:
        print(a)
