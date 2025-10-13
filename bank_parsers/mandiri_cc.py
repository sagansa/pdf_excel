import os
import re
from datetime import datetime
import pandas as pd
import pdfplumber

# Month abbreviation mapping for date conversion
MONTH_ABBR = {
    'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
    'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
    'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
}

def convert_date_format(date_str):
    """Convert date from DD-MMM-YY format to DD/MM/YY format."""
    try:
        if not date_str or '-' not in date_str:
            return date_str
            
        parts = date_str.split('-')
        if len(parts) < 2:
            return date_str
            
        # Ensure day is two digits
        day = parts[0].zfill(2)
        
        # Convert month to number
        month = MONTH_ABBR.get(parts[1].upper(), '00')
        
        # Handle year if present
        year = parts[2] if len(parts) > 2 else ''
        if year and len(year) == 2:
            # Assuming 20YY for simplicity
            year = f"20{year}"
        
        return f"{day}/{month}/{year}" if year else f"{day}/{month}"
    except Exception:
        return date_str

def parse_statement(pdf_path):
    if not os.path.exists(pdf_path):
        raise ValueError("PDF file not found")
        
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")
        
    transactions = []
    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    current_transaction = None
    header_found = False
    
    # Define header and footer markers
    header_markers_en = ['Transaction Date', 'Posting Date', 'Description', 'amount (IDR))']
    header_markers_id = ['Tanggal Transaksi', 'Tanggal Pembukuan', 'Keterangan', 'Jumlah']
    header_found = False
    footer_markers = []
    skip_markers = ['SUB-TOTAL', 'TAGIHAN BULAN LALU', 'Description', 'amount (IDR)', 'Keterangan', 'Jumlah']
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                raise ValueError("PDF file is empty or corrupted. Please ensure the file is a valid Mandiri credit card statement")
            
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
                
                # Group words by y-position (rows)
                rows = {}
                for word in words:
                    # Check for date pattern in the leftmost position (0 < x < 100)
                    if 0 < word['x0'] < 100:
                        text = word['text'].strip()
                        # Check for DD/MM or DD-MMM-YY format
                        if re.match(r'\d{1,2}[-/]\d{2}|\d{1,2}-[A-Za-z]{3}(-\d{2})?', text):
                            header_found = True
                            # Save current transaction before starting new section
                            if current_transaction:
                                current_transaction['created_at'] = conversion_timestamp
                                transactions.append(current_transaction)
                                current_transaction = None
                    
                    # Skip sections with specific markers
                    line_text = word['text'].upper()
                    if any(marker.upper() in line_text for marker in skip_markers):
                        if current_transaction:
                            current_transaction['created_at'] = conversion_timestamp
                            transactions.append(current_transaction)
                            current_transaction = None
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
                    line = ' '.join(w['text'].lower() for w in row_words)
                    
                    # Check for header row in both languages
                    if all(marker.lower() in line for marker in header_markers_en) or \
                       all(marker.lower() in line for marker in header_markers_id):
                        header_found = True
                        continue
                    
                    if not header_found:
                        continue
                    
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
                        if 0 < x < 100:
                            # Check for DD/MM, DD-MMM, and DD-MMM-YY formats
                            if re.match(r'\d{1,2}/\d{2}', text):
                                # Ensure day is two digits for DD/MM format
                                day, month = text.split('/')
                                transaction_date = f"{day.zfill(2)}/{month}"
                            elif re.match(r'\d{1,2}-[A-Za-z]{3}(-\d{2})?', text):
                                # Store the year if present for validation
                                parts = text.split('-')
                                if len(parts) > 2:
                                    transaction_year = parts[2]
                                transaction_date = convert_date_format(text)
                        
                        # Posting date (100 < x < 200)
                        elif 100 < x < 200:
                            # Check for DD/MM, DD-MMM, and DD-MMM-YY formats
                            if re.match(r'\d{1,2}/\d{2}', text):
                                # Ensure day is two digits for DD/MM format
                                day, month = text.split('/')
                                posting_date = f"{day.zfill(2)}/{month}"
                            elif re.match(r'\d{1,2}-[A-Za-z]{3}(-\d{2})?', text):
                                # Store the year if present for validation
                                parts = text.split('-')
                                if len(parts) > 2:
                                    posting_year = parts[2]
                                posting_date = convert_date_format(text)
                        
                        # Transaction details (200 < x < 500)
                        elif 200 < x < 500:
                            transaction_details.append(text)
                        
                        # Amount (500 < x < 625)
                        elif 500 < x < 625:
                            amount = text.strip()
                        
                        # DB/CR indicator (>= 625)
                        elif x >= 625:
                            if text.strip().upper() == 'CR':
                                db_cr = 'CR'
                    
                    # Skip rows where both dates have same year but no transaction details
                    skip_transaction = False
                    if 'transaction_year' in locals() and 'posting_year' in locals():
                        if transaction_year == posting_year and not transaction_details:
                            skip_transaction = True
                    
                    # If we found a transaction date and it's not skipped, create a new transaction
                    if transaction_date and not skip_transaction:
                        if current_transaction:
                            current_transaction['created_at'] = conversion_timestamp
                            transactions.append(current_transaction)
                        
                        current_transaction = {
                            'transaction_date': transaction_date,
                            'posting_date': posting_date,
                            'transaction_details': ' '.join(transaction_details),
                            'amount': amount,
                            'db_cr': db_cr,
                            'created_at': conversion_timestamp
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
                    current_transaction['created_at'] = conversion_timestamp
                    transactions.append(current_transaction)
                    current_transaction = None
                    
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    return pd.DataFrame(transactions) if transactions else pd.DataFrame(
        columns=['transaction_date', 'posting_date', 'transaction_details', 'amount', 'db_cr', 'created_at']
    )
