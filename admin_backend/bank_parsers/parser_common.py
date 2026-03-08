import os
from datetime import datetime
from decimal import Decimal, InvalidOperation


def parser_debug_enabled():
    return str(os.environ.get('BANK_PARSER_DEBUG_LOGS', '')).strip().lower() in {
        '1',
        'true',
        'yes',
        'y',
        'on',
    }


def reset_debug_log(filename, *lines):
    if not parser_debug_enabled():
        return
    with open(filename, 'w', encoding='utf-8') as handle:
        for line in lines:
            handle.write(f"{line}\n")


def append_debug_log(filename, *lines):
    if not parser_debug_enabled():
        return
    with open(filename, 'a', encoding='utf-8') as handle:
        for line in lines:
            handle.write(f"{line}\n")


def ensure_pdf_file(pdf_path):
    if not os.path.exists(pdf_path):
        raise ValueError("PDF file not found")

    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")


def ensure_csv_file(csv_path):
    if not os.path.exists(csv_path):
        raise ValueError("CSV file not found")

    if not csv_path.lower().endswith('.csv'):
        raise ValueError("Invalid file format. Please provide a CSV file")


def validate_pdf_document(pdf, statement_name):
    if not pdf.pages:
        raise ValueError(
            f"PDF file is empty or corrupted. Please ensure the file is a valid {statement_name}"
        )

    try:
        _ = pdf.metadata
        for page in pdf.pages:
            if not hasattr(page, 'extract_words'):
                raise ValueError(
                    "PDF file appears to be corrupted. Unable to extract content from pages."
                )
    # pdfplumber/pdfminer can raise different low-level exceptions while probing metadata/pages.
    except Exception as exc:
        raise ValueError(f"PDF file validation failed. The file may be corrupted: {exc}")


def collect_page_text(pdf):
    full_text_parts = []
    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
            full_text_parts.append(page_text)
    return full_text_parts


def conversion_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def source_file_name(path):
    return os.path.basename(path)


def parse_decimal_amount(value):
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    cleaned = str(value)
    if not cleaned:
        return None

    cleaned = (
        cleaned.strip()
        .replace('\u00a0', '')
        .replace(' ', '')
        .replace('CR', '')
        .replace('DB', '')
    )
    cleaned = cleaned.replace('Rp', '').replace('rp', '')
    cleaned = cleaned.replace('IDR', '').replace('idr', '')

    if not cleaned:
        return None

    sign = -1 if cleaned.startswith('-') else 1
    cleaned = cleaned.lstrip('+-')

    commas = cleaned.count(',')
    dots = cleaned.count('.')

    try:
        if ',' in cleaned and '.' in cleaned:
            if cleaned.rfind(',') > cleaned.rfind('.'):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            if commas == 1 and len(cleaned) - cleaned.rfind(',') == 3:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif '.' in cleaned:
            if not (dots == 1 and len(cleaned) - cleaned.rfind('.') == 3):
                cleaned = cleaned.replace('.', '')

        return Decimal(cleaned) * sign
    except (InvalidOperation, ValueError):
        return None


def parse_decimal_id_amount(value):
    if value is None:
        return None

    cleaned = str(value).strip().replace('\u00a0', '').replace(' ', '')
    if not cleaned:
        return None

    sign = -1 if cleaned.startswith('-') else 1
    cleaned = cleaned.lstrip('+-')
    if not cleaned:
        return None

    try:
        cleaned = cleaned.replace('.', '').replace(',', '.')
        return Decimal(cleaned) * sign
    except (InvalidOperation, ValueError):
        return None


def parse_decimal_us_amount(value):
    if value is None:
        return None

    cleaned = str(value).strip().replace('\u00a0', '').replace(' ', '')
    if not cleaned:
        return None

    try:
        return Decimal(cleaned.replace(',', ''))
    except (InvalidOperation, ValueError):
        return None


def format_amount(value):
    if value is None:
        return ''
    return format(value, '.2f')
