import sys
import json
import os
from decimal import Decimal

sys.path.append('.')

from backend.db.session import get_sagansa_engine
from backend.services.report_service import fetch_balance_sheet_data
from sqlalchemy import text

def test():
    engine, error = get_sagansa_engine()
    print("Engine:", engine.url)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT id, name FROM companies"))
        companies = list(res)
        print("Companies:", companies)
        for c in companies:
            print(f"Fetching report for company {c.id}")
            report = fetch_balance_sheet_data(conn, '2025-12-31', company_id=c.id, report_type='real')
            print("Total assets:", report['total_assets'], "Balanced:", report['is_balanced'])
            assets = report['assets']['current'] + report['assets']['non_current']
            for a in assets:
                if str(a.get('code')).startswith('16') or str(a.get('code')).startswith('15'):
                    print(f"  ASSET {a.get('code')}: {a.get('amount')} ({a.get('name')})")

if __name__ == "__main__":
    test()
