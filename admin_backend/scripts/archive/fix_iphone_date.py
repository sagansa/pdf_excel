import os
from sqlalchemy import create_engine, text

# Database configuration
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', 'root') 
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306') 
DB_NAME = os.environ.get('DB_NAME', 'bank_converter')

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def fix_data():
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            print(f"Connected to database: {DB_NAME}")
            
            # The specific ID from debug output
            txn_id = 'dcb4d073-29bb-4b77-9fe0-90362734cb4f'
            
            print(f"fixing transaction {txn_id}...")
            query = text("UPDATE transactions SET amortization_start_date = NULL WHERE id = :id")
            result = conn.execute(query, {"id": txn_id})
            conn.commit()
            
            print(f"Rows affected: {result.rowcount}")
            print("Done.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_data()
