import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')

url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
engine = create_engine(url)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, batch_date, memo FROM hpp_batches ORDER BY created_at DESC LIMIT 5;"))
        for row in result:
            print(row)
except Exception as e:
    print(e)
