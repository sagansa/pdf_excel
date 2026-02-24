import sys
import json
from decimal import Decimal

# Add path
sys.path.append('.')

from backend.db.session import get_sagansa_engine
from backend.services.report_service import fetch_balance_sheet_data
from sqlalchemy import text

def custom_encoder(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def test():
    engine, error = get_sagansa_engine()
    if error:
        print("DB error:", error)
        return

    with engine.connect() as conn:
        company_id = conn.execute(text("SELECT id FROM companies LIMIT 1")).scalar()
        res = fetch_balance_sheet_data(conn, '2025-12-31', company_id=company_id, report_type='real')
        
    print(json.dumps(res, default=custom_encoder, indent=2))

if __name__ == "__main__":
    test()
