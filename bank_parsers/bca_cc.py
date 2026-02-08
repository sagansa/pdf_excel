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

def parse_statement(pdf_path, base_year=None, password=None):
    if not os.path.exists(pdf_path):
        raise ValueError("PDF file not found")
        
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")
        
    transactions = []
    full_text_parts = []
    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Initialize debug log
    with open('debug_bca.log', 'w') as f:
        f.write(f"START PARSE {datetime.now()}\n")
        f.write(f"base_year: {base_year}\n")
    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
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

            current_transaction = None
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
                
                # Expanded footer and header markers and noise reduction
                # Expanded footer and header markers and noise reduction
                skip_markers = [
                    'TAGIHAN SEBELUMNYA', 'REKENING KARTU KREDIT', 'INFORMASI KARTU KREDIT',
                    'TANGGAL JATUH TEMPO', 'TAGIHAN BARU', 'PEMBAYARAN MINIMUM',
                    'KUALITAS KREDIT', 'SALDO SEBELUMNYA', 'SUBTOTAL',
                    'TOTAL TRANSAKSI', 'SESUAI PMK', 'HUBUNGI HALO BCA',
                    'KETERANGAN JUMLAH', 'TANGGAL PEMBUKUAN', 'PROMO MENARIK',
                    'BERSAMBUNG KE HALAMAN BERIKUT', 'HALAMAN :', 'MATA UANG :',
                    'DARI BATAS KREDIT', 'TUNGGAKAN', 'BIAYA ADM', 
                    'TERIMA KASIH', 'SISA TAGIHAN',
                    'PENAWARAN SPESIAL', 'INFO 1500888', 'BLOKIR KARTU', 'CARA PEMBAYARAN',
                    'WASPADA MODUS', 'NOMOR CUSTOMER', 'SUKU BUNGA', 
                    'PRASMANAN', 'DINING', '1500888',
                    'MEMPROSES', 'LEMBARAN', 'CEK/BILYET', 'PENGKINIAN', 'OTORISASI',
                    'NOTIFIKASI', 'KLAUSUL', 'ADM', ' BIAYA '
                ]
                
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
                
                # Flag to skip content until a new transaction date is found
                in_summary_section = False
                
                for y, row_words in sorted_rows:
                    row_words.sort(key=lambda w: w['x0'])
                    # Construct full line text for skip checking
                    full_line_text = ' '.join([w['text'] for w in row_words]).upper()
                    
                    # Detect end of transaction section
                    is_total_line = "TOTAL" in full_line_text and any(w['x0'] < 100 for w in row_words)
                    is_summary_line = any(marker in full_line_text for marker in ['SALDO SEBELUMNYA', 'LIMIT KREDIT', 'TAGIHAN BARU'])
                    
                    if is_total_line or is_summary_line:
                         if current_transaction:
                             current_transaction['created_at'] = conversion_timestamp
                             transactions.append(current_transaction)
                             current_transaction = None
                         in_summary_section = True
                         continue

                    if any(marker in full_line_text for marker in skip_markers):
                        if "BIAYA IURAN TAHUNAN" in full_line_text or "BEA METERAI" in full_line_text:
                            pass
                        else:
                            continue
                    
                    if (re.search(r'\d+\s*/\s*\d+', full_line_text) and len(full_line_text) < 20) or "HALAMAN :" in full_line_text:
                         continue

                    row_txn_date = ''
                    row_posting_date = ''
                    row_details = []
                    row_amount = None
                    row_db_cr = 'DB'
                    
                    for word in row_words:
                        text = word['text']
                        x = word['x0']
                        y_pos = word['top']
                        if text.strip():
                            with open('debug_bca.log', 'a') as f:
                                f.write(f"  Word: '{text}' at x={x:.2f}, y={y_pos:.2f}\n")
                        
                        # Transaction date (0 < x < 125)
                        if 0 < x < 125:
                            if re.match(r'^\d{2}/\d{2}$', text) or re.match(r'^\d{2}-[A-Za-z]{3}$', text):
                                row_txn_date = convert_date_format(text)
                                in_summary_section = False
                            elif re.match(r'^\d{2}-[A-Za-z]{3}-\d{2,4}$', text):
                                row_txn_date = convert_date_format(text)
                                in_summary_section = False
                        
                        # Posting date (125 < x < 195)
                        elif 125 <= x < 195:
                            if re.match(r'^\d{2}/\d{2}$', text) or re.match(r'^\d{2}-[A-Za-z]{3}$', text):
                                row_posting_date = convert_date_format(text)
                        
                        # Transaction details (185 <= x < 480)
                        elif 185 <= x < 480:
                            if text.strip():
                                row_details.append(text.strip())
                        
                        # Amount (x >= 480)
                        elif x >= 480:
                            if text.strip() and not re.match(r'^[A-Za-z]+$', text.strip()):
                                # Handle numbers with dots and commas
                                row_amount = text.strip()
                                if 'CR' in text.upper():
                                    row_db_cr = 'CR'
                            elif 'CR' in text.upper():
                                row_db_cr = 'CR'
                            elif 'DB' in text.upper():
                                row_db_cr = 'DB'

                    # Process the row results
                    if row_txn_date:
                        # New transaction starts
                        if current_transaction:
                            current_transaction['created_at'] = conversion_timestamp
                            transactions.append(current_transaction)
                        
                        current_transaction = {
                            'bank_code': 'BCA_CC',
                            'account_no': None,
                            'txn_date': row_txn_date,
                            'posting_date': row_posting_date or row_txn_date,
                            'transaction_details': ' '.join(row_details),
                            'amount': row_amount,
                            'db_cr': row_db_cr,
                            'balance': None,
                            'currency': None,
                            'created_at': conversion_timestamp
                        }
                    elif current_transaction and row_details and not in_summary_section:
                        # Continuation line
                        new_details_str = ' '.join(row_details)
                        new_details_upper = new_details_str.upper()
                        
                        # Stop appending if we hit clear footer text
                        if any(marker in new_details_upper for marker in skip_markers) or "TOTAL" in new_details_upper:
                             continue
                        
                        # Specific exclusions for description appending
                        if re.match(r'^\d{4}-\d{4}-\d{4}-\d{4}$', new_details_str.strip()) or "NOMOR KARTU" in new_details_upper:
                             continue
                        if "@BCA.CO.ID" in new_details_upper or "WWW.BCA.CO.ID" in new_details_upper:
                             continue
                        if "LIMIT" in new_details_upper or "MINIMUM" in new_details_upper:
                             continue

                        curr_desc = current_transaction.get('transaction_details', '')
                        if new_details_str not in curr_desc:
                            current_transaction['transaction_details'] = f"{curr_desc} {new_details_str}".strip()
                        
                        if row_amount and not current_transaction.get('amount'):
                            current_transaction['amount'] = row_amount
                            current_transaction['db_cr'] = row_db_cr
                        if row_db_cr == 'CR' and current_transaction['db_cr'] != 'CR':
                            current_transaction['db_cr'] = 'CR'

            # Add the last transaction after all pages
            if current_transaction:
                current_transaction['created_at'] = conversion_timestamp
                transactions.append(current_transaction)

    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    if not transactions:
        return pd.DataFrame(columns=['bank_code', 'account_no', 'txn_date', 'posting_date', 'description', 'amount', 'db_cr', 'balance', 'currency', 'created_at', 'source_file'])

    full_text = '\n'.join(full_text_parts)
    # Debug logging moved to start
    # with open('debug_bca.log', 'w') as f:
    #     f.write(f"START PARSE {datetime.now()}\n")
    #     f.write(f"base_year: {base_year}\n")
    #     f.write(f"Full text snippet: {full_text[:1000]}\n")

    account_no = _extract_account_number(full_text)
    currency = _extract_currency(full_text) or 'IDR'
    
    # Extract statement month (day, month, year)
    st_day, st_month, st_year = _extract_statement_date(full_text)
    extracted_year = st_year or datetime.now().year
    current_year = base_year or extracted_year
    
    with open('debug_bca.log', 'a') as f:
        f.write(f"Statement date: {st_day}/{st_month}/{st_year}\n")
        f.write(f"Initial year set to: {current_year}\n")

    bank_code = 'BCA_CC'
    source_file = os.path.basename(pdf_path)

    rows = []
    
    for entry in transactions:
        raw_txn = entry.get('txn_date', '').strip()
        raw_post = entry.get('posting_date', '').strip()
        
        # Determine month number
        month_num = None
        if '/' in raw_txn:
             try:
                 month_num = int(raw_txn.split('/')[1])
             except (ValueError, IndexError):
                 pass
        
        # Robust Absolute Year Assignment:
        # If transaction month is greater than statement month + buffer, it implies prev year.
        # But if statement is Jan, and txn is Dec -> txn is year-1.
        # If statement is Dec, and txn is Nov -> txn is year.
        
        final_year = current_year
        if month_num is not None and st_month is not None:
            # Logic: If month_num is vastly larger than st_month (e.g. 11, 12 vs 1), likely prev year.
            # Using 6 months window rule often works best for CC.
            if month_num > st_month:
                # If statement is Jan (1), txn is Dec (12). 12 > 1. Year - 1.
                # If statement is Dec (12), txn is Nov (11). 11 < 12. Year same.
                final_year = current_year - 1
            else:
                final_year = current_year

        txn_iso = _convert_cc_date_absolute(raw_txn, final_year)
        post_iso = _convert_cc_date_absolute(raw_post, final_year)

        description = (entry.get('transaction_details') or '').strip()
        
        # Double check description for skip markers (sometimes they are part of subsequent lines)
        if any(marker in description.upper() for marker in skip_markers):
             # Try to clean description or skip if it's entirely a footer
             # For now, simplistic approach: if it STARTS with a marker, skip
             pass 

        amount_dec = _parse_decimal(entry.get('amount', ''))
        if amount_dec is None:
            # Maybe the amount was 0 or failed parse.
            # If description provided but amount missing, might be info text.
            # But let's verify if amount is essentially 0
            raw_amount = entry.get('amount', '').replace('.', '').replace(',', '')
            if raw_amount.isdigit() and int(raw_amount) == 0:
                 amount_value = '0.00'
                 db_cr = entry.get('db_cr', '')
            else:
                 amount_value = ''
                 db_cr = entry.get('db_cr', '').strip().upper()
        else:
            # Default to DB for positive amounts in BCA CC unless CR is found
            db_cr_raw = entry.get('db_cr') or ''
            amount_raw = entry.get('amount') or ''
            db_cr = db_cr_raw.strip().upper() or ('CR' if 'CR' in amount_raw.upper() else 'DB')
            amount_dec = abs(amount_dec)
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
    match = re.search(r'(\d{4}-\d{4}-\d{4}-\d{4})', text) # Standard 16 digit
    if not match:
        match = re.search(r'(\d{4}-\d{2}XX-XXXX-\d{4})', text) # Masked
    if match:
        return match.group(1)
    return ''


def _extract_currency(text: str) -> str:
    match = re.search(r'JUMLAH\s*\(\s*([A-Z]{2,3})\s*\)', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return ''


def _extract_statement_date(text: str) -> tuple[int | None, int | None, int | None]:
    """Extracts (day, month, year) from various statement date patterns."""
    
    # Pattern 1: TANGGAL REKENING : DD MMM YYYY (or YY)
    match = re.search(r'TANGGAL\s+REKENING\s*:\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{2,4})', text, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        m_str = match.group(2).upper()[:3]
        year_str = match.group(3)
        year = int(year_str) if len(year_str) == 4 else 2000 + int(year_str)
        
        month_str = MONTH_MAP.get(m_str)
        month = int(month_str) if month_str else None
        return day, month, year
    
    # Pattern 2: Numeric DD/MM/YYYY
    match = re.search(r'TANGGAL\s+REKENING\s*:\s*(\d{2})/(\d{2})/(\d{2,4})', text)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year_str = match.group(3)
        year = int(year_str) if len(year_str) == 4 else 2000 + int(year_str)
        return day, month, year
        
    # Pattern 3: Tgl. Rekening : DD MMM YYYY
    match = re.search(r'Tgl\.?\s*Rekening\s*[:]\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{2,4})', text, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        m_str = match.group(2).upper()[:3]
        year_str = match.group(3)
        year = int(year_str) if len(year_str) == 4 else 2000 + int(year_str)
        
        month_str = MONTH_MAP.get(m_str)
        month = int(month_str) if month_str else None
        return day, month, year

    # Fallback for just year
    years = re.findall(r'(?:19|20)\d{2}', text)
    if years:
        year = int(max(years))
        return None, None, year
        
    return None, None, int(datetime.now().year)


def _convert_cc_date_absolute(raw: str, year: int):
    """Converts DD/MM or DD-MMM to ISO date with fixed year."""
    if not raw:
        return ''
    raw = raw.strip()
    
    day = None
    month_int = None
    
    if '-' in raw:
        parts = raw.split('-', 1)
        if len(parts) >= 2:
            try:
                day = int(parts[0])
                month_str = parts[1][:3].upper() # Handle MMM-YY
                month_val = MONTH_MAP.get(month_str)
                if month_val:
                    month_int = int(month_val)
            except ValueError:
                pass
    elif '/' in raw:
        parts = raw.split('/', 1)
        if len(parts) == 2:
            try:
                day = int(parts[0])
                month_int = int(parts[1])
            except ValueError:
                pass

    if day is not None and month_int is not None:
        try:
            # Basic validation
            if not (1 <= day <= 31 and 1 <= month_int <= 12):
                return ''
            
            # Create date object to validate real date (e.g. Feb 30)
            target_date = datetime(year, month_int, day)
            date_iso = target_date.strftime('%Y-%m-%d')
            return f"{date_iso} 00:00:00"
        except ValueError:
            # Invalid date (e.g. Feb 30)
            return ''
            
    return ''


def _parse_decimal(value: str):
    if not value:
        return None
    # Remove Currency symbol matches if any
    cleaned = value.strip().replace('\u00a0', '').replace(' ', '').replace('CR', '').replace('DB', '')
    cleaned = re.sub(r'IDR|RP', '', cleaned, flags=re.IGNORECASE)
    
    if not cleaned:
        return None
        
    sign = -1 if cleaned.startswith('-') else 1
    cleaned = cleaned.lstrip('+-')
    
    # Determine format:
    # 1. 1.000,00 (Indonesian/German) -> dot is thousand, comma is decimal
    # 2. 1,000.00 (US/UK) -> comma is thousand, dot is decimal
    # 3. 1000 (Plain)
    
    commas = cleaned.count(',')
    dots = cleaned.count('.')
    
    try:
        if ',' in cleaned and '.' in cleaned:
            # Both present
            last_comma = cleaned.rfind(',')
            last_dot = cleaned.rfind('.')
            
            if last_comma > last_dot:
                # Comma is later, so comma is decimal (INDONESIAN)
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # Dot is later, so dot is decimal (US)
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # Only commas. Check if comma looks like decimal separator (2 digits after?)
            # or if multiple commas (thousands)
            if commas == 1 and len(cleaned) - cleaned.rfind(',') == 3:
                # likely decimal "100,00"
                cleaned = cleaned.replace(',', '.')
            else:
                # likely thousands "10,000" -> 10000
                cleaned = cleaned.replace(',', '')
        elif '.' in cleaned:
             # Only dots. 
             if dots == 1 and len(cleaned) - cleaned.rfind('.') == 3:
                 # likely decimal "100.00"
                 pass # Standard
             elif dots >= 1:
                 # likely thousands "1.000.000"
                 cleaned = cleaned.replace('.', '')
             
        dec = Decimal(cleaned)
        return dec * sign
    except (InvalidOperation, ValueError):
        return None


def _format_amount(dec: Decimal) -> str:
    if dec is None:
        return ''
    return format(dec, '.2f')
