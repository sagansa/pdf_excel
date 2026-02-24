import sys
sys.path.append('.')
from backend.db.session import get_sagansa_engine
from sqlalchemy import text

def test():
    engine, error = get_sagansa_engine()
    with engine.connect() as conn:
        res = conn.execute(text("SELECT count(*) FROM transactions"))
        print("Total transactions:", res.scalar())
        res = conn.execute(text("SELECT t.txn_date, t.amount, coa.code FROM transactions t JOIN marks m ON t.mark_id=m.id JOIN mark_coa_mapping mcm ON mcm.mark_id=m.id JOIN chart_of_accounts coa ON coa.id=mcm.coa_id WHERE coa.code='1600'"))
        print("\n1600 Trans:")
        for r in res:
            print(dict(r._mapping))

if __name__ == "__main__":
    test()
