import os
import re
from datetime import datetime
import pandas as pd
import pdfplumber

# Month abbreviation mapping for date conversion
MONTH_ABBR = {
    'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
    'MAY': '05', 'MEI': '05', 'JUN': '06', 'JUL': '07', 
    'AUG': '08', 'AGT': '08', 'SEP': '09', 'OCT': '10', 
    'OKT': '10', 'NOV': '11', 'DEC': '12', 'DES': '12'
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

def parse_statement(pdf_path, password=None):
    if not os.path.exists(pdf_path):
        raise ValueError("PDF file not found")
        
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")
        
    transactions = []
    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
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

            # Define header and footer markers
            header_markers_en = ['Transaction Date', 'Posting Date', 'Description', 'Amount (IDR)']
            header_markers_id = ['Tanggal Transaksi', 'Tanggal Pembukuan', 'Keterangan', 'Jumlah']
            
            skip_markers = [
                'TAGIHAN BULAN LALU', 'Description', 'Amount (IDR)', 'Keterangan', 'Jumlah',
                'SISA', 'TAGIHAN', 'CICILAN', 'KUALITAS', 'KREDIT', 'REMAINING', 'INSTALLMENT', 
                'BATAS', 'PENARIKAN', 'TUNAI', 'LIVIN\'POIN', 'CASH', 'ADVANCE', 'LIMIT', 'LOAN', 'PERFORMANCE',
                'LANCAR', 'PENAGIHAN', 'SUMMARY', 'TOTAL'
            ]
            
            current_transaction = None
            header_found = False
            
            for page in pdf.pages:
                # Extract text with position information
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3
                )
                
                # Group words by y-position (rows) with tolerance
                rows = {}
                for word in words:
                    y = word['top']
                    # Find existing row within 3px tolerance
                    matched_y = None
                    for existing_y in rows:
                        if abs(y - existing_y) < 3:
                            matched_y = existing_y
                            break
                    
                    if matched_y is not None:
                        rows[matched_y].append(word)
                    else:
                        rows[y] = [word]
                
                # Sort rows by y-position
                sorted_rows = sorted(rows.items())
                page_finished = False
                
                for y, row_words in sorted_rows:
                    if page_finished:
                        break
                        
                    # Sort words in row by x-position
                    row_words.sort(key=lambda w: w['x0'])
                    line = ' '.join(w['text'].lower() for w in row_words)
                    line_upper = line.upper()

                    # Check for header row in both languages
                    if all(marker.lower() in line for marker in header_markers_en) or \
                       all(marker.lower() in line for marker in header_markers_id):
                        header_found = True
                        continue
                    
                    if not header_found:
                         continue
                    
                    # If we hit SUB-TOTAL, finalize current transaction and look for next header (for supplementary cards)
                    if 'SUB-TOTAL' in line_upper:
                        if current_transaction:
                            current_transaction['created_at'] = conversion_timestamp
                            transactions.append(current_transaction)
                            current_transaction = None
                        header_found = False
                        continue

                    # HARD STOP: If we hit real summary headers, this page's table is done
                    # ONLY stop if we have found a header (avoid summary at top of page 1)
                    if header_found and any(marker in line_upper for marker in ['TOTAL TAGIHAN', 'SISA TAGIHAN', 'KUALITAS KREDIT']):
                        page_finished = True
                        break

                    # Process each row
                    transaction_date = ''
                    posting_date = ''
                    transaction_details = []
                    amount = ''
                    db_cr = 'DB'  # Default to DB
                    
                    for word in row_words:
                        text = word['text']
                        x = word['x0']
                        
                        # Normalize text for marker comparison
                        clean_text = re.sub(r'[^a-zA-Z]', '', text).upper()
                        
                        # Check for footer keywords at the word level to skip noise
                        if any(marker in clean_text for marker in skip_markers if len(marker) > 3):
                             continue
                        if clean_text in skip_markers:
                             continue

                        # Transaction date (0 < x < 105)
                        if 0 < x < 105:
                            if re.match(r'\d{1,2}/\d{2}', text):
                                day, month = text.split('/')
                                transaction_date = f"{day.zfill(2)}/{month}"
                            elif re.match(r'\d{1,2}-[A-Za-z]{3}(-\d{2})?', text):
                                transaction_date = convert_date_format(text)
                            elif transaction_date: 
                                pass
                        
                        # Posting date (100 < x < 210)
                        elif 100 < x < 210:
                            if re.match(r'\d{1,2}/\d{2}', text):
                                day, month = text.split('/')
                                posting_date = f"{day.zfill(2)}/{month}"
                            elif re.match(r'\d{1,2}-[A-Za-z]{3}(-\d{2})?', text):
                                posting_date = convert_date_format(text)
                        
                        # Amount detection (usually after description, 400 < x < 630)
                        elif x > 400:
                            clean_val = text.strip()
                            if clean_val.upper() == 'CR':
                                db_cr = 'CR'
                            elif re.match(r'^-?[\d.,]+$', clean_val):
                                if not amount:
                                    amount = clean_val
                        
                        # Everything else in between is details
                        elif 150 < x < 550:
                            transaction_details.append(text)
                    
                    # If we found a transaction date, start a new transaction
                    if transaction_date:
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
                    
                    # If no date found and we have a current transaction, it's a continuation line
                    elif current_transaction and transaction_details:
                        current_details = current_transaction['transaction_details']
                        new_details = ' '.join(transaction_details)
                        current_transaction['transaction_details'] = f"{current_details} {new_details}".strip()
                        
                        if amount and not current_transaction['amount']:
                            current_transaction['amount'] = amount
                        
                        if db_cr == 'CR' and current_transaction['db_cr'] != 'CR':
                            current_transaction['db_cr'] = 'CR'
                
                # Check for interest at the end of the page to finalize
                if current_transaction:
                    details_upper = current_transaction['transaction_details'].upper()
                    if 'INTEREST' in details_upper or 'BUNGA' in details_upper:
                        current_transaction['created_at'] = conversion_timestamp
                        transactions.append(current_transaction)
                        current_transaction = None

            # Add the very last transaction if exists after all pages
            if current_transaction:
                current_transaction['created_at'] = conversion_timestamp
                transactions.append(current_transaction)
                    
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
    # Remove non-numeric characters except dots, commas, and minus
    cleaned = re.sub(r'[^0-9.,-]', '', value).strip()
    if not cleaned: return None
    
    try:
        # If both dots and commas exist: 1.234.567,89 (ID) or 1,234,567.89 (US)
        if '.' in cleaned and ',' in cleaned:
            if cleaned.rfind(',') > cleaned.rfind('.'):
                # ID format: 1.234,56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # US format: 1,234.56
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned: 
            # Only commas: 1,234,567 (US) or 1234,56 (ID decimal)
            if len(cleaned.split(',')[-1]) == 2:
                # 1234,56
                cleaned = cleaned.replace(',', '.')
            else:
                # 1,234,567
                cleaned = cleaned.replace(',', '')
        elif '.' in cleaned:
            # Only dots: 1.234.567 (ID) or 1234.56 (Standard)
            # If the last part has exactly 2 digits, assume it's decimal point
            parts = cleaned.split('.')
            if len(parts[-1]) == 2:
                # 1234.56
                pass 
            else:
                # 1.234.567
                cleaned = cleaned.replace('.', '')
        
        return float(cleaned)
    except:
        return None
