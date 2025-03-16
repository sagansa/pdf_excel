import pdfplumber
import pandas as pd
import re
import os

# Month abbreviation to number mapping
MONTH_MAP = {
    'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
    'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
    'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
}

def convert_date_format(date_str):
    """Convert date from DD-MMM format to DD/MM format."""
    try:
        if not date_str or '-' not in date_str:
            return date_str
        day, month = date_str.split('-')
        month = month.upper()
        if month in MONTH_MAP:
            return f"{day.zfill(2)}/{MONTH_MAP[month]}"
        return date_str
    except Exception:
        return date_str

def parse_statement(pdf_path):
    if not os.path.exists(pdf_path):
        raise ValueError("PDF file not found")
        
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")
        
    transactions = []
    current_transaction = None
    header_found = False
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                raise ValueError("PDF file is empty or corrupted. Please ensure the file is a valid BCA credit card statement")
            
            # Additional validation for PDF integrity
            try:
                # Try to access PDF metadata to verify basic PDF structure
                _ = pdf.metadata
                # Verify that pages are accessible and contain content
                for page in pdf.pages:
                    if not hasattr(page, 'extract_words'):
                        raise ValueError("PDF file appears to be corrupted. Unable to extract content from pages.")
            except Exception as e:
                raise ValueError(f"PDF file validation failed. The file may be corrupted: {str(e)}")

            for page in pdf.pages:
                # Extract text with position information
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3
                )
                
                # Add footer markers
                footer_markers = [
                    'TAGIHAN SEBELUMNYA'
                ]
                
                # Group words by y-position (rows)
                rows = {}
                skip_until_next_page = False
                for word in words:
                    # Skip if line contains any footer markers or if skipping until next page
                    line_text = word['text'].upper()  # Convert to uppercase for better matching
                    if any(marker.upper() in line_text for marker in footer_markers):
                        skip_until_next_page = True
                        continue
                    
                    # Skip processing if we're in skip mode
                    if skip_until_next_page:
                        continue
                        
                    y = round(word['top'])
                    if y not in rows:
                        rows[y] = []
                    rows[y].append(word)
                
                # Sort rows by y-position
                sorted_rows = sorted(rows.items())
                
                for y, row_words in sorted_rows:
                    # Sort words in row by x-position
                    row_words.sort(key=lambda w: w['x0'])
                    
                    # Process each word based on x-position
                    transaction_date = ''
                    posting_date = ''
                    transaction_details = []
                    amount = ''
                    db_cr = 'DB'  # Default to DB
                    
                    for word in row_words:
                        text = word['text']
                        x = word['x0']
                        
                        # Transaction date (0 < x < 100)
                        if 0 < x < 125:
                            # Check for both DD/MM and DD-MMM formats
                            if re.match(r'\d{2}/\d{2}', text) or re.match(r'\d{2}-[A-Za-z]{3}', text):
                                transaction_date = convert_date_format(text) if '-' in text else text
                        
                        # Posting date (100 < x < 220)
                        elif 125 < x < 190:
                            if re.match(r'\d{2}/\d{2}', text) or re.match(r'\d{2}-[A-Za-z]{3}', text):
                                posting_date = convert_date_format(text) if '-' in text else text
                        
                        # Transaction details (220 < x < 500)
                        elif 190 < x < 480:
                            transaction_details.append(text)
                        
                        # Amount (500 < x < 525)
                        elif 480 < x < 525:
                            amount = text.strip()
                        
                        # DB/CR indicator (>= 525)
                        elif x >= 525:
                            if text.strip().upper() == 'CR':
                                db_cr = 'CR'
                    
                    # If we found a transaction date, create a new transaction
                    if transaction_date:
                        if current_transaction:
                            transactions.append(current_transaction)
                        
                        current_transaction = {
                            'transaction_date': transaction_date,
                            'posting_date': posting_date,
                            'transaction_details': ' '.join(transaction_details),
                            'amount': amount,
                            'db_cr': db_cr
                        }
                    # If no date found and we have a current transaction, append details
                    elif current_transaction and transaction_details:
                        current_details = current_transaction['transaction_details']
                        new_details = ' '.join(transaction_details)
                        current_transaction['transaction_details'] = f"{current_details} {new_details}".strip()
                        
                        # Update amount if present in the continuation line
                        if amount:
                            current_transaction['amount'] = amount
                
                # Add the last transaction if exists
                if current_transaction:
                    transactions.append(current_transaction)
                    current_transaction = None
                    
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    return pd.DataFrame(transactions) if transactions else pd.DataFrame(
        columns=['transaction_date', 'posting_date', 'transaction_details', 'amount', 'db_cr']
    )