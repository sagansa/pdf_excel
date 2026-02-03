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
    
    if not transactions:
        raise ValueError("No transaction data found in the PDF. Please ensure this is a valid Mandiri credit card statement")

    full_text = '\n'.join([page.extract_text() or '' for page in pdf.pages])
    account_no = _extract_account_number(full_text)
    currency = _extract_currency(full_text) or 'IDR'
    extracted_year = _extract_year(full_text) or datetime.now().year
    bank_code = 'MANDIRI_CC'
    source_file = os.path.basename(pdf_path)

    rows = []
    current_year = extracted_year
    last_month = None

    for entry in transactions:
        raw_txn = entry.get('transaction_date', '').strip()
        txn_iso, last_month, current_year = _convert_mandiri_cc_date(raw_txn, last_month, current_year)
        
        description = entry.get('transaction_details', '').strip()
        
        amount_val = entry.get('amount', '').strip()
        amount_dec = _parse_decimal(amount_val)
        
        db_cr = entry.get('db_cr', 'DB').strip().upper()

        if amount_dec is not None:
             # Standardize: Amount string 2 decimals
             # Mandiri CC: DB is usually regular charge (positive in statement but 'DB' logical). 
             # BCA CC logic treats charges as 'DB' but amount is positive string.
             # We store absolute string. DB/CR column handles the sign logic for app.
             amount_str = format(abs(amount_dec), '.2f')
        else:
             amount_str = ''

        rows.append({
            'bank_code': bank_code,
            'account_no': account_no,
            'txn_date': txn_iso,
            'posting_date': txn_iso, 
            'description': description,
            'amount': amount_str,
            'db_cr': db_cr,
            'balance': '',
            'currency': currency,
            'created_at': entry.get('created_at', conversion_timestamp),
            'source_file': source_file
        })

    columns = ['bank_code', 'account_no', 'txn_date', 'posting_date', 'description', 'amount', 'db_cr', 'balance', 'currency', 'created_at', 'source_file']
    return pd.DataFrame(rows, columns=columns)

def _extract_account_number(text: str) -> str:
    match = re.search(r'No\s+Kartu\s*:\s*(\d{4}\s+\d{4}\s+\d{4}\s+\d{4})', text, re.IGNORECASE)
    if match:
        return match.group(1).replace(' ', '')
    return ''

def _extract_currency(text: str) -> str:
    return 'IDR'

def _extract_year(text: str) -> int | None:
    # Look for "TANGGAL TAGIHAN : 20 MEI 2023"
    match = re.search(r'Tanggal\s+Tagihan\s*:\s*\d{1,2}\s+[A-Za-z]+\s+(\d{4})', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    years = re.findall(r'(?:19|20)\d{2}', text)
    if years:
        return int(years[0])
    return None

def _convert_mandiri_cc_date(raw: str, last_month: int | None, current_year: int):
    # Raw is like DD/MM or DD/MM/YY (from convert_date_format)
    if not raw: return '', last_month, current_year
    
    try:
        parts = raw.split('/')
        day = int(parts[0])
        month = int(parts[1])
        year_part = int(parts[2]) if len(parts) > 2 else None
        
        # Determine year
        date_year = current_year
        if year_part:
            if year_part < 100: date_year = 2000 + year_part
            else: date_year = year_part
        else:
             # Basic rollover logic if we don't have year
             if last_month is not None and month < last_month:
                 # Usually checking back in time? 
                 # If statement is Jan, and we see Dec transaction, it is prev year.
                 pass # Logic already handled?
             # Let's trust extracted_year as base.
        
        last_month = month
        return f"{date_year}-{str(month).zfill(2)}-{str(day).zfill(2)} 00:00:00", last_month, current_year
    except:
        return '', last_month, current_year

from decimal import Decimal, InvalidOperation
def _parse_decimal(value: str):
    if not value: return None
    cleaned = value.replace('CR', '').replace('DB', '').replace(',', '').strip()
    # Mandiri CC uses comma as thousands sep usually? Or dot?
    # Original logic didn't specify. DBS uses comma. Mandiri (regular) uses dot for thousands, comma for decimal.
    # Check original amount regex or patterns.
    # Mandiri CC PDF usually: "500.000" -> 500000? Or "500,000.00"?
    # If using pdfplumber raw text locally, Mandiri CC usually ID format.
    # "1.000.000,00"
    # But this parser might be simpler.
    # Let's assume standard ID format if dots present.
    try:
        if '.' in cleaned and ',' in cleaned:
             cleaned = cleaned.replace('.', '').replace(',', '.')
        elif ',' in cleaned: # "500,00" or "500,000"
             if len(cleaned.split(',')[-1]) == 2: # Decimal
                  cleaned = cleaned.replace('.', '').replace(',', '.') # Treat as ID
             else:
                  cleaned = cleaned.replace(',', '') # Treat as US
        
        return float(cleaned)
    except:
        return None
