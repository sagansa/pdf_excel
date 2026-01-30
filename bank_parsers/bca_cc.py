import pdfplumber
import pandas as pd
import re
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Month abbreviation to number mapping
MONTH_MAP = {
    'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
    'MAY': '05', 'MEI': '05', 'JUN': '06', 'JUL': '07', 
    'AUG': '08', 'AGT': '08', 'SEP': '09', 'OCT': '10', 
    'OKT': '10', 'NOV': '11', 'DEC': '12', 'DES': '12'
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
    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    current_transaction = None
    header_found = False
    full_text_parts = []
    
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
                page_text = page.extract_text()
                if page_text:
                    full_text_parts.append(page_text)
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
        return pd.DataFrame(columns=['bank_code', 'account_no', 'txn_date', 'posting_date', 'description', 'amount', 'db_cr', 'balance', 'currency', 'created_at', 'source_file'])

    full_text = '\n'.join(full_text_parts)
    account_no = _extract_account_number(full_text)
    currency = _extract_currency(full_text) or 'IDR'
    base_year = _extract_year(full_text) or datetime.now().year
    bank_code = 'BCA_CC'
    source_file = os.path.basename(pdf_path)

    rows = []
    current_year = base_year
    last_month = None

    for entry in transactions:
        raw_txn = entry.get('transaction_date', '').strip()
        raw_post = entry.get('posting_date', '').strip()
        txn_iso, last_month, current_year = _convert_cc_date(raw_txn, last_month, current_year)
        post_iso, _, _ = _convert_cc_date(raw_post, None, current_year)

        description = (entry.get('transaction_details') or '').strip()

        amount_dec = _parse_decimal(entry.get('amount', ''))
        if amount_dec is None:
            amount_value = ''
            db_cr = entry.get('db_cr', '').strip().upper()
        else:
            db_cr = entry.get('db_cr', '').strip().upper() or ('CR' if amount_dec >= 0 else 'DB')
            if db_cr == 'DB' and amount_dec > 0:
                amount_dec = -amount_dec
            elif db_cr == 'CR' and amount_dec < 0:
                amount_dec = -amount_dec
            amount_value = _format_amount(amount_dec)

        rows.append({
            'bank_code': bank_code,
            'account_no': account_no,
            'txn_date': txn_iso,
            'posting_date': post_iso,
            'description': description,
            'amount': amount_value,
            'db_cr': db_cr or '',
            'balance': '',
            'currency': currency,
            'created_at': entry.get('created_at', conversion_timestamp),
            'source_file': source_file
        })

    columns = ['bank_code', 'account_no', 'txn_date', 'posting_date', 'description', 'amount', 'db_cr', 'balance', 'currency', 'created_at', 'source_file']
    return pd.DataFrame(rows, columns=columns)


def _extract_account_number(text: str) -> str:
    match = re.search(r'(\d{4}-\d{2}XX-XXXX-\d{4})', text)
    if match:
        return match.group(1)
    return ''


def _extract_currency(text: str) -> str:
    match = re.search(r'JUMLAH\s*\(\s*([A-Z]{2,3})\s*\)', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return ''


def _extract_year(text: str) -> int | None:
    match = re.search(r'TANGGAL\s+REKENING\s*:\s*\d{1,2}\s+[A-Za-z]+\s+(\d{4})', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    years = re.findall(r'(?:19|20)\d{2}', text)
    if years:
        return int(years[0])
    return None


def _convert_cc_date(raw: str, last_month: int | None, current_year: int):
    if not raw:
        return '', last_month, current_year
    raw = raw.strip()
    
    day = None
    month_int = None
    
    if '-' in raw:
        # Handle DD-MMM format (e.g., 22-DES)
        parts = raw.split('-', 1)
        if len(parts) == 2:
            try:
                day = int(parts[0])
                month_str = parts[1].upper()
                month_val = MONTH_MAP.get(month_str)
                if month_val:
                    month_int = int(month_val)
            except ValueError:
                pass
    elif '/' in raw:
        # Handle DD/MM format
        parts = raw.split('/', 1)
        if len(parts) == 2:
            try:
                # BCA typically uses DD/MM in CC statements
                day = int(parts[0])
                month_int = int(parts[1])
            except ValueError:
                pass

    if day is not None and month_int is not None:
        try:
            # Basic validation
            if not (1 <= day <= 31 and 1 <= month_int <= 12):
                return '', last_month, current_year
                
            if last_month is not None and month_int < last_month:
                current_year += 1
            last_month = month_int
            date_iso = f"{current_year}-{str(month_int).zfill(2)}-{str(day).zfill(2)}"
            return f"{date_iso} 00:00:00", last_month, current_year
        except Exception:
            return '', last_month, current_year
            
    return '', last_month, current_year


def _parse_decimal(value: str):
    if not value:
        return None
    cleaned = value.strip().replace('\u00a0', '').replace(' ', '').replace('CR', '').replace('DB', '')
    if not cleaned:
        return None
    sign = -1 if cleaned.startswith('-') else 1
    cleaned = cleaned.lstrip('+-')
    cleaned = cleaned.replace('.', '').replace(',', '.')
    try:
        dec = Decimal(cleaned)
    except InvalidOperation:
        return None
    return dec * sign


def _format_amount(dec: Decimal) -> str:
    if dec is None:
        return ''
    return format(dec, '.2f')
