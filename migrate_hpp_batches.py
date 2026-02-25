import sys
import os
sys.path.append('.')

from backend.db.session import get_db_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

def migrate():
    engine, error = get_db_engine()
    if error:
        print("Database connection error:", error)
        return False
        
    try:
        with engine.begin() as conn:
            print("Dropping old table if exists...")
            conn.execute(text("DROP TABLE IF EXISTS transaction_products"))
            
            print("Creating hpp_batches table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS hpp_batches (
                    id CHAR(36) PRIMARY KEY,
                    company_id CHAR(36) NOT NULL,
                    memo VARCHAR(255),
                    total_amount DECIMAL(20,2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """))

            print("Creating hpp_batch_transactions table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS hpp_batch_transactions (
                    batch_id CHAR(36) NOT NULL,
                    transaction_id CHAR(36) NOT NULL,
                    PRIMARY KEY (batch_id, transaction_id),
                    FOREIGN KEY (batch_id) REFERENCES hpp_batches(id) ON DELETE CASCADE,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """))

            print("Creating hpp_batch_products table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS hpp_batch_products (
                    id CHAR(36) PRIMARY KEY,
                    batch_id CHAR(36) NOT NULL,
                    product_id CHAR(36) NOT NULL,
                    quantity DECIMAL(15,4) NOT NULL DEFAULT 0.0000,
                    foreign_currency VARCHAR(10) NOT NULL DEFAULT 'USD',
                    foreign_price DECIMAL(20,2) NOT NULL DEFAULT 0.00,
                    calculated_total_idr DECIMAL(20,2) NOT NULL DEFAULT 0.00,
                    calculated_unit_idr_hpp DECIMAL(20,2) NOT NULL DEFAULT 0.00,
                    FOREIGN KEY (batch_id) REFERENCES hpp_batches(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """))

            print("Migration successful.")
            return True
            
    except Exception as e:
        print("Migration failed:", e)
        return False

if __name__ == '__main__':
    migrate()
