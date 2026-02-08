import pdfplumber
import pandas as pd
import re
import os
from datetime import datetime

# Define Month Map for DBS
MONTH_MAP_DBS = {
    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'MEI': 5,
    'JUN': 6, 'JUL': 7, 'AUG': 8, 'AGT': 8, 'SEP': 9, 'OCT': 10, 'OKT': 10,
    'NOV': 11, 'DEC': 12, 'DES': 12
}

def parse_statement(pdf_path, password=None, target_year=None):
    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    transactions = []
    header_found = False
    current_transaction = None
    last_y = 0
    MAX_Y_GAP = 15  # Maximum vertical space to consider a line a continuation
    
    # Text fragments that indicate a line is footer/info text, not transaction detail
    BLACKLIST = [
        'CONTINUE TO NEXT PAGE', 'IMPORTANT!', 'USE YOUR PIN', 'TO SET OR CHANGE',
        'LOG IN TO YOUR', 'VISIT HTTPS', 'DBS CUSTOMER CENTRE', 'TOTAL TRANSAKSI',
        'POIN SEKARANG', 'BUNGA DAN', 'PEMBAYARAN DAN KREDIT'
    ]
    
    try:
        # Open PDF with password if provided
        with pdfplumber.open(pdf_path, password=password) as pdf:
            for page in pdf.pages:
                # Reset vertical tracking for each page
                last_y = 0
                
                # Extract text with position information
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3
                )
                
                # Group words by y-position (rows)
                rows = {}
                for word in words:
                    y = round(word['top'], 1)
                    if y not in rows:
                        rows[y] = []
                    rows[y].append(word)
                
                # Sort rows by y-position
                sorted_rows = sorted(rows.items())

                for y, row_words in sorted_rows:
                    # Sort words in row by x-position
                    row_words.sort(key=lambda w: w['x0'])
                    line_text = ' '.join(w['text'] for w in row_words).strip()
                    
                    # Detect potential date at the start (x < 100)
                    row_date = None
                    for word in row_words:
                        text = word['text'].upper().strip()
                        x = word['x0']
                        
                        if x >= 100: break # Date must be at start
                        
                        # Match MM/DD (e.g. 10/05 = Oct 5)
                        if re.match(r'^\d{2}/\d{2}$', text):
                            try:
                                month = int(text[:2])
                                day = int(text[3:])
                                if 1 <= day <= 31 and 1 <= month <= 12:
                                    row_date = f"{month:02d}/{day:02d}"
                                    break
                            except: pass
                        
                        # Match DD-MMM (e.g. 05-OCT or 05 OCT)
                        if re.match(r'^\d{1,2}-[A-Z]{3}$', text):
                             try:
                                 parts = text.split('-')
                                 day = int(parts[0])
                                 m_str = parts[1]
                                 if m_str in MONTH_MAP_DBS:
                                     row_date = f"{day:02d}/{MONTH_MAP_DBS[m_str]:02d}"
                                     break
                             except: pass

                    if row_date:
                        # If a new date is found, save the previous transaction if it exists
                        if current_transaction:
                            transactions.append(current_transaction)
                        
                        current_transaction = {
                            'Transaction Date': row_date,
                            'Posting Date': '',
                            'Transaction Details': '',
                            'Amount': '',
                            'DB/CR': 'DB',
                            'created_at': conversion_timestamp
                        }
                        
                        # Process fields for the current row
                        for word in row_words:
                            x = word['x0']
                            text = word['text']
                            
                            # Posting Date (approx 100 <= x < 200)
                            if 100 <= x < 200:
                                if re.match(r'^\d{2}/\d{2}$', text):
                                    current_transaction['Posting Date'] = text
                            
                            # Details (approx 200 <= x < 450)
                            elif 200 <= x < 450:
                                if not current_transaction['Transaction Details']:
                                    current_transaction['Transaction Details'] = text
                                else:
                                    current_transaction['Transaction Details'] += ' ' + text
                            
                            # Amount (approx x >= 479)
                            elif x >= 479:
                                val = text.replace(',', '').strip()
                                if 'CR' in val.upper():
                                    val = val.upper().replace('CR', '').strip()
                                    current_transaction['DB/CR'] = 'CR'
                                
                                if val.upper() != 'RP.':
                                    current_transaction['Amount'] = val
                        
                        last_y = y  # Update last vertical position
                    
                    elif current_transaction:
                        # Skip explicit navigation/footer lines
                        is_blacklist = any(item in line_text.upper() for item in BLACKLIST)
                        is_too_far = (y - last_y) > MAX_Y_GAP
                        
                        if is_blacklist or is_too_far:
                            # If we hit garbage or wide gap, finalize current transaction
                            transactions.append(current_transaction)
                            current_transaction = None
                            continue

                        # Continuation check
                        detail_parts = []
                        has_amount = False
                        for word in row_words:
                            x = word['x0']
                            text = word['text']
                            if 200 <= x < 450:
                                detail_parts.append(text)
                            elif x >= 479 and any(c.isdigit() for c in text):
                                has_amount = True
                        
                        if detail_parts and not has_amount:
                            current_transaction['Transaction Details'] += ' ' + ' '.join(detail_parts)
                            last_y = y  # Only update last_y for successful continuation
                        # If it has a new amount but no date, it shouldn't happen in DBS, 
                        # but we save previous and handle this as a weird case?
                        # For now, let's just ignore non-transaction lines like headers.
                
                # Save last transaction of the page
                if current_transaction:
                    transactions.append(current_transaction)
                    current_transaction = None
    
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    if not transactions:
        raise ValueError("No transaction data found in the PDF. Please ensure this is a valid DBS statement")

    full_text = '\n'.join([page.extract_text() or '' for page in pdf.pages])
    
    # Debug logging
    with open('debug_dbs.log', 'w') as f:
        f.write(f"Starting DBS parse - target_year: {target_year}\n")
        f.write(f"Full text snippet (first 1000 chars): {full_text[:1000]}\n")
    
    account_no = _extract_account_number(full_text)
    currency = _extract_currency(full_text) or 'IDR'
    
    # Extract statement date (day, month, year)
    st_day, st_month, st_year = _extract_statement_date(full_text)
    extracted_year = target_year or st_year or datetime.now().year
    
    with open('debug_dbs.log', 'a') as f:
        f.write(f"Extracted statement info: day={st_day}, month={st_month}, year={st_year}\n")
        f.write(f"Final extracted_year: {extracted_year}\n")
    
    bank_code = 'DBS'
    source_file = os.path.basename(pdf_path)

    rows = []
    current_year = extracted_year
    last_month = None  # Track last month for year rollover detection
    first_transaction = True  # Flag to check first transaction
    
    for entry in transactions:
        raw_date = entry.get('Transaction Date', '').strip()
        
        # Extract month from raw_date for year rollover detection
        month_num = None
        if raw_date and '/' in raw_date:
            try:
                month_num = int(raw_date.split('/')[0])  # MM/DD format
            except:
                pass
        
        # Adjust starting year logic
        # If the first transaction month is significantly ahead of the statement month, 
        # it likely belongs to the previous year (e.g. Dec transaction in a Jan statement).
        if first_transaction and month_num is not None:
            if st_month is not None:
                # If transaction month is greater than statement month, it's from previous year
                if month_num > st_month:
                    current_year -= 1
                    with open('debug_dbs.log', 'a') as f:
                        f.write(f"First txn month {month_num} > statement month {st_month}, adjusting year to {current_year}\n")
            else:
                # Fallback: only subtract if it's Oct-Dec AND we don't have a clear year info
                # This is less reliable but keeps some safety if statement date is missed.
                # HOWEVER, if target_year is provided, we should be careful.
                if target_year is None and month_num >= 10:
                    current_year -= 1
                    with open('debug_dbs.log', 'a') as f:
                        f.write(f"No statement month, but month {month_num} >= 10, adjusting year to {current_year}\n")
            
            first_transaction = False
        
        # Year rollover detection
        if last_month is not None and month_num is not None:
            # Detect year boundary: 
            # 1. Going forward (Ascending): month jumps from large (10-12) to small (1-3)
            if month_num <= 3 and last_month >= 10:
                with open('debug_dbs.log', 'a') as f:
                    f.write(f"Year rollover detected (ASCENDING): last_month={last_month}, month_num={month_num}, incrementing year from {current_year} to {current_year+1}\n")
                current_year += 1
            # 2. Going backward (Descending): month jumps from small (1-3) to large (10-12)
            elif month_num >= 10 and last_month <= 3:
                with open('debug_dbs.log', 'a') as f:
                    f.write(f"Year rollover detected (DESCENDING): last_month={last_month}, month_num={month_num}, decrementing year from {current_year} to {current_year-1}\n")
                current_year -= 1
        
        if month_num is not None:
            last_month = month_num
        
        txn_iso = _convert_dbs_date(raw_date, current_year)
        
        with open('debug_dbs.log', 'a') as f:
            f.write(f"Processing: raw_date={raw_date}, month={month_num}, current_year={current_year}, result={txn_iso}\n")
        
        description = entry.get('Transaction Details', '').strip()
        
        amount_val = entry.get('Amount', '').strip()
        amount_dec = _parse_decimal(amount_val)
        
        db_cr = entry.get('DB/CR', 'DB').strip().upper() 
        
        if amount_dec is not None:
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
    match = re.search(r'Account\s+Number\s*:\s*([0-9-]+)', text, re.IGNORECASE)
    if match:
        return match.group(1).replace('-', '')
    return ''

def _extract_currency(text: str) -> str:
    # Basic guess or regex
    if 'IDR' in text: return 'IDR'
    return 'IDR'

def _extract_statement_date(text: str) -> tuple[int | None, int | None, int | None]:
    """Extracts (day, month, year) from header text"""
    # 1. Look for 'Statement Date : DD MMM YYYY'
    match = re.search(r'Statement\s+Date\s*:\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', text, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        m_str = match.group(2).upper()[:3]
        year = int(match.group(3))
        month = MONTH_MAP_DBS.get(m_str)
        return day, month, year
    
    # 2. Look for numeric date patterns (MM/DD/YYYY or DD/MM/YYYY)
    # DBS often has a date range at the top like 01/19/2025 to 02/04/2025
    # We take the first full date as a hint for the "current" statement month/year
    date_matches = re.finditer(r'(\d{2})/(\d{2})/(\d{4})', text)
    for match in date_matches:
        v1 = int(match.group(1))
        v2 = int(match.group(2))
        year = int(match.group(3))
        # DBS is usually US format: MM/DD/YYYY
        if 1 <= v1 <= 12 and 1 <= v2 <= 31:
            month, day = v1, v2
            return day, month, year
    
    # 3. Fallback for just year
    years = re.findall(r'(?:19|20)\d{2}', text)
    year = int(years[0]) if years else None
    return None, None, year

def _convert_dbs_date(raw: str, year: int) -> str:
    if not raw: return ''
    try:
        # Expected format MM/DD from extraction (DBS uses US format)
        if '/' in raw and len(raw) == 5:
            month = int(raw[:2])
            day = int(raw[3:])
            return f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)} 00:00:00"
    except:
        pass
    return ''

def _parse_decimal(value: str):
    if not value: return None
    cleaned = value.replace(',', '').replace('CR', '').strip()
    try:
        return float(cleaned)
    except:
        return None
