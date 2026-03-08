import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
import pdfplumber


def parse_statement(pdf_path):
    """
    Parse BLU BY BCA PDF bank statement.
    
    Format:
    - Single page statement
    - Columns: Tanggal & Jam | Keterangan | Nominal | Sisa Saldo
    - Bilingual (Indonesian/English)
    - Amount format: Rp0,00 (comma as decimal separator)
    """
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")

    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    transactions = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                raise ValueError("PDF has no pages")
            
            # Extract text from first page
            text = pdf.pages[0].extract_text()
            if not text:
                raise ValueError("Could not extract text from PDF")
            
            # Extract account number and transactions
            account_no = _extract_account_number(text)
            transactions = _extract_transactions(text, account_no, conversion_timestamp)
    
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    # BLU might have no transactions (as in sample)
    if not transactions:
        # Return empty DataFrame with correct structure
        print("Warning: No transactions found in BLU statement")
    
    source_file = os.path.basename(pdf_path)
    
    # Convert to DataFrame
    standard_rows = []
    for txn in transactions:
        standard_rows.append({
            'bank_code': 'BLU',
            'account_no': account_no,
            'txn_date': txn.get('txn_date', ''),
            'posting_date': txn.get('txn_date', ''),
            'description': txn.get('description', ''),
            'amount': txn.get('amount', ''),
            'db_cr': txn.get('db_cr', ''),
            'balance': txn.get('balance', ''),
            'currency': 'IDR',
            'created_at': conversion_timestamp,
            'source_file': source_file
        })
    
    columns = ['bank_code', 'account_no', 'txn_date', 'posting_date', 'description', 
               'amount', 'db_cr', 'balance', 'currency', 'created_at', 'source_file']
    
    return pd.DataFrame(standard_rows, columns=columns)


def _extract_account_number(text):
    """Extract account number from BLU statement."""
    # Look for "Rekening / Account" followed by account type
    # In BLU, the account is "bluAccount" which is the product name
    # We'll use a placeholder or extract from filename if available
    match = re.search(r'Rekening\s*/\s*Account\s*\n\s*(\w+)', text)
    if match:
        return match.group(1)
    return 'bluAccount'


def _extract_transactions(text, account_no, conversion_timestamp):
    """Extract transactions from BLU statement text."""
    transactions = []
    lines = text.split('\n')
    
    # Check for "no transactions" message
    if 'Tidak ada transaksi' in text or 'No transactions' in text:
        return []
    
    # Find transaction table section
    # Look for header: "Tanggal & Jam" ... "Keterangan" ... "Nominal" ... "Sisa Saldo"
    in_transaction_section = False
    
    for i, line in enumerate(lines):
        # Check for table header
        if 'Tanggal & Jam' in line and 'Keterangan' in line:
            in_transaction_section = True
            continue
        
        # Check for end of transactions
        if in_transaction_section and ('Disclaimer' in line or 'BCA Digital berizin' in line):
            break
        
        # Parse transaction lines
        if in_transaction_section:
            txn = _parse_transaction_line(line, account_no, conversion_timestamp)
            if txn:
                transactions.append(txn)
    
    return transactions


def _parse_transaction_line(line, account_no, conversion_timestamp):
    """Parse a single transaction line from BLU statement."""
    if not line or len(line) < 10:
        return None
    
    # Skip header lines and empty lines
    if 'Date & Time' in line or 'Detail Transaksi' in line:
        return None
    
    # BLU format is more structured, might need table extraction
    # For now, try to parse text-based format
    # Expected: Date Time | Description | Amount | Balance
    
    # Try to match date pattern: DD/MM/YYYY HH:MM or similar
    date_match = re.match(r'^(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})\s+(.+)$', line)
    if not date_match:
        return None
    
    date_str = date_match.group(1)
    remainder = date_match.group(2).strip()
    
    # Parse date
    txn_date = _parse_date(date_str)
    if not txn_date:
        return None
    
    # Extract amounts (Nominal and Sisa Saldo)
    # Format: Rp1.234,56
    amounts = re.findall(r'Rp[\d.,]+', remainder)
    if len(amounts) < 2:
        return None
    
    amount_str = amounts[0]  # Nominal
    balance_str = amounts[1]  # Sisa Saldo
    
    # Description is between date and first amount
    desc_end = remainder.find(amount_str)
    description = remainder[:desc_end].strip()
    
    # Parse amounts
    amount_value = _parse_amount(amount_str)
    balance_value = _parse_amount(balance_str)
    
    # Determine DB/CR from context (if amount is negative or from description)
    # For now, assume debit unless description indicates credit
    db_cr = 'CR' if any(word in description.lower() for word in ['terima', 'masuk', 'kredit', 'topup']) else 'DB'
    
    return {
        'account_no': account_no,
        'txn_date': txn_date,
        'description': description,
        'amount': amount_value,
        'db_cr': db_cr,
        'balance': balance_value,
        'created_at': conversion_timestamp
    }


def _parse_date(date_str):
    """Parse BLU date format: DD/MM/YYYY HH:MM."""
    try:
        dt = datetime.strptime(date_str.strip(), '%d/%m/%Y %H:%M')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''


def _parse_amount(amount_str):
    """Parse BLU amount format: Rp1.234,56."""
    try:
        # Remove Rp prefix
        cleaned = amount_str.replace('Rp', '').strip()
        # Remove thousands separator (.)
        cleaned = cleaned.replace('.', '')
        # Replace decimal separator (,) with period
        cleaned = cleaned.replace(',', '.')
        
        amount_decimal = Decimal(cleaned)
        return format(abs(amount_decimal), '.2f')
    except (InvalidOperation, ValueError):
        return '0.00'
