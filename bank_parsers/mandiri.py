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

    try:
        lines = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
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

    df = pd.DataFrame(transactions)
    expected_columns = ['no', 'date', 'remarks', 'amount', 'balance', 'created_at']
    for column in expected_columns:
        if column not in df.columns:
            df[column] = ''

    return df[expected_columns]
