import os
import hashlib
import uuid
from flask import Blueprint, request, jsonify, send_file, current_app as app
from werkzeug.utils import secure_filename
import pandas as pd
import PyPDF2
from backend.db.session import get_db_engine
from backend.services.transaction_service import save_transactions_to_db
from backend.utils.date_helpers import normalize_date_columns, standardize_statement_dates
from backend.utils.pdf_helpers import infer_year_from_pdf, infer_year_from_filename
from pdf_unlock import unlock_pdf
from bank_parsers import bca, mandiri, dbs, bca_cc, mandiri_cc, bri, saqu, blu
from sqlalchemy import text

# PyPDF2 Error handling
try:
    from PyPDF2.errors import PdfReadError
except (ImportError, AttributeError):
    try:
        from PyPDF2.utils import PdfReadError
    except (ImportError, AttributeError):
        class PdfReadError(Exception):
            pass

pdf_bp = Blueprint('pdf_bp', __name__)

@pdf_bp.route('/')
def index():
    return send_file('index.html')

@pdf_bp.route('/check_password', methods=['POST', 'OPTIONS'])
@pdf_bp.route('/api/check-password', methods=['POST', 'OPTIONS'])
def check_password():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['pdf_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)
        
        try:
            with open(pdf_path, 'rb') as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                is_protected = reader.is_encrypted
                if is_protected:
                    try:
                        result = reader.decrypt('')
                        if result not in (0, False):
                            is_protected = False
                    except Exception:
                        pass
                
            return jsonify({'password_protected': bool(is_protected)})
        except PdfReadError:
            return jsonify({'error': 'Invalid or corrupted PDF file'}), 400
        finally:
            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except Exception:
                    pass
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@pdf_bp.route('/convert_pdf', methods=['POST', 'OPTIONS'])
@pdf_bp.route('/api/convert', methods=['POST', 'OPTIONS'])
def convert_pdf():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'No file uploaded. Please select a PDF or CSV file.'}), 400
        
        file = request.files['pdf_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected. Please choose a PDF or CSV file to upload.'}), 400
        
        is_csv = file.filename.lower().endswith('.csv')
        is_pdf = file.filename.lower().endswith('.pdf')
        
        if not (is_csv or is_pdf):
            return jsonify({'error': 'Invalid file type. Please upload a PDF or CSV file.'}), 400
            
        file_content = file.read()
        if len(file_content) > 10 * 1024 * 1024:
            return jsonify({'error': 'File size too large. Maximum file size is 10MB.'}), 400
        file.seek(0)

        bank_type = request.form.get('bank_type', 'bca')
        company_id = request.form.get('company_id')
        if not company_id or company_id == 'none':
            company_id = None
        
        filename = secure_filename(file.filename)
        original_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(original_pdf_path)
        file.seek(0)
        pdf_path = original_pdf_path
        
        password = request.form.get('password', '')
        password = password.strip() if password else None
        requires_password = False

        if is_pdf:
            try:
                with open(original_pdf_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
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
                            requires_password = True
            except Exception as e:
                return jsonify({'error': f'Error evaluating PDF encryption: {str(e)}'}), 400

            if requires_password and not password:
                return jsonify({
                    'error': 'This PDF is password protected. Please provide the password.',
                    'require_password': True
                }), 400

            if password:
                try:
                    pdf_path = unlock_pdf(original_pdf_path, password)
                except PdfReadError:
                    return jsonify({'error': 'Invalid PDF password', 'require_password': True}), 400
                except RuntimeError as e:
                    return jsonify({'error': str(e)}), 400

        if is_pdf:
            inferred_year = infer_year_from_pdf(pdf_path) or infer_year_from_filename(original_pdf_path)
        else:
            inferred_year = infer_year_from_filename(original_pdf_path)
        
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
            engine, error_msg = get_db_engine()
            if engine:
                try:
                    with engine.connect() as conn:
                        existing = conn.execute(text("SELECT id FROM transactions WHERE file_hash = :hash LIMIT 1"), {"hash": file_hash}).fetchone()
                        if existing:
                            return jsonify({'error': 'This file has already been uploaded.'}), 409
                except Exception:
                    pass

        base_name = os.path.splitext(filename)[0]
        output_dir = 'excel' if output_format == 'excel' else 'csv'
        file_extension = '.xlsx' if output_format == 'excel' else '.csv'
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if output_format == 'excel' else 'text/csv'
        
        if is_preview:
            output_format = 'json'
        
        try:
            bank_key = bank_type.lower()
            if bank_key == 'bri' and not is_csv:
                return jsonify({'error': 'BRI statements must be in CSV format.'}), 400
            elif bank_key != 'bri' and is_csv:
                return jsonify({'error': 'CSV files are only supported for BRI bank.'}), 400
            
            if bank_key == 'mandiri':
                df = mandiri.parse_statement(pdf_path)
            elif bank_key == 'dbs':
                df = dbs.parse_statement(pdf_path, target_year=inferred_year)
            elif bank_key == 'ccbca':
                df = bca_cc.parse_statement(pdf_path, inferred_year)
            elif bank_key == 'ccmandiri':
                df = mandiri_cc.parse_statement(pdf_path, password=password)
            elif bank_key == 'bri':
                df = bri.parse_statement(pdf_path)
            elif bank_key == 'saqu':
                df = saqu.parse_statement(pdf_path, password=password)
            elif bank_key == 'blu':
                df = blu.parse_statement(pdf_path)
            else:
                df = bca.parse_statement(pdf_path)
                df = standardize_statement_dates(df, 'Tanggal', 'dd/mm', inferred_year)

            original_name = os.path.basename(original_pdf_path)
            if 'source_file' in df.columns:
                df['source_file'] = original_name
                
            if bank_key not in {'dbs'}:
                df = normalize_date_columns(df, inferred_year)
            
            df['company_id'] = company_id
                
            if is_preview:
                df_json = df.copy()
                for col in df_json.columns:
                    if pd.api.types.is_datetime64_any_dtype(df_json[col]):
                        df_json[col] = df_json[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
                records = df_json.to_dict(orient='records')
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
            
            bank_code_for_db = bank_key.upper()
            if bank_code_for_db == 'CCBCA': bank_code_for_db = 'BCA_CC'
            elif bank_code_for_db == 'CCMANDIRI': bank_code_for_db = 'MANDIRI_CC'
            
            db_success, db_error = save_transactions_to_db(df, bank_code_for_db, original_name, file_hash)
            if not db_success:
                app.logger.error(f"Database upload failed: {db_error}")
            
            return send_file(output_path, as_attachment=True, download_name=f'{base_name}{file_extension}', mimetype=mimetype)
            
        except Exception as e:
            app.logger.exception('Error processing file')
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
    finally:
        cleanup_paths = []
        if 'pdf_path' in locals(): cleanup_paths.append(pdf_path)
        if 'original_pdf_path' in locals(): cleanup_paths.append(original_pdf_path)
        if 'output_path' in locals(): cleanup_paths.append(output_path)
        for path in {p for p in cleanup_paths if p}:
            if os.path.exists(path):
                try: os.remove(path)
                except Exception: pass
