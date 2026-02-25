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
            print("Dropping old tables if exists...")
            conn.execute(text("DROP TABLE IF EXISTS transaction_products"))
            conn.execute(text("DROP TABLE IF EXISTS products"))
            
            print("Creating products table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS products (
                    id CHAR(36) NOT NULL,
                    company_id CHAR(36),
                    code VARCHAR(50),
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(100),
                    default_currency VARCHAR(10) DEFAULT 'USD',
                    default_price DECIMAL(15,2) DEFAULT 0.00,
                    created_at DATETIME,
                    updated_at DATETIME,
                    PRIMARY KEY (id),
                    KEY idx_company (company_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """))

            print("Creating transaction_products table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS transaction_products (
                    id CHAR(36) NOT NULL,
                    transaction_id CHAR(36) NOT NULL,
                    product_id CHAR(36) NOT NULL,
                    quantity DECIMAL(15,2) DEFAULT 1.00,
                    foreign_currency VARCHAR(10) DEFAULT 'USD',
                    foreign_price DECIMAL(15,2) DEFAULT 0.00,
                    calculated_idr_hpp DECIMAL(15,2) DEFAULT 0.00,
                    created_at DATETIME,
                    updated_at DATETIME,
                    PRIMARY KEY (id),
                    KEY idx_transaction (transaction_id),
                    KEY idx_product (product_id),
                    CONSTRAINT fk_txn_prod_txn FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
                    CONSTRAINT fk_txn_prod_prod FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """))

            print("Migration successful.")
            return True
    except Exception as e:
        print("Migration failed:", e)
        return False

if __name__ == '__main__':
    migrate()
