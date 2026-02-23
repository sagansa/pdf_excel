import pandas as pd
from bank_parsers import mandiri_email
from pdf_unlock import unlock_pdf

pdf_path = '/Users/gargar/Development/pdf_excel/contoh/MANDIRI_2024_01.pdf'
password = '15101981'

try:
    unlocked_path = unlock_pdf(pdf_path, password)
    df = mandiri_email.parse_statement(unlocked_path)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', None)
    print(df[['txn_date', 'description', 'amount', 'db_cr', 'balance']].head(10))
    print(df[['txn_date', 'description', 'amount', 'db_cr', 'balance']].tail(5))
except Exception as e:
    print(f"Error: {e}")
