from sqlalchemy import create_engine, text
import pymysql

engine = create_engine('mysql+pymysql://root:root@127.0.0.1:3306/bank_converter')
with engine.connect() as conn:
    result = conn.execute(text("DESCRIBE marks;"))
    for row in result:
        print(row)
