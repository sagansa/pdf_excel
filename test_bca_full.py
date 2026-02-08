import os
import pandas as pd
from bank_parsers import bca_cc
from pdf_unlock import unlock_pdf

def test_full_parse():
    pdf_path = 'contoh/contoh_cc_bca.pdf'
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found")
        return

    try:
        print(f"Parsing {pdf_path}...")
        df = bca_cc.parse_statement(pdf_path, base_year=2025)
        
        print("\n--- Resulting DataFrame ---")
        print(df[['txn_date', 'description', 'amount', 'db_cr']])
        
        # Save to csv for easier inspection
        df.to_csv('test_bca_output.csv', index=False)
        print("\nFull output saved to test_bca_output.csv")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_full_parse()
