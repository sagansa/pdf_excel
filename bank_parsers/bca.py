import re
import os
import pdfplumber
import pandas as pd
from datetime import datetime
from decimal import Decimal, InvalidOperation

def parse_statement(pdf_path):
    if not os.path.exists(pdf_path):
        raise ValueError("PDF file not found")
        
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")
        
    transactions = []
    current_transaction = None
    header_found = False
    
    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_text_parts = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                raise ValueError("PDF file is empty or corrupted. Please ensure the file is a valid BCA statement")
            
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

                # Debug table structure
                table_settings = {
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "min_words_vertical": 3,
                    "min_words_horizontal": 2,
                    "snap_tolerance": 3,
                    "snap_x_tolerance": 2,
                    "snap_y_tolerance": 3,
                    "join_tolerance": 3,
                    "edge_min_length": 3,
                    "min_words_horizontal": 2
                }
                
                # Get table structure for debugging
                tables = page.debug_tablefinder(table_settings)
                
                # Extract text with position information
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3,
                    use_text_flow=True
                )
        
                # Add footer markers
                footer_markers = [
                    'TRANSAKSI TIDAK TERSEDIA',
                    'bersambung ke halaman berikut',
                    'SALDO AWAL :',
                    'MUTASI CR :',
                    'MUTASI DB :',
                    'SALDO AKHIR :'
                ]
        
                # Group words by y-position (rows)
                rows = {}
                for word in words:
                    # Skip if line contains any footer markers
                    line_text = word['text'].upper()  # Convert to uppercase for better matching
                    if any(marker.upper() in line_text for marker in footer_markers):
                        header_found = False  # Reset header flag when footer is found
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
                    
                    # Skip header rows with more robust detection
                    header_line = ' '.join(w['text'].upper() for w in row_words)
                    if 'TANGGAL' in header_line and ('KETERANGAN' in header_line or 'MUTASI' in header_line):
                        header_found = True
                        continue
                    
                    if not header_found:
                        continue
                    
                    try:
                        # Process row words into transaction
                        line = ' '.join(w['text'] for w in row_words)
                        # Skip if line contains any footer markers
                        if any(marker.upper() in line.upper() for marker in footer_markers):
                            continue
                        
                        # Enhanced date pattern matching for DD/MM format
                        date_match = re.match(r'^s*([0-3][0-9]/[0-1][0-9])s*', line)
                        
                        if date_match and len(date_match.group(1)) == 5:  # Ensure exact DD/MM format
                            # Validate date components
                            day, month = map(int, date_match.group(1).split('/'))
                            if 1 <= day <= 31 and 1 <= month <= 12:
                                if current_transaction:
                                    process_transaction(transactions, current_transaction, conversion_timestamp)
                                
                                # Initialize new transaction with date
                                current_transaction = {
                                    'date': date_match.group(1),
                                    'keterangan1': '',
                                    'keterangan2': '',
                                    'cbg': '',
                                    'mutasi': '',
                                    'saldo': ''
                                }
                                
                                # Process fields for the row with date
                                for word in row_words:
                                    x = word['x0']
                                    text = word['text']
                                    if x < 75:  # Date field
                                        continue
                                    elif x >= 75 and x < 180:  # Keterangan1 field
                                        current_transaction['keterangan1'] = text[:36]
                                    elif x >= 180 and x < 300:  # Keterangan2 field
                                        current_transaction['keterangan2'] = text[:90]
                                    elif x >= 300 and x < 320:  # CBG field
                                        if current_transaction['cbg']:
                                            current_transaction['cbg'] += ' ' + text
                                        else:
                                            current_transaction['cbg'] = text
                                    elif x >= 320 and x < 430:  # Mutasi field
                                        if current_transaction['mutasi']:
                                            current_transaction['mutasi'] += ' ' + text
                                        else:
                                            current_transaction['mutasi'] = text
                                    elif x >= 430 and x < 500:  # DB/CR indicator field
                                        text_upper = text.strip().upper()
                                        if text_upper == 'D' or text_upper == 'DB':
                                            current_transaction['db_cr'] = 'DB'
                                        else:
                                            current_transaction['db_cr'] = 'CR'
                                    elif x >= 500:  # Saldo field
                                        if current_transaction['saldo']:
                                            current_transaction['saldo'] += ' ' + text
                                        else:
                                            current_transaction['saldo'] = text
                                        current_transaction['saldo'] = text[:20]
                        else:
                            # Handle rows without date by concatenating to current transaction
                            if current_transaction:
                                for word in row_words:
                                    x = word['x0']
                                    text = word['text'].strip()
                                    if x >= 75 and x < 180:
                                        if current_transaction['keterangan1']:
                                            current_transaction['keterangan1'] = (current_transaction['keterangan1'] + ' ' + text)[:36]
                                        else:
                                            current_transaction['keterangan1'] = text[:36]
                                    elif x >= 180 and x < 300:
                                        if current_transaction['keterangan2']:
                                            current_transaction['keterangan2'] = (current_transaction['keterangan2'] + ' ' + text)[:90]
                                        else:
                                            current_transaction['keterangan2'] = text[:90]
                                    elif x >= 300 and x < 320:  # CBG field
                                        if current_transaction['cbg']:
                                            current_transaction['cbg'] += ' ' + text
                                        else:
                                            current_transaction['cbg'] = text
                                    elif x >= 320 and x < 430:  # Mutasi field
                                        if current_transaction['mutasi']:
                                            current_transaction['mutasi'] += ' ' + text
                                        else:
                                            current_transaction['mutasi'] = text
                                    elif x >= 430 and x < 500:  # DB/CR indicator field
                                        if text.strip().upper() == 'D':
                                            current_transaction['db_cr'] = 'DB'
                                    elif x >= 500:  # Saldo field
                                        current_transaction['saldo'] = text[:20]
                    except (IndexError, ValueError) as e:
                        # Log the error and continue with next row
                        print(f"Error processing row: {str(e)}")
                        continue
                
                if current_transaction:
                    process_transaction(transactions, current_transaction, conversion_timestamp)
                    current_transaction = None
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    if not transactions:
        raise ValueError("No transaction data found in the PDF. Please ensure this is a valid BCA statement")

    full_text = '\n'.join(full_text_parts)
    account_no = _extract_account_number(full_text)
    currency = _extract_currency(full_text) or 'IDR'
    base_year = _extract_period_year(full_text) or datetime.now().year
    bank_code = 'BCA'
    source_file = os.path.basename(pdf_path)

    standard_rows = []
    current_year = base_year
    last_month = None

    for entry in transactions:
        raw_date = entry.get('Tanggal', '').strip()
        txn_datetime = ''
        if raw_date:
            try:
                day, month = map(int, raw_date.split('/'))
                if last_month is not None and month < last_month:
                    current_year += 1
                last_month = month
                date_iso = datetime(current_year, month, day).strftime('%Y-%m-%d')
                txn_datetime = f"{date_iso} 00:00:00"
            except ValueError:
                txn_datetime = ''

        description_parts = [
            entry.get('Keterangan 1', '').strip(),
            entry.get('Keterangan 2', '').strip(),
            entry.get('CBG', '').strip()
        ]
        description = ' '.join(part for part in description_parts if part).strip()

        amount_value = _normalize_amount(entry.get('Mutasi', ''))
        db_cr = entry.get('DB/CR', 'CR').strip().upper() or 'CR'
        # Keep all amounts positive, DB/CR column indicates transaction type
        if amount_value and amount_value.startswith('-'):
            amount_value = amount_value.lstrip('-')

        balance_value = _normalize_amount(entry.get('Saldo', ''))

        standard_rows.append({
            'bank_code': bank_code,
            'account_no': account_no,
            'txn_date': txn_datetime,
            'posting_date': txn_datetime,
            'description': description,
            'amount': amount_value,
            'db_cr': db_cr,
            'balance': balance_value,
            'currency': currency,
            'created_at': entry.get('created_at', conversion_timestamp),
            'source_file': source_file
        })

    columns = ['bank_code', 'account_no', 'txn_date', 'posting_date', 'description', 'amount', 'db_cr', 'balance', 'currency', 'created_at', 'source_file']

    return pd.DataFrame(standard_rows, columns=columns)

def process_transaction(transactions, transaction, conversion_timestamp):
    transactions.append({
        'Tanggal': transaction['date'],
        'Keterangan 1': transaction['keterangan1'].strip(),
        'Keterangan 2': transaction['keterangan2'].strip(),
        'CBG': transaction['cbg'].strip(),
        'Mutasi': transaction['mutasi'].strip(),
        'DB/CR': transaction.get('db_cr', 'CR'),  # Default to CR if not specified
        'Saldo': transaction['saldo'].strip(),
        'created_at': conversion_timestamp
    })


def _extract_account_number(text: str) -> str:
    match = re.search(r'NO\.?\s*REK(?:ENING)?\s*:?[\s\n]*([0-9\s]+)', text, re.IGNORECASE)
    if match:
        return re.sub(r'\D', '', match.group(1))
    return ''


def _extract_currency(text: str) -> str:
    match = re.search(r'MATA\s+UANG\s*:?[\s\n]*([A-Z]{3})', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return ''


def _extract_period_year(text: str) -> int | None:
    match = re.search(r'PERIODE\s*:?[\s\n]*[A-Z]+\s+(\d{4})', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    years = re.findall(r'(?:19|20)\d{2}', text)
    if years:
        return int(years[0])
    return None


def _normalize_amount(value: str) -> str:
    if not value:
        return ''

    cleaned = value
    cleaned = cleaned.replace('CR', '').replace('DB', '').replace('Rp', '')
    cleaned = cleaned.replace(' ', '').replace('\u00a0', '')
    # BCA uses comma as thousand separator and period as decimal separator
    # Remove commas (thousand separator), keep periods (decimal separator)
    cleaned = cleaned.replace(',', '')

    if cleaned.count('.') > 1:
        parts = cleaned.split('.')
        integer = ''.join(parts[:-1])
        decimal = parts[-1]
        cleaned = integer + '.' + decimal

    try:
        dec = Decimal(cleaned)
        return format(dec, '.2f')
    except InvalidOperation:
        return value.strip()
