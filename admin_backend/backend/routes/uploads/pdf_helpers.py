import os
import re

import pandas as pd
import PyPDF2
from werkzeug.utils import secure_filename

from backend.utils.date_helpers import normalize_date_columns, standardize_statement_dates
from backend.utils.pdf_year_utils import infer_year_from_filename, infer_year_from_pdf
from bank_parsers import bca, bca_cc, blu, bri, dbs, mandiri, mandiri_cc, mandiri_email, saqu
from backend.utils.pdf_unlock import unlock_pdf

try:
    from PyPDF2.errors import PdfReadError
except (ImportError, AttributeError):
    try:
        from PyPDF2.utils import PdfReadError
    except (ImportError, AttributeError):
        class PdfReadError(Exception):
            pass


def normalize_company_id(value):
    if value is None:
        return None
    candidate = str(value).strip()
    if not candidate or candidate.lower() in {'none', 'null'}:
        return None
    match = re.search(
        r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})',
        candidate,
    )
    if match:
        return match.group(1)
    return None


def save_uploaded_file(upload_folder, file_storage):
    filename = secure_filename(file_storage.filename or '')
    file_path = os.path.join(upload_folder, filename)
    file_storage.save(file_path)
    return filename, file_path


def detect_pdf_password_requirement(pdf_path):
    with open(pdf_path, 'rb') as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        is_protected = reader.is_encrypted
        if not is_protected:
            return False
        try:
            result = reader.decrypt('')
            return result in (0, False)
        except Exception:
            return True


def resolve_pdf_access_path(original_pdf_path, password=None):
    requires_password = False
    pdf_path = original_pdf_path

    with open(original_pdf_path, 'rb') as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        if reader.is_encrypted:
            if not password:
                try:
                    result = reader.decrypt('')
                except Exception:
                    result = 0
                if result not in (0, False):
                    try:
                        pdf_path = unlock_pdf(original_pdf_path, '')
                    except PdfReadError:
                        requires_password = True
                else:
                    requires_password = True
            else:
                pdf_path = unlock_pdf(original_pdf_path, password)

    return pdf_path, requires_password


def infer_statement_year(file_path, original_file_path, is_pdf):
    if is_pdf:
        return infer_year_from_pdf(file_path) or infer_year_from_filename(original_file_path)
    return infer_year_from_filename(original_file_path)


def parse_statement(bank_key, file_path, inferred_year=None, password=None, is_csv=False):
    if bank_key == 'bri' and not is_csv:
        raise ValueError('BRI statements must be in CSV format.')
    if bank_key != 'bri' and is_csv:
        raise ValueError('CSV files are only supported for BRI bank.')

    if bank_key == 'mandiri':
        return mandiri.parse_statement(file_path)
    if bank_key == 'mandiri_email':
        return mandiri_email.parse_statement(file_path)
    if bank_key == 'dbs':
        return dbs.parse_statement(file_path, target_year=inferred_year)
    if bank_key == 'ccbca':
        return bca_cc.parse_statement(file_path, inferred_year)
    if bank_key == 'ccmandiri':
        return mandiri_cc.parse_statement(file_path, password=password)
    if bank_key == 'bri':
        return bri.parse_statement(file_path)
    if bank_key == 'saqu':
        return saqu.parse_statement(file_path, password=password)
    if bank_key == 'blu':
        return blu.parse_statement(file_path)

    df = bca.parse_statement(file_path)
    return standardize_statement_dates(df, 'Tanggal', 'dd/mm', inferred_year)


def normalize_statement_dataframe(df, bank_key, inferred_year, company_id, original_name):
    if 'source_file' in df.columns:
        df['source_file'] = original_name

    if bank_key not in {'dbs'}:
        df = normalize_date_columns(df, inferred_year)

    df['company_id'] = company_id
    return df


def dataframe_preview_records(df):
    preview_df = df.copy()
    for col in preview_df.columns:
        if pd.api.types.is_datetime64_any_dtype(preview_df[col]):
            preview_df[col] = preview_df[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
    return preview_df.to_dict(orient='records')


def dataframe_bank_code(bank_key):
    bank_code_for_db = bank_key.upper()
    if bank_code_for_db == 'CCBCA':
        return 'BCA_CC'
    if bank_code_for_db == 'CCMANDIRI':
        return 'MANDIRI_CC'
    if bank_code_for_db == 'MANDIRI_EMAIL':
        return 'MANDIRI'
    return bank_code_for_db


def output_file_meta(output_format):
    if output_format == 'csv':
        return {
            'dir': 'csv',
            'extension': '.csv',
            'mimetype': 'text/csv',
        }
    return {
        'dir': 'excel',
        'extension': '.xlsx',
        'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }
