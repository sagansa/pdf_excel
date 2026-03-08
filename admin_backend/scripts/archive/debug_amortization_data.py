import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
import json

# Database connection
DB_URL = "mysql+pymysql://root:root@127.0.0.1:3306/bank_converter"
engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        # Check what amortization items are in the database
        print("=== Checking amortization_items table ===")
        result = conn.execute(text("SELECT * FROM amortization_items WHERE year = 2025 OR year IS NULL"))
        for row in result:
            d = dict(row._mapping)
            print(json.dumps(d, indent=2, default=str))

        print("\n=== Checking transactions with amortization settings ===")
        result = conn.execute(text("""
            SELECT
                t.id, t.txn_date, t.description, t.amount,
                t.amortization_asset_group_id, t.amortization_start_date, t.use_half_rate,
                m.personal_use
            FROM transactions t
            LEFT JOIN marks m ON t.mark_id = m.id
            WHERE (t.amortization_asset_group_id IS NOT NULL OR t.is_amortizable = TRUE)
            AND YEAR(t.txn_date) <= 2025
            ORDER BY t.txn_date DESC
        """))
        for row in result:
            d = dict(row._mapping)
            print(json.dumps(d, indent=2, default=str))

        print("\n=== Checking amortization_assets table ===")
        result = conn.execute(text("""
            SELECT a.*, ag.group_name, ag.tarif_rate
            FROM amortization_assets a
            LEFT JOIN amortization_asset_groups ag ON a.asset_group_id = ag.id
            WHERE a.is_active = TRUE
        """))
        for row in result:
            d = dict(row._mapping)
            print(json.dumps(d, indent=2, default=str))

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
