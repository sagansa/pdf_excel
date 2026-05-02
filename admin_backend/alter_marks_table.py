from sqlalchemy import create_engine, text
import pymysql

engine = create_engine('mysql+pymysql://root:root@127.0.0.1:3306/bank_converter')
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE marks ADD COLUMN fiscal_category VARCHAR(50) DEFAULT NULL;"))
print("Column added successfully")
