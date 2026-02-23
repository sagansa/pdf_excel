import sys
from bank_parsers import mandiri_email
from pdf_unlock import unlock_pdf

pdf_path = '/Users/gargar/Development/pdf_excel/contoh/MANDIRI_2024_01.pdf'
password = '15101981'

try:
    unlocked_path = unlock_pdf(pdf_path, password)
    print(f"Unlocked PDF to {unlocked_path}")
    df = mandiri_email.parse_statement(unlocked_path)
    print(df.head())
    print("Total rows:", len(df))
except Exception as e:
    print(f"Error: {e}")
