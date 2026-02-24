import sys
import json
from decimal import Decimal
import os
from dotenv import load_dotenv

sys.path.append('.')
load_dotenv()

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
        print(f"Connected to {engine.url}")
        companies = [1, 2, None]
        for cid in companies:
            print(f"--- Company {cid} ---")
            res = fetch_balance_sheet_data(conn, '2025-12-31', company_id=cid, report_type='real')
            assets = res['assets']['current'] + res['assets']['non_current']
            for a in assets:
                if str(a.get('code')).startswith('16') or str(a.get('code')).startswith('15'):
                    print(f"ASSET {a.get('code')}: {a.get('amount')} ({a.get('name')})")
            print("is_balanced:", res['is_balanced'])

if __name__ == "__main__":
    test()
