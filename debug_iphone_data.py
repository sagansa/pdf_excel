import os
from sqlalchemy import create_engine, text

# Database configuration (matching server.py defaults)
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', 'root') 
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306') 
DB_NAME = os.environ.get('DB_NAME', 'bank_converter')

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def inspect_data():
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            print(f"Connected to database: {DB_NAME}")
            
            # Search logic
            print("\nSearching for 'iPhone' in notes/amortization_notes...")
            query = text("""
                SELECT id, txn_date, amortization_start_date, description, notes, amortization_notes 
                FROM transactions 
                WHERE notes LIKE '%iPhone%' OR amortization_notes LIKE '%iPhone%'
            """)
            result = conn.execute(query)
            for row in result:
                print(f"ID: {row[0]}")
                print(f"Description: {row[3]}")
                print(f"Notes: {row[4]}")
                print(f"Amortization Notes: {row[5]}")
                print(f"Txn Date: {row[1]}")
                print(f"Amortization Start Date: {row[2]}")
                print("-" * 30)

            print("\nSearching for 'BLIBLI' in description...")
            query = text("""
                SELECT id, txn_date, amortization_start_date, description, notes, amortization_notes 
                FROM transactions 
                WHERE description LIKE '%BLIBLI%'
            """)
            result = conn.execute(query)
            for row in result:
                print(f"ID: {row[0]}")
                print(f"Description: {row[3]}")
                print(f"Notes: {row[4]}")
                print(f"Amortization Notes: {row[5]}")
                print(f"Txn Date: {row[1]}")
                print(f"Amortization Start Date: {row[2]}")
                print("-" * 30)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_data()
