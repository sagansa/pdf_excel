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

def test():
    engine, error = get_sagansa_engine()
    with engine.connect() as conn:
        cid = 1
        res = fetch_balance_sheet_data(conn, '2025-12-31', company_id=cid, report_type='real')
        assets = res['assets']['current'] + res['assets']['non_current']
        print(f"Total Assets count: {len(assets)}")
        for a in assets:
            print(f"ASSET {a.get('code')}: {a.get('amount')} ({a.get('name')})")

if __name__ == "__main__":
    test()
