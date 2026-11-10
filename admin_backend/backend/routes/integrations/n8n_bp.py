"""Endpoint integrasi untuk otomasi n8n (server-to-server).

Dipakai workflow n8n untuk mengirim lampiran e-statement bank yang didownload
dari Gmail. Berbeda dari upload manual (pdf_bp), endpoint ini:
  - diautentikasi dengan API key (header X-API-Key), bukan session login;
  - selalu mengembalikan ringkasan JSON, bukan file Excel/CSV;
  - idemponen: file yang sudah pernah diupload (hash sama) dijawab
    status "duplicate" dengan HTTP 200, bukan 409, supaya re-poll email
    oleh workflow tidak dianggap error.
"""

import hashlib
import logging
import os
import secrets

from flask import Blueprint, current_app as app, jsonify, request

from backend.routes.accounting_utils import require_db_engine
from backend.routes.uploads.pdf_bp import (
    _error_response,
    _read_upload_bytes,
    _remove_file_if_exists,
    _resolve_processing_pdf_path,
    _uploaded_file_from_request,
    _validate_upload_type,
)
from backend.routes.uploads.pdf_helpers import (
    dataframe_bank_code,
    infer_statement_year,
    normalize_company_id,
    normalize_statement_dataframe,
    parse_statement,
    save_uploaded_file,
)
from backend.routes.uploads.pdf_queries import (
    find_transaction_by_file_hash_query,
    find_transaction_by_message_id_query,
)
from backend.services.notifications.telegram import (
    notify_import_problem,
    notify_missing_statements,
)
from backend.services.transactions.statement_expectations import find_missing_statements
from backend.services.transactions.transaction_service import save_transactions_to_db

logger = logging.getLogger(__name__)

integrations_bp = Blueprint('integrations_bp', __name__)

# Sama dengan bank_type yang diterima form upload manual (pdf_bp.convert_pdf).
BANK_TYPES = {'bca', 'mandiri', 'mandiri_email', 'dbs', 'ccbca', 'ccmandiri', 'bri', 'saqu', 'blu'}

EMAIL_META_FIELDS = ('email_from', 'email_subject', 'email_date', 'message_id')
# Kunci kanonik di dalam aplikasi (mengikuti nama kolom DB).
EMAIL_META_KEYS = ('email_from', 'email_subject', 'email_date', 'email_message_id')


@integrations_bp.before_request
def _require_api_key():
    """Autentikasi server-to-server: header X-API-Key vs env INTEGRATION_API_KEY.

    Fail closed: tanpa INTEGRATION_API_KEY endpoint mati total (503), bukan
    terbuka tanpa autentikasi.
    """
    expected = os.environ.get('INTEGRATION_API_KEY', '').strip()
    if not expected:
        logger.error('INTEGRATION_API_KEY belum diset — endpoint integrasi nonaktif')
        return jsonify({
            'error': 'Integration endpoint is not configured',
            'code': 'integration_disabled',
        }), 503
    provided = request.headers.get('X-API-Key', '')
    if not secrets.compare_digest(provided.encode(), expected.encode()):
        return jsonify({'error': 'Invalid API key', 'code': 'invalid_api_key'}), 401
    return None


def _is_duplicate_file_hash(file_hash):
    engine = require_db_engine()
    with engine.connect() as conn:
        existing = conn.execute(
            find_transaction_by_file_hash_query(),
            {"hash": file_hash}
        ).fetchone()
    return existing is not None


def _is_duplicate_message_id(message_id):
    engine = require_db_engine()
    with engine.connect() as conn:
        existing = conn.execute(
            find_transaction_by_message_id_query(),
            {"message_id": message_id}
        ).fetchone()
    return existing is not None


def _notify_problem_safe(bank_type, filename, error_code, detail='', email_meta=None):
    """Kirim notifikasi Telegram; kegagalannya tidak boleh menelan error asli."""
    try:
        notify_import_problem(
            bank_type, filename, error_code, detail=detail, email_meta=email_meta,
        )
    except Exception:
        logger.exception('Gagal mengirim notifikasi Telegram untuk import bermasalah')


@integrations_bp.route('/api/integrations/statement', methods=['POST'])
def ingest_statement():
    file, error_response = _uploaded_file_from_request(
        missing_file_message='No file uploaded. Attach the statement as multipart field "pdf_file".',
        empty_file_message='No file selected. Attach the statement as multipart field "pdf_file".',
    )
    if error_response:
        return error_response

    is_csv, is_pdf, error_response = _validate_upload_type(file)
    if error_response:
        return error_response

    file_content, error_response = _read_upload_bytes(file)
    if error_response:
        return error_response

    bank_type = (request.form.get('bank_type') or '').strip().lower()
    if bank_type not in BANK_TYPES:
        return _error_response(
            f'Unknown bank_type "{bank_type}". Valid values: {", ".join(sorted(BANK_TYPES))}.',
            400,
            code='invalid_bank_type',
        )

    # Form field tetap 'message_id' (format workflow n8n); di dalam aplikasi
    # kunci mengikuti nama kolom DB agar satu kanonik.
    email_meta = {
        'email_from': (request.form.get('email_from') or '').strip()[:300],
        'email_subject': (request.form.get('email_subject') or '').strip()[:300],
        'email_date': (request.form.get('email_date') or '').strip()[:300],
        'email_message_id': (request.form.get('message_id') or '').strip()[:300],
    }
    logger.info(
        'Integrasi n8n: menerima %s (bank_type=%s) dari %s | subject=%r | message_id=%s',
        file.filename, bank_type,
        email_meta['email_from'] or '(tidak diketahui)',
        email_meta['email_subject'],
        email_meta['email_message_id'] or '-',
    )

    # Idempotensi lapis pertama: message_id. Bank kadang me-regenerate PDF
    # (byte berbeda → hash berbeda) untuk email yang sama; file_hash saja
    # tidak cukup mencegah double-import pada kasus itu.
    if email_meta['email_message_id'] and _is_duplicate_message_id(email_meta['email_message_id']):
        logger.info(
            'Integrasi n8n: message_id %s sudah pernah diproses — dilewati',
            email_meta['email_message_id'],
        )
        return jsonify({
            'status': 'duplicate',
            'duplicate': True,
            'source_file': file.filename,
            'bank_type': bank_type,
            'duplicate_by': 'message_id',
        })

    company_id = normalize_company_id(request.form.get('company_id'))
    password = request.form.get('password', '')
    password = password.strip() if password else None

    filename, original_pdf_path = save_uploaded_file(app.config['UPLOAD_FOLDER'], file)
    file.seek(0)
    pdf_path = original_pdf_path

    try:
        if is_pdf:
            pdf_path, error_response = _resolve_processing_pdf_path(original_pdf_path, password)
            if error_response:
                _notify_problem_safe(
                    bank_type, filename, 'processing_failed',
                    detail='Gagal membuka PDF (password salah atau file rusak)',
                    email_meta=email_meta,
                )
                return error_response

        inferred_year = infer_statement_year(pdf_path, original_pdf_path, is_pdf)
        statement_year_raw = request.form.get('statement_year')
        if statement_year_raw and statement_year_raw.isdigit():
            inferred_year = int(statement_year_raw)

        file_hash = hashlib.md5(file_content).hexdigest()

        if _is_duplicate_file_hash(file_hash):
            logger.info('Integrasi n8n: %s sudah pernah diupload — dilewati', filename)
            return jsonify({
                'status': 'duplicate',
                'duplicate': True,
                'source_file': filename,
                'bank_type': bank_type,
                'duplicate_by': 'file_hash',
            })

        try:
            df = parse_statement(
                bank_type, pdf_path, inferred_year=inferred_year, password=password, is_csv=is_csv,
            )
            df = normalize_statement_dataframe(df, bank_type, inferred_year, company_id, filename)
        except ValueError as exc:
            _notify_problem_safe(
                bank_type, filename, 'parse_failed', detail=str(exc), email_meta=email_meta,
            )
            return _error_response(str(exc), 400, code='parse_failed')
        except Exception as exc:
            app.logger.exception('Error processing file via integrasi n8n')
            _notify_problem_safe(
                bank_type, filename, 'processing_failed', detail=str(exc), email_meta=email_meta,
            )
            return _error_response(str(exc), 500, code='processing_failed')

        bank_code_for_db = dataframe_bank_code(bank_type)
        db_success, db_error, inserted_ids = save_transactions_to_db(
            df, bank_code_for_db, filename, file_hash, email_meta=email_meta,
        )
        if not db_success:
            app.logger.error(f"Database upload failed: {db_error}")
            _notify_problem_safe(
                bank_type, filename, 'db_failed', detail=str(db_error), email_meta=email_meta,
            )
            return _error_response(f'Failed to save transactions to database: {db_error}', 500)

        # Pass AI setelah import — sama seperti upload manual: kegagalan pass
        # tidak pernah memengaruhi hasil import.
        ai_pass_queued = False
        try:
            from backend.db.session import get_db_engine
            from backend.services.ai.llm_client import get_ai_settings
            from backend.services.ai.mark_pass import queue_ai_mark_pass, resolve_ai_pass_mode
            ai_engine, _ = get_db_engine()
            if ai_engine is not None:
                with ai_engine.connect() as conn:
                    ai_config = get_ai_settings(conn)
                if resolve_ai_pass_mode(ai_config) == 'thread':
                    ai_pass_queued = queue_ai_mark_pass(inserted_ids)
        except Exception:
            app.logger.exception('Gagal menjadwalkan AI mark pass')

        return jsonify({
            'status': 'imported',
            'duplicate': False,
            'source_file': filename,
            'bank_type': bank_type,
            'rows_inserted': len(inserted_ids),
            'ai_pass_queued': ai_pass_queued,
        })

    finally:
        for path in {p for p in (pdf_path, original_pdf_path) if p}:
            _remove_file_if_exists(path)


@integrations_bp.route('/api/integrations/statement-check', methods=['POST'])
def check_missing_statements():
    """Cek e-statement bulan lalu yang belum masuk + kirim alert Telegram.

    Dipanggil workflow n8n harian setelah polling Gmail. Query param `date`
    (ISO, opsional) memungkinkan pengecekan mundur untuk bulan tertentu —
    tanpa param, tanggal hari ini yang dipakai.
    """
    import datetime

    engine = require_db_engine()
    today = datetime.date.today()
    date_raw = (request.args.get('date') or '').strip()
    if date_raw:
        try:
            today = datetime.date.fromisoformat(date_raw)
        except ValueError:
            return _error_response(
                f'Invalid date "{date_raw}" — gunakan format YYYY-MM-DD.',
                400,
                code='invalid_date',
            )

    missing = find_missing_statements(engine, today=today)
    notified = False
    if missing:
        try:
            notified = notify_missing_statements(missing)
        except Exception:
            logger.exception('Gagal mengirim notifikasi statement hilang')

    return jsonify({
        'status': 'ok',
        'checked_for': missing[0]['month'] if missing else None,
        'missing': missing,
        'notified': notified,
    })
