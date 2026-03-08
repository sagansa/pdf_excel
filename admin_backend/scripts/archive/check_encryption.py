
import pdfplumber
import sys

file_path = 'contoh/CC_BCA_2025_12.pdf'
try:
    with pdfplumber.open(file_path) as pdf:
        print(f"File {file_path} opened successfully.")
        print(f"Pages: {len(pdf.pages)}")
except Exception as e:
    print(f"Failed to open {file_path}: {e}")
