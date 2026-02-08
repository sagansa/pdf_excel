import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
import pdfplumber

DATE_PATTERN = re.compile(r'^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$')
DATE_LINE_PATTERN = re.compile(r'^\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})(.*)$')
TIME_LINE_PATTERN = re.compile(r'^(\d{2}:\d{2}:\d{2})\s+(WIB|WITA|WIT)\s*(.*)$', re.IGNORECASE)
AMOUNT_PATTERN = re.compile(r'[+-]?\d[\d\.]*,\d{2}')
FOOTER_KEYWORDS = [
    'pt bank mandiri',
    'mandiri call',
    'disclaimer',
    'batas akhir transaksi',
    'ini adalah batas akhir'
]

MAX_DETAIL_LINES = 4

def _to_iso_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, '%d %b %Y').strftime('%Y-%m-%d')
    except ValueError:
        return date_str


def _add_detail_line(transaction: dict, snippet: str) -> None:
    if not snippet:
        return

    snippet = snippet.strip()
    if not snippet:
        return

    detail_lines = transaction.setdefault('detail_lines', [])
    if len(detail_lines) < MAX_DETAIL_LINES:
        detail_lines.append(snippet)
    else:
        detail_lines[-1] = f"{detail_lines[-1]} {snippet}".strip()


def _finalize_transaction(transaction: dict) -> dict:
    if not transaction:
        return None

    date_lines = transaction.get('date_lines', [])
    iso_date = date_lines[0] if date_lines else ''
    time_value = transaction.get('time_value') or ''
    if iso_date and time_value:
        try:
            parsed_time = datetime.strptime(time_value, '%H:%M:%S')
            time_value = parsed_time.strftime('%H:%M:%S')
        except ValueError:
            time_value = time_value
        date_value = f"{iso_date} {time_value}"
    elif iso_date:
        date_value = f"{iso_date} 00:00:00"
    else:
        date_value = ''

    remarks = ' '.join(transaction.get('detail_lines', [])[:MAX_DETAIL_LINES]).strip()

    amount_str = (transaction.get('amount') or '').strip()
    balance_str = (transaction.get('balance') or '').strip()

    def _clean_amount(value: str) -> str:
        if not value:
            return ''
        try:
            dec = Decimal(value.replace('.', '').replace(',', '.'))
        except InvalidOperation:
            return value
        if dec == dec.to_integral() or abs(dec - dec.to_integral()) < Decimal('0.0001'):
            return str(int(dec))
        return format(dec, 'f')

    def _clean_balance(value: str) -> str:
        if not value:
            return ''
        try:
            dec = Decimal(value.replace('.', '').replace(',', '.'))
        except InvalidOperation:
            return value
        return f"{dec:.2f}".replace('.', ',')

    amount = _clean_amount(amount_str)
    balance = _clean_balance(balance_str)

    if not transaction.get('no') and not iso_date and not amount and not remarks:
        return None

    return {
        'no': transaction.get('no', ''),
        'date': date_value,
        'remarks': remarks,
        'amount': amount,
        'balance': balance,
        'created_at': transaction.get('created_at')
    }

def parse_statement(pdf_path):
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")

    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    transactions = []
    full_text_parts = []

    try:
        lines = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text_parts.append(text)
                    lines.extend([ln.rstrip() for ln in text.split('\n')])

        in_table = False
        current_transaction = None
        pending_details = []

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            lower_line = line.lower()
            footer_hit = any(keyword in lower_line for keyword in FOOTER_KEYWORDS)
            if footer_hit and in_table:
                break
            if footer_hit and not in_table:
                continue

            normalized_line = ' '.join(line.split()).lower()
            header_detected = (
                normalized_line.startswith('no no')
                or normalized_line.startswith('no tanggal')
                or normalized_line.startswith('no date')
            )

            if not in_table:
                if header_detected:
                    in_table = True
                continue

            if current_transaction is None:
                if re.fullmatch(r'\d+', line):
                    current_transaction = {
                        'no': line,
                        'date_lines': [],
                        'detail_lines': pending_details[:],
                        'amount': '',
                        'balance': '',
                        'time_value': None,
                        'created_at': conversion_timestamp
                    }
                    pending_details.clear()
                elif DATE_LINE_PATTERN.match(line):
                    current_transaction = {
                        'no': '',
                        'date_lines': [],
                        'detail_lines': pending_details[:],
                        'amount': '',
                        'balance': '',
                        'time_value': None,
                        'created_at': conversion_timestamp
                    }
                    pending_details.clear()
                    match = DATE_LINE_PATTERN.match(line)
                    current_transaction['date_lines'].append(_to_iso_date(match.group(1)))
                    remainder = match.group(2).strip()
                    if remainder:
                        _add_detail_line(current_transaction, remainder)
                else:
                    pending_details.append(line)
                continue

            if re.fullmatch(r'\d+', line):
                finalized = _finalize_transaction(current_transaction)
                if finalized:
                    transactions.append(finalized)
                current_transaction = {
                    'no': line,
                    'date_lines': [],
                    'detail_lines': pending_details[:],
                    'amount': '',
                    'balance': '',
                    'time_value': None,
                    'created_at': conversion_timestamp
                }
                pending_details.clear()
                continue

            date_line_match = DATE_LINE_PATTERN.match(line)
            if date_line_match:
                if current_transaction and current_transaction['date_lines']:
                    finalized = _finalize_transaction(current_transaction)
                    if finalized:
                        transactions.append(finalized)
                    current_transaction = {
                        'no': '',
                        'date_lines': [],
                        'detail_lines': [],
                        'amount': '',
                        'balance': '',
                        'time_value': None,
                        'created_at': conversion_timestamp
                    }
                elif current_transaction is None:
                    current_transaction = {
                        'no': '',
                        'date_lines': [],
                        'detail_lines': pending_details[:],
                        'amount': '',
                        'balance': '',
                        'time_value': None,
                        'created_at': conversion_timestamp
                    }
                    pending_details.clear()
                current_transaction['date_lines'].append(_to_iso_date(date_line_match.group(1)))
                remainder = date_line_match.group(2).strip()
                if remainder:
                    _add_detail_line(current_transaction, remainder)
                continue

            if (
                current_transaction
                and current_transaction['amount']
                and current_transaction['date_lines']
                and not any(char.isdigit() for char in line)
            ):
                pending_details.append(line)
                finalized = _finalize_transaction(current_transaction)
                if finalized:
                    transactions.append(finalized)
                current_transaction = None
                continue

            if current_transaction is None:
                continue

            time_match = TIME_LINE_PATTERN.match(line)
            if time_match:
                current_transaction['time_value'] = time_match.group(1)
                remainder = time_match.group(3).strip()
                if remainder:
                    _add_detail_line(current_transaction, remainder)
                continue

            amounts = AMOUNT_PATTERN.findall(line)
            if amounts:
                amount_value = amounts[0].strip()
                balance_value = amounts[-1].strip()

                current_transaction['amount'] = amount_value
                current_transaction['balance'] = balance_value

                cleaned_line = line
                for candidate in amounts:
                    cleaned_line = cleaned_line.replace(candidate, '')
                cleaned_line = cleaned_line.replace('CR', '').strip()
                _add_detail_line(current_transaction, cleaned_line)
                continue

            _add_detail_line(current_transaction, line)

        if current_transaction:
            finalized = _finalize_transaction(current_transaction)
            if finalized:
                transactions.append(finalized)

    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")

    if not transactions:
        raise ValueError("No transaction data found in the PDF. Please ensure this is a valid Mandiri statement")

    full_text = '\n'.join(full_text_parts)
    account_no = _extract_account_number(full_text)
    currency = _extract_currency(full_text) or 'IDR'
    bank_code = 'MANDIRI'
    source_file = os.path.basename(pdf_path)

    standard_rows = []

    for entry in transactions:
        raw_date = entry.get('date', '').strip()
        txn_datetime = ''
        if raw_date:
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    parsed_dt = datetime.strptime(raw_date, fmt)
                    if fmt == '%Y-%m-%d':
                        parsed_dt = parsed_dt.replace(hour=0, minute=0, second=0)
                    txn_datetime = parsed_dt.strftime('%Y-%m-%d %H:%M:%S')
                    break
                except ValueError:
                    continue

        amount_dec = _parse_decimal(entry.get('amount', ''))
        if amount_dec is None:
            amount_value = ''
            db_cr = ''
        else:
            db_cr = 'DB' if amount_dec < 0 else 'CR'
            amount_value = _format_decimal(amount_dec)

        balance_dec = _parse_decimal(entry.get('balance', ''))
        balance_value = _format_decimal(balance_dec) if balance_dec is not None else ''

        standard_rows.append({
            'bank_code': bank_code,
            'account_no': account_no,
            'txn_date': txn_datetime,
            'posting_date': txn_datetime,
            'description': entry.get('remarks', '').strip(),
            'amount': amount_value,
            'db_cr': db_cr,
            'balance': balance_value,
            'currency': currency,
            'created_at': entry.get('created_at', conversion_timestamp),
            'source_file': source_file
        })

    columns = ['bank_code', 'account_no', 'txn_date', 'posting_date', 'description', 'amount', 'db_cr', 'balance', 'currency', 'created_at', 'source_file']

    return pd.DataFrame(standard_rows, columns=columns)


def _extract_account_number(text: str) -> str:
    match = re.search(r'Nomor\s+Rekening(?:/Account Number)?\s*:\s*([0-9\s]+)', text, re.IGNORECASE)
    if match:
        return re.sub(r'\D', '', match.group(1))
    return ''


def _extract_currency(text: str) -> str:
    match = re.search(r'Mata\s+Uang(?:/Currency)?\s*:\s*([A-Z]{3})', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return ''


def _parse_decimal(value: str):
    if not value:
        return None
    cleaned = value.strip().replace('\u00a0', '').replace(' ', '')
    if not cleaned:
        return None
    # Detect sign for DB/CR determination
    sign = -1 if cleaned.startswith('-') else 1
    cleaned = cleaned.lstrip('+-')
    if not cleaned:
        return None
    
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
            if len(cleaned.split('.')[-1]) == 2:
                # 1234.56
                pass 
            else:
                # 1.234.567
                cleaned = cleaned.replace('.', '')
        
        dec = Decimal(cleaned)
    except InvalidOperation:
        return None
    return dec * sign  # Return with sign for DB/CR detection


def _format_decimal(dec: Decimal | None) -> str:
    if dec is None:
        return ''
    return format(abs(dec), '.2f')  # Always format as positive
