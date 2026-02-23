import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
import pdfplumber

from bank_parsers import mandiri

# e-Statement (Livin email) patterns
ES_DATE_LINE_PATTERN = re.compile(r'^\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})(?:\s+(.*))?$')
ES_NO_AMOUNT_BALANCE_PATTERN = re.compile(r'^\s*(\d+)\s+([+-]?\d[\d\.]*,\d{2})\s+([+-]?\d[\d\.]*,\d{2})\s*$')
ES_NO_WITH_DESC_AMOUNT_BALANCE_PATTERN = re.compile(
    r'^\s*(\d+)\s+(.+?)\s+([+-]?\d[\d\.]*,\d{2})\s+([+-]?\d[\d\.]*,\d{2})\s*$'
)
ES_TIME_LINE_PATTERN = re.compile(r'^(\d{2}:\d{2}:\d{2})\s+(WIB|WITA|WIT)\s*(.*)$', re.IGNORECASE)

ES_END_OF_TRANSACTIONS_KEYWORDS = (
    'ini adalah batas akhir transaksi anda',
    'batas akhir transaksi anda',
)

ES_TABLE_HEADER_PREFIXES = (
    'no tanggal',
    'no date',
    'no no',
)

ES_IGNORED_NON_TXN_KEYWORDS = (
    'e-statement',
    'plaza mandiri',
    'nama/name',
    'periode/period',
    'cabang/branch',
    'dicetak pada/issued on',
    'tabungan mandiri',
    'saldo awal/initial balance',
    'nomor rekening/account number',
    'mata uang/currency',
    'dana masuk/incoming transactions',
    'dana keluar/outgoing transactions',
    'saldo akhir/closing balance',
    'disclaimer',
    'pt bank mandiri',
    'mandiri call',
    'serta merupakan peserta penjamin',
    'lembaga penjamin simpanan',
    'this e-statement is an electronic document',
)

# Rekening Koran / Statement of Account patterns
RK_ACCOUNT_LINE_PATTERN = re.compile(r'(\d{3}-\d{2}-\d{7}-\d)')
RK_TRANSACTION_LINE_PATTERN = re.compile(
    r'^(?P<date>\d{2}/\d{2})\s+(?:\d{2}/\d{2}\s+)?(?P<details>.+?)\s+'
    r'(?P<amount>[\d,]+\.\d{2})\s+(?:(?P<debit_flag>D)\s+)?(?P<balance>[\d,]+\.\d{2})$'
)
RK_YEAR_PATTERN = re.compile(r'Periode\s*/\s*Period\s*:\s*\d{1,2}/\d{2}/(\d{2,4})', re.IGNORECASE)

RK_IGNORED_LINE_KEYWORDS = (
    'rekening koran / statement of account',
    'ringkasan / at a glance',
    'ringkasan akun / summary of accounts',
    'tabungan / savings',
    'kartu kredit / credit card',
    'account number product name',
    'no. rekening nama produk',
    'tanggal tanggal rincian transaksi',
    'transaction valuta transaction details',
    'date date',
    'transaksi valuta',
    'saldo awal / previous balance',
    'mutasi kredit / total of credit transactions',
    'mutasi debit / total of debit transactions',
    'saldo akhir / current balance',
    'hal page',
    'p age',
    'hubungi kami / contact us',
    'call center',
    'email : mandiricare',
    'website : https://www.bankmandiri.co.id',
)

MAX_DETAIL_LINES = 8


def _normalize_whitespace(value: str) -> str:
    return re.sub(r'\s+', ' ', (value or '').strip())


def _extract_account_number(text: str) -> str:
    match = re.search(r'Nomor\s+Rekening(?:/Account Number)?\s*:\s*([0-9\s]+)', text, re.IGNORECASE)
    if not match:
        return ''
    return re.sub(r'\D', '', match.group(1))


def _extract_currency(text: str) -> str:
    match = re.search(r'Mata\s+Uang(?:/Currency)?\s*:\s*([A-Z]{3})', text, re.IGNORECASE)
    if not match:
        # Rekening koran style
        if '(IDR)' in text or 'Indonesian Rupiah' in text:
            return 'IDR'
        return ''
    return match.group(1).upper()


def _to_iso_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, '%d %b %Y').strftime('%Y-%m-%d')
    except ValueError:
        return date_str


def _parse_decimal_id(value: str):
    if not value:
        return None
    cleaned = str(value).strip().replace('\u00a0', '').replace(' ', '')
    if not cleaned:
        return None

    sign = -1 if cleaned.startswith('-') else 1
    cleaned = cleaned.lstrip('+-')
    if not cleaned:
        return None

    try:
        # ID style: 1.234.567,89
        cleaned = cleaned.replace('.', '').replace(',', '.')
        dec = Decimal(cleaned)
    except InvalidOperation:
        return None
    return dec * sign


def _parse_decimal_us(value: str):
    if not value:
        return None
    cleaned = str(value).strip().replace('\u00a0', '').replace(' ', '')
    if not cleaned:
        return None
    try:
        # US style: 1,234,567.89
        dec = Decimal(cleaned.replace(',', ''))
    except InvalidOperation:
        return None
    return dec


def _format_decimal(dec: Decimal | None) -> str:
    if dec is None:
        return ''
    return format(abs(dec), '.2f')


def _add_detail_line(txn: dict | None, line: str) -> None:
    if txn is None:
        return
    snippet = _normalize_whitespace(line)
    if not snippet:
        return
    details = txn.setdefault('detail_lines', [])
    if len(details) < MAX_DETAIL_LINES:
        details.append(snippet)
    else:
        details[-1] = f"{details[-1]} {snippet}".strip()


def _finalize_es_transaction(txn: dict, conversion_timestamp: str):
    if not txn:
        return None

    iso_date = txn.get('iso_date') or ''
    if not iso_date:
        return None

    time_value = txn.get('time_value') or '00:00:00'
    try:
        time_value = datetime.strptime(time_value, '%H:%M:%S').strftime('%H:%M:%S')
    except ValueError:
        time_value = '00:00:00'

    amount_dec = _parse_decimal_id(txn.get('amount_text') or '')
    if amount_dec is None:
        return None

    balance_dec = _parse_decimal_id(txn.get('balance_text') or '')
    description = _normalize_whitespace(' '.join(txn.get('detail_lines', [])))

    return {
        'account_no': txn.get('account_no') or '',
        'txn_date': f"{iso_date} {time_value}",
        'description': description,
        'amount': _format_decimal(amount_dec),
        'db_cr': 'DB' if amount_dec < 0 else 'CR',
        'balance': _format_decimal(balance_dec),
        'created_at': txn.get('created_at') or conversion_timestamp
    }


def _extract_statement_year(full_text: str, source_file: str) -> int:
    match = RK_YEAR_PATTERN.search(full_text or '')
    if match:
        raw_year = match.group(1)
        year_int = int(raw_year)
        if year_int < 100:
            year_int += 2000
        if 2000 <= year_int <= 2100:
            return year_int

    filename_match = re.search(r'(20\d{2})', source_file or '')
    if filename_match:
        return int(filename_match.group(1))

    return datetime.now().year


def _is_rk_ignorable_line(normalized_lower: str) -> bool:
    if not normalized_lower:
        return True

    if any(keyword in normalized_lower for keyword in RK_IGNORED_LINE_KEYWORDS):
        return True

    if re.fullmatch(r'\d+\s+of\s+\d+', normalized_lower):
        return True

    return False


def _finalize_rk_transaction(txn: dict, statement_year: int, conversion_timestamp: str):
    if not txn:
        return None

    date_mmdd = txn.get('date') or ''
    date_match = re.fullmatch(r'(\d{2})/(\d{2})', date_mmdd)
    if not date_match:
        return None

    day = int(date_match.group(1))
    month = int(date_match.group(2))
    try:
        txn_date = datetime(statement_year, month, day).strftime('%Y-%m-%d 00:00:00')
    except ValueError:
        return None

    amount_dec = _parse_decimal_us(txn.get('amount_text') or '')
    balance_dec = _parse_decimal_us(txn.get('balance_text') or '')
    if amount_dec is None:
        return None

    is_debit = bool(txn.get('is_debit'))
    description = _normalize_whitespace(' '.join(txn.get('detail_lines', [])))

    return {
        'account_no': txn.get('account_no') or '',
        'txn_date': txn_date,
        'description': description,
        'amount': _format_decimal(amount_dec),
        'db_cr': 'DB' if is_debit else 'CR',
        'balance': _format_decimal(balance_dec),
        'created_at': txn.get('created_at') or conversion_timestamp
    }


def _parse_rekening_koran(lines: list[str], full_text: str, source_file: str, conversion_timestamp: str):
    statement_year = _extract_statement_year(full_text, source_file)
    fallback_account = _extract_account_number(full_text)
    transactions = []
    current_account_no = ''
    current_txn = None

    for raw_line in lines:
        line = (raw_line or '').strip()
        if not line:
            continue
        normalized_line = _normalize_whitespace(line)
        normalized_lower = normalized_line.lower()

        account_match = RK_ACCOUNT_LINE_PATTERN.search(normalized_line)
        if account_match and 'mandiri tabungan' in normalized_lower:
            current_account_no = re.sub(r'\D', '', account_match.group(1))
            continue

        if _is_rk_ignorable_line(normalized_lower):
            continue

        row_match = RK_TRANSACTION_LINE_PATTERN.match(normalized_line)
        if row_match:
            if current_txn:
                finalized = _finalize_rk_transaction(current_txn, statement_year, conversion_timestamp)
                if finalized:
                    transactions.append(finalized)

            current_txn = {
                'account_no': current_account_no or fallback_account,
                'date': row_match.group('date'),
                'detail_lines': [row_match.group('details')],
                'amount_text': row_match.group('amount'),
                'balance_text': row_match.group('balance'),
                'is_debit': bool(row_match.group('debit_flag')),
                'created_at': conversion_timestamp
            }
            continue

        # Continuation detail line for the latest transaction
        if current_txn:
            _add_detail_line(current_txn, normalized_line)

    if current_txn:
        finalized = _finalize_rk_transaction(current_txn, statement_year, conversion_timestamp)
        if finalized:
            transactions.append(finalized)

    return transactions


def _parse_e_statement(lines: list[str], account_no: str, conversion_timestamp: str):
    transactions = []
    in_table = False
    current = None
    pending_details = []

    for raw_line in lines:
        line = (raw_line or '').strip()
        if not line:
            continue

        normalized_line = _normalize_whitespace(line).lower()

        if any(keyword in normalized_line for keyword in ES_END_OF_TRANSACTIONS_KEYWORDS):
            if current:
                finalized = _finalize_es_transaction(current, conversion_timestamp)
                if finalized:
                    transactions.append(finalized)
            current = None
            break

        if any(normalized_line.startswith(prefix) for prefix in ES_TABLE_HEADER_PREFIXES):
            in_table = True
            continue

        is_page_counter = bool(
            re.fullmatch(r'\d+\s+dari\s+\d+', normalized_line)
            or re.fullmatch(r'\d+\s+of\s+\d+', normalized_line)
        )
        if is_page_counter or any(keyword in normalized_line for keyword in ES_IGNORED_NON_TXN_KEYWORDS):
            continue

        date_match = ES_DATE_LINE_PATTERN.match(line)
        no_amount_balance_match = ES_NO_AMOUNT_BALANCE_PATTERN.match(line)
        no_with_desc_match = ES_NO_WITH_DESC_AMOUNT_BALANCE_PATTERN.match(line)

        # Some PDFs don't expose table header line cleanly
        if not in_table and (date_match or no_amount_balance_match or no_with_desc_match):
            in_table = True

        if not in_table:
            continue

        if date_match:
            if current and current.get('amount_text'):
                finalized = _finalize_es_transaction(current, conversion_timestamp)
                if finalized:
                    transactions.append(finalized)
                current = None

            if current is None:
                current = {
                    'account_no': account_no,
                    'iso_date': _to_iso_date(date_match.group(1)),
                    'detail_lines': pending_details[:],
                    'time_value': None,
                    'amount_text': '',
                    'balance_text': '',
                    'created_at': conversion_timestamp
                }
                pending_details.clear()
            else:
                current['iso_date'] = _to_iso_date(date_match.group(1))

            remainder = (date_match.group(2) or '').strip()
            if remainder:
                _add_detail_line(current, remainder)
            continue

        if no_with_desc_match:
            if current is None:
                current = {
                    'account_no': account_no,
                    'iso_date': '',
                    'detail_lines': pending_details[:],
                    'time_value': None,
                    'amount_text': '',
                    'balance_text': '',
                    'created_at': conversion_timestamp
                }
                pending_details.clear()

            _add_detail_line(current, no_with_desc_match.group(2))
            current['amount_text'] = no_with_desc_match.group(3)
            current['balance_text'] = no_with_desc_match.group(4)
            continue

        if no_amount_balance_match:
            if current is None:
                current = {
                    'account_no': account_no,
                    'iso_date': '',
                    'detail_lines': pending_details[:],
                    'time_value': None,
                    'amount_text': '',
                    'balance_text': '',
                    'created_at': conversion_timestamp
                }
                pending_details.clear()

            current['amount_text'] = no_amount_balance_match.group(2)
            current['balance_text'] = no_amount_balance_match.group(3)
            continue

        time_match = ES_TIME_LINE_PATTERN.match(line)
        if time_match:
            if current is None:
                pending_details.append(line)
                continue

            current['time_value'] = time_match.group(1)
            remainder = (time_match.group(3) or '').strip()
            if remainder:
                _add_detail_line(current, remainder)
            continue

        if current is None or not current.get('iso_date'):
            pending_details.append(line)
            continue

        _add_detail_line(current, line)

    if current:
        finalized = _finalize_es_transaction(current, conversion_timestamp)
        if finalized:
            transactions.append(finalized)

    return transactions


def parse_statement(pdf_path):
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError('Invalid file format. Please provide a PDF file')

    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    source_file = os.path.basename(pdf_path)

    try:
        lines = []
        full_text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ''
                if text:
                    full_text_parts.append(text)
                    lines.extend([ln.rstrip() for ln in text.split('\n')])

        full_text = '\n'.join(full_text_parts)
        full_text_lower = full_text.lower()

        # First path: Rekening Koran / Statement of Account format
        if 'rekening koran / statement of account' in full_text_lower:
            rk_transactions = _parse_rekening_koran(lines, full_text, source_file, conversion_timestamp)
            if rk_transactions:
                rows = []
                currency = _extract_currency(full_text) or 'IDR'
                for txn in rk_transactions:
                    txn_date = txn.get('txn_date', '')
                    rows.append({
                        'bank_code': 'MANDIRI',
                        'account_no': txn.get('account_no', ''),
                        'txn_date': txn_date,
                        'posting_date': txn_date,
                        'description': txn.get('description', ''),
                        'amount': txn.get('amount', ''),
                        'db_cr': txn.get('db_cr', ''),
                        'balance': txn.get('balance', ''),
                        'currency': currency,
                        'created_at': txn.get('created_at', conversion_timestamp),
                        'source_file': source_file
                    })
                columns = [
                    'bank_code', 'account_no', 'txn_date', 'posting_date', 'description',
                    'amount', 'db_cr', 'balance', 'currency', 'created_at', 'source_file'
                ]
                return pd.DataFrame(rows, columns=columns)

        # Second path: e-Statement email style
        account_no = _extract_account_number(full_text)
        es_transactions = _parse_e_statement(lines, account_no, conversion_timestamp)
        if es_transactions:
            rows = []
            currency = _extract_currency(full_text) or 'IDR'
            for txn in es_transactions:
                txn_date = txn.get('txn_date', '')
                rows.append({
                    'bank_code': 'MANDIRI',
                    'account_no': txn.get('account_no', ''),
                    'txn_date': txn_date,
                    'posting_date': txn_date,
                    'description': txn.get('description', ''),
                    'amount': txn.get('amount', ''),
                    'db_cr': txn.get('db_cr', ''),
                    'balance': txn.get('balance', ''),
                    'currency': currency,
                    'created_at': txn.get('created_at', conversion_timestamp),
                    'source_file': source_file
                })
            columns = [
                'bank_code', 'account_no', 'txn_date', 'posting_date', 'description',
                'amount', 'db_cr', 'balance', 'currency', 'created_at', 'source_file'
            ]
            return pd.DataFrame(rows, columns=columns)

    except Exception as e:
        raise ValueError(f'Error processing Mandiri email PDF: {str(e)}')

    # Final fallback for unseen layouts
    try:
        return mandiri.parse_statement(pdf_path)
    except Exception:
        raise ValueError('No transaction data found in Mandiri email PDF.')

