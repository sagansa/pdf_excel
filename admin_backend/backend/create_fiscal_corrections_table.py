from sqlalchemy import create_engine, text
import pymysql

engine = create_engine('mysql+pymysql://root:root@127.0.0.1:3306/bank_converter')
with engine.begin() as conn:
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS fiscal_corrections (
        id CHAR(36) PRIMARY KEY,
        company_id CHAR(36) NOT NULL,
        coa_id CHAR(36) NOT NULL,
        period_date DATE NOT NULL,
        correction_type ENUM('POSITIVE', 'NEGATIVE') NOT NULL,
        amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
        reason TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        FOREIGN KEY (coa_id) REFERENCES chart_of_accounts(id) ON DELETE CASCADE
    );
    """))
print("Table created successfully")
