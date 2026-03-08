import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
import pdfplumber

# Month mapping for Indonesian months
MONTH_MAP = {
    'januari': '01', 'februari': '02', 'maret': '03', 'april': '04',
    'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08',
    'september': '09', 'oktober': '10', 'november': '11', 'desember': '12'
}

# Section headers to identify different saku types
SECTION_HEADERS = [
    'SAKU UTAMA',
    'SAKU NABUNG',
    'SAKU TRANSAKSI',
    'BOOSTER'
]


def parse_statement(pdf_path, password=None):
    """
    Parse SAQU PDF bank statement.
    
    SAQU has multiple sections (saku) with different account numbers.
    Each section has transactions in format:
    Tanggal Transaksi | Tipe | Deskripsi Transaksi | Jumlah
    
    Args:
        pdf_path: Path to PDF file
        password: Password for encrypted PDF (optional)
    """
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")

    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    transactions = []
    
    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            full_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
            
            combined_text = '\n'.join(full_text)
            
            # Extract transactions from all sections
            transactions = _extract_transactions(combined_text, conversion_timestamp)
    
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    if not transactions:
        raise ValueError("No transaction data found in the PDF. Please ensure this is a valid SAQU statement")
    
    source_file = os.path.basename(pdf_path)
    
    # Convert to DataFrame
    standard_rows = []
    for txn in transactions:
        standard_rows.append({
            'bank_code': 'SAQU',
            'account_no': txn.get('account_no', ''),
            'txn_date': txn.get('txn_date', ''),
            'posting_date': txn.get('txn_date', ''),
            'description': txn.get('description', ''),
            'amount': txn.get('amount', ''),
            'db_cr': txn.get('db_cr', ''),
            'balance': '',  # SAQU doesn't show running balance per transaction
            'currency': 'IDR',
            'created_at': conversion_timestamp,
            'source_file': source_file
        })
    
    columns = ['bank_code', 'account_no', 'txn_date', 'posting_date', 'description', 
               'amount', 'db_cr', 'balance', 'currency', 'created_at', 'source_file']
    
    return pd.DataFrame(standard_rows, columns=columns)


def _extract_transactions(text, conversion_timestamp):
    """Extract transactions from SAQU statement text."""
    transactions = []
    lines = text.split('\n')
    
    current_section = None
    current_account = None
    in_transaction_section = False
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for section headers
        for header in SECTION_HEADERS:
            if header in line:
                current_section = header
                current_account = None
                in_transaction_section = False
                break
        
        # Extract account number
        if 'Nomor rekening' in line or 'No rekening' in line:
            match = re.search(r':\s*(\d+)', line)
            if match:
                current_account = match.group(1)
        
        # Check if we're in transaction section (after "Tanggal Transaksi" header)
        if 'Tanggal Transaksi' in line and 'Tipe' in line:
            in_transaction_section = True
            i += 1
            continue
        
        # Parse transaction lines
        if in_transaction_section and current_account:
            # Check for end of section markers
            if any(keyword in line.lower() for keyword in ['dana akhir', 'disclaimer', 'halaman']):
                in_transaction_section = False
                i += 1
                continue
            
            # Try to parse transaction line
            # Format: DD Month YYYY | Tipe | Description | Amount
            txn = _parse_transaction_line(line, current_account, conversion_timestamp)
            if txn:
                transactions.append(txn)
        
        i += 1
    
    return transactions


def _parse_transaction_line(line, account_no, conversion_timestamp):
    """Parse a single transaction line."""
    if not line or len(line) < 10:
        return None
    
    # Try to match date pattern at start: DD Month YYYY
    date_match = re.match(r'^(\d{1,2}\s+\w+\s+\d{4})\s+(.+)$', line)
    if not date_match:
        return None
    
    date_str = date_match.group(1)
    remainder = date_match.group(2).strip()
    
    # Parse date
    txn_date = _parse_date(date_str)
    if not txn_date:
        return None
    
    # Extract amount (last part with Rp)
    # Amount can be: Rp130.650 or +Rp53
    amount_match = re.search(r'([+]?Rp[\d.,]+)$', remainder)
    if not amount_match:
        return None
    
    amount_str = amount_match.group(1)
    description = remainder[:amount_match.start()].strip()
    
    # Parse amount and determine DB/CR
    is_credit = amount_str.startswith('+')
    amount_clean = amount_str.replace('+', '').replace('Rp', '').replace('.', '').replace(',', '.')
    
    try:
        amount_decimal = Decimal(amount_clean)
        amount_value = format(abs(amount_decimal), '.2f')
        db_cr = 'CR' if is_credit else 'DB'
    except (InvalidOperation, ValueError):
        return None
    
    return {
        'account_no': account_no,
        'txn_date': txn_date,
        'description': description,
        'amount': amount_value,
        'db_cr': db_cr,
        'created_at': conversion_timestamp
    }


def _parse_date(date_str):
    """Parse Indonesian date format: DD Month YYYY."""
    try:
        # Split date string
        parts = date_str.strip().split()
        if len(parts) != 3:
            return ''
        
        day = parts[0].zfill(2)
        month_name = parts[1].lower()
        year = parts[2]
        
        # Get month number
        month = MONTH_MAP.get(month_name)
        if not month:
            return ''
        
        # Format as YYYY-MM-DD HH:MM:SS
        return f"{year}-{month}-{day} 00:00:00"
    except Exception:
        return ''
