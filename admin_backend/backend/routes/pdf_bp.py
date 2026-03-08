import os
import hashlib
from flask import Blueprint, current_app as app, jsonify, request, send_file

import pandas as pd

from backend.routes.accounting_utils import require_db_engine
from backend.routes.pdf_helpers import (
    PdfReadError,
    dataframe_bank_code,
    dataframe_preview_records,
    detect_pdf_password_requirement,
    infer_statement_year,
    normalize_company_id,
    normalize_statement_dataframe,
    output_file_meta,
    parse_statement,
    resolve_pdf_access_path,
    save_uploaded_file,
)
from backend.routes.pdf_queries import (
    count_transactions_by_source_file_query,
    find_transaction_by_file_hash_query,
)
from backend.services.transaction_service import save_transactions_to_db

pdf_bp = Blueprint('pdf_bp', __name__)
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FRONTEND_DIST_INDEX = os.path.abspath(
    os.path.join(BACKEND_ROOT, '..', 'admin_frontend', 'dist', 'index.html')
)


def _empty_options_response():
    return jsonify({}), 200


def _error_response(message, status_code, **payload):
    data = {'error': str(message)}
    data.update(payload)
    return jsonify(data), status_code


def _remove_file_if_exists(path):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def _uploaded_file_from_request(
    missing_file_message='No file uploaded. Please select a PDF or CSV file.',
    empty_file_message='No file selected. Please choose a PDF or CSV file to upload.',
):
    if 'pdf_file' not in request.files:
        return None, _error_response(missing_file_message, 400)

    file = request.files['pdf_file']
    if file.filename == '':
        return None, _error_response(empty_file_message, 400)

    return file, None


def _validate_upload_type(file_storage):
    is_csv = file_storage.filename.lower().endswith('.csv')
    is_pdf = file_storage.filename.lower().endswith('.pdf')
    if not (is_csv or is_pdf):
        return None, None, _error_response('Invalid file type. Please upload a PDF or CSV file.', 400)
    return is_csv, is_pdf, None


def _read_upload_bytes(file_storage):
    file_content = file_storage.read()
    if len(file_content) > 10 * 1024 * 1024:
        return None, _error_response('File size too large. Maximum file size is 10MB.', 400)
    file_storage.seek(0)
    return file_content, None


def _check_duplicate_file_hash(file_hash):
    engine = require_db_engine()
    with engine.connect() as conn:
        existing = conn.execute(
            find_transaction_by_file_hash_query(),
            {"hash": file_hash}
        ).fetchone()
    if existing:
        return _error_response('This file has already been uploaded.', 409)
    return None


def _resolve_processing_pdf_path(original_pdf_path, password):
    try:
        pdf_path, requires_password = resolve_pdf_access_path(original_pdf_path, password=password)
    except PdfReadError:
        return None, _error_response('Invalid or corrupted PDF file', 400)
    except RuntimeError as exc:
        return None, _error_response(str(exc), 400)
    except Exception as exc:
        return None, _error_response(f'Error evaluating PDF encryption: {exc}', 400)

    if requires_password and not password:
        return None, _error_response(
            'This PDF is password protected. Please provide the password.',
            400,
            require_password=True,
        )

    return pdf_path, None


@pdf_bp.route('/')
def index():
    if os.path.exists(FRONTEND_DIST_INDEX):
        return send_file(FRONTEND_DIST_INDEX)
    return jsonify({
        'message': 'API is running',
        'frontend': 'Run admin_frontend dev server or build admin_frontend/dist first.'
    })

@pdf_bp.route('/check_password', methods=['POST', 'OPTIONS'])
@pdf_bp.route('/api/check-password', methods=['POST', 'OPTIONS'])
def check_password():
    if request.method == 'OPTIONS':
        return _empty_options_response()

    file, error_response = _uploaded_file_from_request(
        missing_file_message='No file uploaded',
        empty_file_message='No file selected',
    )
    if error_response:
        return error_response

    _, pdf_path = save_uploaded_file(app.config['UPLOAD_FOLDER'], file)
    try:
        try:
            return jsonify({'password_protected': bool(detect_pdf_password_requirement(pdf_path))})
        except PdfReadError:
            return _error_response('Invalid or corrupted PDF file', 400)
    finally:
        _remove_file_if_exists(pdf_path)


@pdf_bp.route('/check_upload_name', methods=['POST', 'OPTIONS'])
@pdf_bp.route('/api/check-upload-name', methods=['POST', 'OPTIONS'])
def check_upload_name():
    if request.method == 'OPTIONS':
        return _empty_options_response()

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        raw_name = payload.get('file_name', '')
    else:
        raw_name = request.form.get('file_name', '')

    source_file = os.path.basename(raw_name or '')
    if not source_file:
        return _error_response('file_name is required', 400)

    engine = require_db_engine()
    with engine.connect() as conn:
        count_row = conn.execute(
            count_transactions_by_source_file_query(),
            {'source_file': source_file}
        ).fetchone()
        uploaded_count = int(count_row.cnt or 0) if count_row else 0

    return jsonify({
        'source_file': source_file,
        'exists': uploaded_count > 0,
        'count': uploaded_count
    })

@pdf_bp.route('/convert_pdf', methods=['POST', 'OPTIONS'])
@pdf_bp.route('/api/convert', methods=['POST', 'OPTIONS'])
def convert_pdf():
    if request.method == 'OPTIONS':
        return _empty_options_response()

    file, error_response = _uploaded_file_from_request()
    if error_response:
        return error_response

    is_csv, is_pdf, error_response = _validate_upload_type(file)
    if error_response:
        return error_response

    file_content, error_response = _read_upload_bytes(file)
    if error_response:
        return error_response

    bank_type = request.form.get('bank_type', 'bca')
    company_id = normalize_company_id(request.form.get('company_id'))
    filename, original_pdf_path = save_uploaded_file(app.config['UPLOAD_FOLDER'], file)
    file.seek(0)
    pdf_path = original_pdf_path
    output_path = None

    password = request.form.get('password', '')
    password = password.strip() if password else None

    try:
        if is_pdf:
            pdf_path, error_response = _resolve_processing_pdf_path(original_pdf_path, password)
            if error_response:
                return error_response

        inferred_year = infer_statement_year(pdf_path, original_pdf_path, is_pdf)
        statement_year_raw = request.form.get('statement_year')
        if statement_year_raw and statement_year_raw.isdigit():
            inferred_year = int(statement_year_raw)

        raw_output_format = request.form.get('output_format') or request.values.get('output_format') or 'excel'
        output_format = raw_output_format.lower()
        if output_format not in {'excel', 'csv'}:
            output_format = 'excel'

        is_preview = request.form.get('preview', 'false').lower() == 'true'
        file_hash = hashlib.md5(file_content).hexdigest()

        if not is_preview:
            duplicate_response = _check_duplicate_file_hash(file_hash)
            if duplicate_response:
                return duplicate_response

        base_name = os.path.splitext(filename)[0]
        output_meta = output_file_meta(output_format)
        output_dir = output_meta['dir']
        file_extension = output_meta['extension']
        mimetype = output_meta['mimetype']

        if is_preview:
            output_format = 'json'

        try:
            bank_key = bank_type.lower()
            try:
                df = parse_statement(bank_key, pdf_path, inferred_year=inferred_year, password=password, is_csv=is_csv)
            except ValueError as exc:
                return _error_response(str(exc), 400)

            original_name = os.path.basename(original_pdf_path)
            df = normalize_statement_dataframe(df, bank_key, inferred_year, company_id, original_name)

            if is_preview:
                records = dataframe_preview_records(df)
                return jsonify({'data': records, 'bank_type': bank_key})

            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f'{base_name}{file_extension}')

            if output_format == 'csv':
                df_to_save = df.copy()
                if bank_key not in {'dbs'}:
                    datetime_cols = [col for col in df_to_save.columns if pd.api.types.is_datetime64_any_dtype(df_to_save[col])]
                    for col in datetime_cols:
                        df_to_save[col] = df_to_save[col].dt.strftime('%Y-%m-%d')
                df_to_save.to_csv(output_path, index=False)
            else:
                df.to_excel(output_path, index=False)
            
            bank_code_for_db = dataframe_bank_code(bank_key)
            db_success, db_error = save_transactions_to_db(df, bank_code_for_db, original_name, file_hash)
            if not db_success:
                app.logger.error(f"Database upload failed: {db_error}")
                return _error_response(f'Failed to save transactions to database: {db_error}', 500)

            return send_file(output_path, as_attachment=True, download_name=f'{base_name}{file_extension}', mimetype=mimetype)

        except Exception as exc:
            app.logger.exception('Error processing file')
            return _error_response(str(exc), 500)
    finally:
        cleanup_paths = [pdf_path, original_pdf_path, output_path]
        for path in {p for p in cleanup_paths if p}:
            _remove_file_if_exists(path)
