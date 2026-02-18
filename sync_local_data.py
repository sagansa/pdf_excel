import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

def sync_data():
    # Database connection parameters
    db_user = os.getenv('DB_USER', 'root')
    db_pass = os.getenv('DB_PASS', 'root')
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = int(os.getenv('DB_PORT', 3306))
    
    # Databases
    pos_db = os.getenv('POS_DB_NAME', 'sagansa_2025')
    target_db = os.getenv('DB_NAME', 'bank_converter')
    
    try:
        # Connect to both databases
        conn_pos = pymysql.connect(host=db_host, user=db_user, password=db_pass, database=pos_db, port=db_port)
        conn_target = pymysql.connect(host=db_host, user=db_user, password=db_pass, database=target_db, port=db_port)
        
        print(f"Connected to {pos_db} and {target_db}")
        
        with conn_pos.cursor(pymysql.cursors.DictCursor) as cursor_pos, \
             conn_target.cursor() as cursor_target:
            
            # 1. Sync Companies (tenants -> companies)
            print("Syncing companies...")
            cursor_pos.execute("SELECT id, name FROM tenants")
            tenants = cursor_pos.fetchall()
            
            for tenant in tenants:
                cursor_target.execute(
                    "INSERT IGNORE INTO companies (id, name, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())",
                    (tenant['id'], tenant['name'])
                )
            
            # 2. Sync Stores (stores -> rental_stores)
            print("Syncing stores...")
            cursor_pos.execute("SELECT id, tenant_id, name FROM stores")
            stores = cursor_pos.fetchall()
            
            for store in stores:
                cursor_target.execute(
                    "INSERT IGNORE INTO rental_stores (id, company_id, store_name, store_code, created_at, updated_at) VALUES (%s, %s, %s, %s, NOW(), NOW())",
                    (store['id'], store['tenant_id'], store['name'], store['name'][:10]) # Use prefix of name as code
                )
                
            conn_target.commit()
            print(f"Successfully synced {len(tenants)} companies and {len(stores)} stores.")
            
    except Exception as e:
        print(f"Error during sync: {str(e)}")
    finally:
        if 'conn_pos' in locals():
            conn_pos.close()
        if 'conn_target' in locals():
            conn_target.close()

if __name__ == "__main__":
    sync_data()
