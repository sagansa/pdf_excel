from sqlalchemy import create_engine, inspect
import pymysql

engine = create_engine('mysql+pymysql://root:root@127.0.0.1:3306/bank_converter')
inspector = inspect(engine)
columns = inspector.get_columns('chart_of_accounts')
for col in columns:
    print(f"{col['name']}: {col['type']}")
