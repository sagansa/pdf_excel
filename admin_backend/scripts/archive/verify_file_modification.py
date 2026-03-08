import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
from datetime import datetime, date
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Database connection
DB_URL = "mysql+pymysql://root:root@127.0.0.1:3306/bank_converter"
engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        # Read the report_service.py file to check if the modification is there
        with open('/Users/gargar/Development/pdf_excel/backend/services/report_service.py', 'r') as f:
            content = f.read()

        if 'transaction_amort_total' in content:
            print("✅ The file contains 'transaction_amort_total'")
        else:
            print("❌ The file does NOT contain 'transaction_amort_total'")

        if 'total_5314_amort = calculated_amort_total + transaction_amort_total + manual_amort_total' in content:
            print("✅ The file has the correct formula")
        else:
            print("❌ The formula is different")

except Exception as e:
    print(f"Error: {e}")
