import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def update_coa():
    try:
        conn = pymysql.connect(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            port=int(os.getenv('DB_PORT', '3306')),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASS', 'root'),
            database=os.getenv('DB_NAME', 'bank_converter'),
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with conn.cursor() as cursor:
            # Update COA 5494
            query = "UPDATE chart_of_accounts SET fiscal_category = 'NON_DEDUCTIBLE_PERMANENT' WHERE code = '5494'"
            cursor.execute(query)
            conn.commit()
            
            # Verify
            cursor.execute("SELECT code, name, fiscal_category FROM chart_of_accounts WHERE code = '5494'")
            result = cursor.fetchone()
            print(f"Updated: {result}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_coa()
