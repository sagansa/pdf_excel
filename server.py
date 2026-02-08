from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import os
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from bank_parsers import bca, mandiri, dbs, bca_cc, mandiri_cc, bri, saqu, blu
import pandas as pd
import io
import xml.etree.ElementTree as ET
import pdfplumber
from flask_cors import CORS
import PyPDF2
import uuid
from sqlalchemy import create_engine, text
try:  # Support both new and legacy PyPDF2 versions
    from PyPDF2.errors import PdfReadError  # type: ignore[attr-defined]
except (ImportError, AttributeError):  # pragma: no cover - fallback for older PyPDF2
    try:
        from PyPDF2.utils import PdfReadError  # type: ignore
    except (ImportError, AttributeError):
        class PdfReadError(Exception):  # type: ignore
            """Fallback PdfReadError for very old PyPDF2 releases."""
            pass
from pdf_unlock import unlock_pdf
from migrate import run_migrations
from decimal import Decimal

# Database configuration
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', 'root') # Default MAMP
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306') # Default MAMP
DB_NAME = os.environ.get('DB_NAME', 'bank_converter')

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# Base URL without database name to allow creating the database
DB_BASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}"
_db_engine = None
_db_last_error = None

def get_db_engine():
    global _db_engine, _db_last_error
    if _db_engine is None:
        try:
            # First, try to connect to the specific database
            _db_engine = create_engine(DB_URL)
            # Test connection
            with _db_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _db_last_error = None
        except Exception as e:
            # If the database doesn't exist, try to create it
            if "Unknown database" in str(e) or "database exists" in str(e) or "1049" in str(e):
                try:
                    print(f"Database '{DB_NAME}' not found. Attempting to create it...")
                    temp_engine = create_engine(DB_BASE_URL)
                    with temp_engine.connect() as conn:
                        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
                        conn.commit()
                    # Now try connecting again
                    _db_engine = create_engine(DB_URL)
                    _db_last_error = None
                except Exception as create_err:
                    _db_last_error = f"Database creation failed: {str(create_err)}"
                    _db_engine = None
            else:
                _db_last_error = f"Connection failed: {str(e)}"
                _db_engine = None
    return _db_engine, _db_last_error

def save_transactions_to_db(df: pd.DataFrame, bank_code: str, source_file: str, file_hash: str):
    engine, error_msg = get_db_engine()
    if engine is None:
        return False, error_msg or f"Failed to connect to database at {DB_HOST}:{DB_PORT}"
    
    records = []
    now = datetime.now()
    for _, row in df.iterrows():
        try:
            txn_id = str(uuid.uuid4())
            txn_date = row.get('txn_date') or row.get('Transaction Date') or row.get('Tanggal')
            description = row.get('description') or row.get('Transaction Details') or row.get('Keterangan')
            amount = row.get('amount') or row.get('Amount')
            db_cr = row.get('db_cr') or row.get('DB/CR') or 'DB'
            created_at = row.get('created_at') or now
            
            if isinstance(amount, float):
                 amount_val = amount
            elif isinstance(amount, str):
                amount_val = amount.replace(',', '')
                try:
                    amount_val = float(amount_val) if amount_val else 0.0
                except (ValueError, TypeError):
                    amount_val = 0.0
            else:
                amount_val = float(amount or 0.0)
            
            records.append({
                'id': txn_id,
                'txn_date': txn_date,
                'description': str(description or '')[:1000],
                'amount': amount_val,
                'db_cr': str(db_cr or 'DB')[:2].upper(),
                'bank_code': bank_code,
                'source_file': source_file,
                'file_hash': file_hash,
                'mark_id': None, # Default to None
                'company_id': row.get('company_id'),
                'created_at': created_at,
                'updated_at': now
            })
        except Exception as e:
            continue
            
    if records:
        try:
            with engine.connect() as conn:
                query = text("""
                    INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, source_file, file_hash, mark_id, company_id, created_at, updated_at)
                    VALUES (:id, :txn_date, :description, :amount, :db_cr, :bank_code, :source_file, :file_hash, :mark_id, :company_id, :created_at, :updated_at)
                """)
                conn.execute(query, records)
                conn.commit()
                return True, None
        except Exception as e:
            return False, f"Database Error: {str(e)}"
    return True, None

def normalize_date_columns(df: pd.DataFrame, default_year: Optional[int] = None) -> pd.DataFrame:
    """Convert date-like columns to ISO strings (YYYY-MM-DD)."""
    if df is None or df.empty:
        return df

    date_like_columns = [
        col for col in df.columns
        if any(keyword in col.lower() for keyword in ('tanggal', 'date'))
    ]

    for col in date_like_columns:
        df[col] = df[col].apply(lambda value: coerce_iso_date(value, default_year))

    return df

def infer_year_from_pdf(pdf_path: str) -> Optional[int]:
    """Extract a plausible statement year by scanning the first pages of the PDF."""
    try:
        with open(pdf_path, 'rb') as fh:
            reader = PyPDF2.PdfReader(fh)
            text_content = []
            for page in reader.pages[:2]:
                try:
                    text_content.append(page.extract_text() or '')
                except Exception:
                    continue
            text = '\n'.join(text_content)
    except Exception:
        return None

    year_counts: Dict[int, int] = {}

    for _, _, year in re.findall(r'(\d{2})/(\d{2})/(\d{4})', text):
        year_int = int(year)
        year_counts[year_int] = year_counts.get(year_int, 0) + 1

    for year in re.findall(r'((?:19|20)\d{2})', text):
        year_int = int(year)
        year_counts[year_int] = year_counts.get(year_int, 0) + 1

    if year_counts:
        return max(year_counts, key=year_counts.get)

    return None

def standardize_statement_dates(df: pd.DataFrame, date_col: str, format_type: str = 'dd/mm', base_year: Optional[int] = None) -> pd.DataFrame:
    """Convert statement dates (DD/MM or MM/DD) into ISO format with year rollover detection."""
    if df is None or df.empty or date_col not in df.columns:
        return df

    current_year = base_year or datetime.now().year
    last_month = None
    iso_dates: List[str] = []

    for raw_value in df[date_col]:
        val_str = str(raw_value).strip()
        if not val_str or val_str.lower() == 'nan':
            iso_dates.append(raw_value)
            continue

        # Match DD/MM or MM/DD
        match = re.match(r'^([0-1]?\d)[/]([0-3]?\d)$', val_str)
        if not match:
            # Try to see if it's already ISO or something else
            iso_dates.append(raw_value)
            continue

        if format_type.lower() == 'mm/dd':
            month = int(match.group(1))
            day = int(match.group(2))
        else: # Default dd/mm
            day = int(match.group(1))
            month = int(match.group(2))

        if not (1 <= day <= 31 and 1 <= month <= 12):
            iso_dates.append(raw_value)
            continue

        # Year Rollover Detection (Dec -> Jan jump)
        if last_month is not None and month < last_month:
            # Month decreased, assume new year (e.g. 12 -> 01)
            current_year += 1
        last_month = month

        try:
            iso_dates.append(datetime(current_year, month, day).strftime('%Y-%m-%d'))
        except ValueError:
            iso_dates.append(raw_value)

    df = df.copy()
    df[date_col] = iso_dates
    return df

def infer_year_from_filename(path: str) -> Optional[int]:
    """Extract a year from the supplied filename."""
    basename = os.path.basename(path)
    matches = re.findall(r'(?:19|20)\d{2}', basename)
    if not matches:
        return None
    # Prefer the last occurrence in case of ranges like 2023-2024
    return int(matches[-1])

def coerce_iso_date(value, default_year: Optional[int] = None) -> Optional[str]:
    """Best-effort conversion of assorted date representations to ISO format."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    if isinstance(value, (datetime, pd.Timestamp)):
        return value.strftime('%Y-%m-%d')

    text = str(value).strip()
    if not text:
        return None

    # Already in ISO format (with optional time component)
    match_iso = re.match(r'^(\d{4})[-/](\d{2})[-/](\d{2})(?:\s+\d{2}:\d{2}:\d{2})?$', text)
    if match_iso:
        year, month, day = map(int, match_iso.groups())
        return safe_iso_date(year, month, day, fallback=text)

    # DD/MM[/YYYY]
    match_ddmm = re.match(r'^(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?$', text)
    if match_ddmm:
        day = int(match_ddmm.group(1))
        month = int(match_ddmm.group(2))
        year_part = match_ddmm.group(3)

        if year_part:
            year = int(year_part)
            if year < 100:
                year += 2000 if year < 50 else 1900
        else:
            year = default_year or datetime.now().year

        return safe_iso_date(year, month, day, fallback=text)

    # Fallback to pandas parsing (still assuming day-first)
    try:
        parsed = pd.to_datetime(text, dayfirst=True, errors='raise')
        return parsed.strftime('%Y-%m-%d')
    except Exception:
        return text

def safe_iso_date(year: int, month: int, day: int, fallback: str) -> str:
    try:
        return datetime(year, month, day).strftime('%Y-%m-%d')
    except ValueError:
        return fallback

app = Flask(__name__)
# Configure CORS with more specific settings
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "expose_headers": "*"}})

# Configure upload folder
UPLOAD_FOLDER = 'pdfs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/check_password', methods=['POST', 'OPTIONS'])
@app.route('/api/check-password', methods=['POST', 'OPTIONS'])
def check_password():

    # Handle preflight OPTIONS request for CORS
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        if 'pdf_file' not in request.files:
            return {'error': 'No file uploaded'}, 400, {'Content-Type': 'application/json'}
        
        file = request.files['pdf_file']
        if file.filename == '':
            return {'error': 'No file selected'}, 400, {'Content-Type': 'application/json'}
            
        # Save the uploaded PDF temporarily
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)
        
        try:
            # Check if PDF is password protected
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
                
            return {'password_protected': bool(is_protected)}, 200, {'Content-Type': 'application/json'}
            
        except PdfReadError:
            return {'error': 'Invalid or corrupted PDF file'}, 400, {'Content-Type': 'application/json'}
        finally:
            # Clean up temporary file
            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except Exception:
                    pass
                    
    except Exception as e:
        return {'error': str(e)}, 400, {'Content-Type': 'application/json'}

@app.route('/convert_pdf', methods=['POST', 'OPTIONS'])
@app.route('/api/convert', methods=['POST', 'OPTIONS'])
def convert_pdf():

    # Handle preflight OPTIONS request for CORS
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
        
    try:
        # Validate file upload
        if 'pdf_file' not in request.files:
            return {'error': 'No file uploaded. Please select a PDF or CSV file.'}, 400, {'Content-Type': 'application/json'}
        
        file = request.files['pdf_file']
        if file.filename == '':
            return {'error': 'No file selected. Please choose a PDF or CSV file to upload.'}, 400, {'Content-Type': 'application/json'}
        
        # Check file extension
        is_csv = file.filename.lower().endswith('.csv')
        is_pdf = file.filename.lower().endswith('.pdf')
        
        if not (is_csv or is_pdf):
            return {'error': 'Invalid file type. Please upload a PDF or CSV file.'}, 400, {'Content-Type': 'application/json'}
            
        # Validate file size (max 10MB)
        if len(file.read()) > 10 * 1024 * 1024:  # 10MB in bytes
            return {'error': 'File size too large. Maximum file size is 10MB.'}, 400, {'Content-Type': 'application/json'}
        file.seek(0)  # Reset file pointer after reading

        # Get bank type and company from form data
        bank_type = request.form.get('bank_type', 'bca')
        company_id = request.form.get('company_id')
        if not company_id or company_id == 'none':
            company_id = None
        
        # Ensure upload directory exists
        os.makedirs('pdfs', exist_ok=True)
        
        # Save the uploaded PDF
        filename = secure_filename(file.filename)
        original_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(original_pdf_path)
        file.seek(0) # Reset file pointer for subsequent hashing or parsing
        pdf_path = original_pdf_path
        
        # Handle password-protected PDFs (skip for CSV files)
        password = request.form.get('password', '')
        password = password.strip() if password else None
        requires_password = False

        if is_pdf:
            # Determine if the PDF is encrypted and whether it can be opened without a password
            try:
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
                                except RuntimeError as e:
                                    return {'error': str(e)}, 400, {'Content-Type': 'application/json'}
                                except Exception as e:
                                    return {'error': f'Error processing PDF: {str(e)}'}, 400, {'Content-Type': 'application/json'}
                            else:
                                requires_password = True
                        else:
                            requires_password = True
            except Exception as e:
                return {'error': f'Error evaluating PDF encryption: {str(e)}'}, 400, {'Content-Type': 'application/json'}

            if requires_password and not password:
                return {
                    'error': 'This PDF is password protected. Please provide the password.',
                    'require_password': True
                }, 400, {'Content-Type': 'application/json'}

            if password:
                try:
                    pdf_path = unlock_pdf(original_pdf_path, password)
                except PdfReadError:
                    return {'error': 'Invalid PDF password', 'require_password': True}, 400, {'Content-Type': 'application/json'}
                except RuntimeError as e:
                    return {'error': str(e)}, 400, {'Content-Type': 'application/json'}
                except Exception as e:
                    return {'error': f'Error processing PDF: {str(e)}'}, 400, {'Content-Type': 'application/json'}

        # Infer year (skip PDF parsing for CSV files)
        if is_pdf:
            inferred_year = infer_year_from_pdf(pdf_path) or infer_year_from_filename(original_pdf_path)
        else:
            inferred_year = infer_year_from_filename(original_pdf_path)
        
        # Get statement year from request (Priority override)
        statement_year_raw = request.form.get('statement_year')
        if statement_year_raw and statement_year_raw.isdigit():
            inferred_year = int(statement_year_raw)
        
        # Determine desired output format and destination
        raw_output_format = (
            request.form.get('output_format')
            or request.values.get('output_format')
            or request.args.get('output_format')
            or 'excel'
        )
        output_format = raw_output_format.lower() if raw_output_format else 'excel'
        if output_format not in {'excel', 'csv'}:
            output_format = 'excel'

        is_preview = request.form.get('preview', 'false').lower() == 'true'
        
        if is_pdf:
            file_content = file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            file.seek(0) # Reset file pointer for saving
            
            # Check for existing file_hash in DB (only if NOT a preview)
            if not is_preview:
                engine, error_msg = get_db_engine()
                if engine:
                    try:
                        with engine.connect() as conn:
                            existing = conn.execute(text("SELECT id FROM transactions WHERE file_hash = :hash LIMIT 1"), {"hash": file_hash}).fetchone()
                            if existing:
                                return {'error': 'This file has already been uploaded.'}, 409, {'Content-Type': 'application/json'}
                    except Exception as e:
                        print(f"Hash check failed: {e}")
        else: # CSV
            file_content = file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            file.seek(0)
            
            engine, error_msg = get_db_engine()
            if engine:
                try:
                    with engine.connect() as conn:
                        existing = conn.execute(text("SELECT id FROM transactions WHERE file_hash = :hash LIMIT 1"), {"hash": file_hash}).fetchone()
                        if existing:
                            return {'error': 'This file has already been uploaded.'}, 409, {'Content-Type': 'application/json'}
                except Exception as e:
                    print(f"Hash check failed: {e}")

        # ... rest of the function ...
        base_name = os.path.splitext(filename)[0]
        is_preview = request.form.get('preview', 'false').lower() == 'true'
        
        # Initialize default variables to prevent UnboundLocalError
        output_dir = 'excel'
        file_extension = '.xlsx'
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        output_path = ''
        
        if is_preview:
            output_format = 'json'
        
        try:
            # Parse the file based on bank type
            bank_key = bank_type.lower()
            
            # Validate bank type matches file type
            if bank_key == 'bri' and not is_csv:
                return {'error': 'BRI statements must be in CSV format. Please upload a CSV file.'}, 400, {'Content-Type': 'application/json'}
            elif bank_key != 'bri' and is_csv:
                return {'error': 'CSV files are only supported for BRI bank. Please select BRI as the bank type or upload a PDF file.'}, 400, {'Content-Type': 'application/json'}
            
            if bank_key == 'mandiri':
                df = mandiri.parse_statement(pdf_path)
            elif bank_key == 'dbs':
                df = dbs.parse_statement(pdf_path, target_year=inferred_year)
            elif bank_key == 'ccbca':
                df = bca_cc.parse_statement(pdf_path, inferred_year)
            elif bank_key == 'ccmandiri':
                df = mandiri_cc.parse_statement(pdf_path, password=password)
            elif bank_key == 'bri':
                # BRI uses CSV format
                df = bri.parse_statement(pdf_path)
            elif bank_key == 'saqu':
                # SAQU may be password-protected
                df = saqu.parse_statement(pdf_path, password=password)
            elif bank_key == 'blu':
                df = blu.parse_statement(pdf_path)
            else:  # Default to BCA
                df = bca.parse_statement(pdf_path)
                df = standardize_statement_dates(df, 'Tanggal', 'dd/mm', inferred_year)

            original_name = os.path.basename(original_pdf_path)
            if 'source_file' in df.columns:
                df['source_file'] = original_name
                
            if bank_key not in {'dbs'}:
                df = normalize_date_columns(df, inferred_year)
            
            # Add company_id to dataframe for saving to DB
            df['company_id'] = company_id
                
            if is_preview:
                # Return data as JSON for preview, skip DB and file saving
                # Convert NaT/None to empty strings for JSON compatibility
                df_json = df.copy()
                # Handle datetime columns for JSON
                for col in df_json.columns:
                    if pd.api.types.is_datetime64_any_dtype(df_json[col]):
                        df_json[col] = df_json[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
                
                records = df_json.to_dict(orient='records')
                return {'data': records, 'bank_type': bank_key}, 200, {'Content-Type': 'application/json'}

            # Determine file output details (only for non-preview)
            if output_format == 'csv':
                output_dir = 'csv'
                file_extension = '.csv'
                mimetype = 'text/csv'
            else:
                output_dir = 'excel'
                file_extension = '.xlsx'
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f'{base_name}{file_extension}')

            # Save to the requested format
            if output_format == 'csv':
                df_to_save = df.copy()
                if bank_key not in {'dbs'}:
                    datetime_cols = [
                        col for col in df_to_save.columns
                        if pd.api.types.is_datetime64_any_dtype(df_to_save[col])
                    ]
                    for col in datetime_cols:
                        df_to_save[col] = df_to_save[col].dt.strftime('%Y-%m-%d')
                df_to_save.to_csv(output_path, index=False)
            else:
                df.to_excel(output_path, index=False)
            
            # Save to Database for all banks
            bank_code_for_db = bank_key.upper()
            if bank_code_for_db == 'CCBCA': bank_code_for_db = 'BCA_CC'
            elif bank_code_for_db == 'CCMANDIRI': bank_code_for_db = 'MANDIRI_CC'
            
            db_success, db_error = save_transactions_to_db(df, bank_code_for_db, original_name, file_hash)
            if not db_success:
                app.logger.error(f"Database upload failed: {db_error}")
            
            # Send the generated file back to the client
            response = send_file(
                output_path,
                as_attachment=True,
                download_name=f'{base_name}{file_extension}',
                mimetype=mimetype
            )
            
            return response
            
        except ValueError as e:
            return {'error': str(e)}, 400, {'Content-Type': 'application/json'}
        except pd.errors.EmptyDataError:
            return {'error': 'Could not extract data from the PDF file. Please ensure this is a valid bank statement with transaction data.'}, 400, {'Content-Type': 'application/json'}
        except PermissionError:
            return {'error': 'Permission denied while processing the file. Please try again.'}, 500, {'Content-Type': 'application/json'}
        except Exception as e:
            app.logger.exception('Unexpected error processing PDF')
            return {'error': f'Unexpected error: {str(e)}'}, 500, {'Content-Type': 'application/json'}
            
    except Exception as e:
        return {'error': f'Server error: {str(e)}'}, 500, {'Content-Type': 'application/json'}
        
    finally:
        # Clean up temporary files
        cleanup_paths = []

        if 'pdf_path' in locals():
            cleanup_paths.append(pdf_path)
        if 'original_pdf_path' in locals():
            cleanup_paths.append(original_pdf_path)
        if 'output_path' in locals():
            cleanup_paths.append(output_path)

        for path in {p for p in cleanup_paths if p}:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT t.*, m.internal_report, m.personal_use, m.tax_report, 
                       c.name as company_name, c.short_name as company_short_name
                FROM transactions t 
                LEFT JOIN marks m ON t.mark_id = m.id 
                LEFT JOIN companies c ON t.company_id = c.id
                ORDER BY t.txn_date DESC, t.created_at DESC
            """)
            result = conn.execute(query)
            transactions = []
            for row in result:
                # Convert row to dict, handling datetime objects
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, Decimal):
                        d[key] = float(value)
                transactions.append(d)
            return {'transactions': transactions}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/transactions/upload-summary', methods=['GET'])
def get_upload_summary():
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT t.source_file, 
                       COUNT(*) as transaction_count, 
                       MIN(t.txn_date) as start_date, 
                       MAX(t.txn_date) as end_date,
                       t.bank_code,
                       c.name as company_name,
                       t.company_id,
                       SUM(CASE WHEN t.db_cr = 'DB' THEN t.amount ELSE 0 END) as total_debit,
                       SUM(CASE WHEN t.db_cr = 'CR' THEN t.amount ELSE 0 END) as total_credit,
                       MAX(t.created_at) as last_upload
                FROM transactions t
                LEFT JOIN companies c ON t.company_id = c.id
                GROUP BY t.source_file, t.bank_code, t.company_id
                ORDER BY last_upload DESC
            """)
            result = conn.execute(query)
            summary = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, Decimal):
                        d[key] = float(value)
                summary.append(d)
            return {'summary': summary}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/transactions/delete-by-source', methods=['POST'])
def delete_by_source():
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    
    data = request.json
    source_file = data.get('source_file')
    bank_code = data.get('bank_code')
    company_id = data.get('company_id')
    
    if not source_file:
        return {'error': 'source_file is required'}, 400
        
    try:
        with engine.begin() as conn:
            # Build query dynamically based on whether bank_code/company_id are provided
            # (Matches how they are grouped in the summary)
            where_clauses = ["source_file = :source_file"]
            params = {"source_file": source_file}
            
            if bank_code:
                where_clauses.append("bank_code = :bank_code")
                params["bank_code"] = bank_code
            if company_id:
                where_clauses.append("company_id = :company_id")
                params["company_id"] = company_id
            else:
                where_clauses.append("company_id IS NULL")
                
            query = text(f"DELETE FROM transactions WHERE {' AND '.join(where_clauses)}")
            result = conn.execute(query, params)
            return {'message': f'Deleted {result.rowcount} transactions'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/marks', methods=['GET'])
def get_marks():
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        with engine.connect() as conn:
            # 1. Fetch Marks
            result = conn.execute(text("SELECT * FROM marks ORDER BY personal_use ASC"))
            marks = []
            marks_dict = {}
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                d['mappings'] = [] # Initialize mappings list
                marks.append(d)
                marks_dict[d['id']] = d

            # 2. Fetch Mappings with COA info
            mapping_query = text("""
                SELECT mcm.mark_id, mcm.mapping_type, coa.code, coa.name
                FROM mark_coa_mapping mcm
                JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            """)
            mapping_result = conn.execute(mapping_query)
            
            for row in mapping_result:
                m = dict(row._mapping)
                mark_id = m['mark_id']
                if mark_id in marks_dict:
                    marks_dict[mark_id]['mappings'].append({
                        'code': m['code'],
                        'name': m['name'],
                        'type': m['mapping_type']
                    })

            return {'marks': marks}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/marks', methods=['POST'])
def create_mark():
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        data = request.json
        now = datetime.now()
        mark_id = str(uuid.uuid4())
        new_row = {
            'id': mark_id,
            'internal_report': data.get('internal_report', ''),
            'personal_use': data.get('personal_use', ''),
            'tax_report': data.get('tax_report', ''),
            'created_at': now,
            'updated_at': now
        }
        with engine.connect() as conn:
            query = text("""
                INSERT INTO marks (id, internal_report, personal_use, tax_report, created_at, updated_at)
                VALUES (:id, :internal_report, :personal_use, :tax_report, :created_at, :updated_at)
            """)
            conn.execute(query, new_row)
            conn.commit()
            return {'message': 'Mark created successfully', 'id': mark_id}, 201
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/marks/<mark_id>', methods=['PUT'])
def update_mark(mark_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        data = request.json
        now = datetime.now()
        with engine.connect() as conn:
            query = text("""
                UPDATE marks 
                SET internal_report = :internal_report, 
                    personal_use = :personal_use, 
                    tax_report = :tax_report, 
                    updated_at = :updated_at 
                WHERE id = :id
            """)
            conn.execute(query, {
                'id': mark_id,
                'internal_report': data.get('internal_report', ''),
                'personal_use': data.get('personal_use', ''),
                'tax_report': data.get('tax_report', ''),
                'updated_at': now
            })
            conn.commit()
            return {'message': 'Mark updated successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/marks/<mark_id>', methods=['DELETE'])
def delete_mark(mark_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        with engine.connect() as conn:
            # Check if used in transactions
            usage = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE mark_id = :id"), {'id': mark_id}).scalar()
            if usage > 0:
                return {'error': 'Cannot delete mark that is being used by transactions'}, 400
            
            conn.execute(text("DELETE FROM marks WHERE id = :id"), {'id': mark_id})
            conn.commit()
            return {'message': 'Mark deleted successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/transactions/<txn_id>/assign-mark', methods=['POST'])
def assign_mark_transaction(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        data = request.json
        mark_id = data.get('mark_id')
        now = datetime.now()
        with engine.connect() as conn:
            query = text("UPDATE transactions SET mark_id = :mark_id, updated_at = :updated_at WHERE id = :id")
            conn.execute(query, {'id': txn_id, 'mark_id': mark_id, 'updated_at': now})
            conn.commit()
            return {'message': 'Transaction marked successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/transactions/<txn_id>/assign-company', methods=['POST'])
def assign_company_transaction(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        data = request.json
        company_id = data.get('company_id')
        now = datetime.now()
        with engine.connect() as conn:
            query = text("UPDATE transactions SET company_id = :company_id, updated_at = :updated_at WHERE id = :id")
            conn.execute(query, {'id': txn_id, 'company_id': company_id, 'updated_at': now})
            conn.commit()
            return {'message': 'Company assigned successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/transactions/bulk-mark', methods=['POST'])
def bulk_mark_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        data = request.json
        txn_ids = data.get('transaction_ids', [])
        mark_id = data.get('mark_id') or None # Can be None/empty to unmark
        
        if not txn_ids:
            return {'error': 'No transaction IDs provided'}, 400
            
        now = datetime.now()
        with engine.connect() as conn:
            # SQLAlchemy handles list/tuple for IN clause if using :ids
            query = text("UPDATE transactions SET mark_id = :mark_id, updated_at = :updated_at WHERE id IN :ids")
            conn.execute(query, {'ids': txn_ids, 'mark_id': mark_id, 'updated_at': now})
            conn.commit()
            return {'message': f'{len(txn_ids)} transactions updated successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/transactions/bulk-assign-company', methods=['POST'])
def bulk_assign_company_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        data = request.json
        txn_ids = data.get('transaction_ids', [])
        company_id = data.get('company_id') or None
        
        if not txn_ids:
            return {'error': 'No transaction IDs provided'}, 400
            
        now = datetime.now()
        with engine.connect() as conn:
            query = text("UPDATE transactions SET company_id = :company_id, updated_at = :updated_at WHERE id IN :ids")
            conn.execute(query, {'ids': txn_ids, 'company_id': company_id, 'updated_at': now})
            conn.commit()
            return {'message': f'{len(txn_ids)} transactions updated successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/transactions/<txn_id>', methods=['DELETE'])
def delete_transaction(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM transactions WHERE id = :id"), {'id': txn_id})
            conn.commit()
            return {'message': 'Transaction deleted successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/transactions/bulk-delete', methods=['POST'])
def bulk_delete_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        data = request.json
        txn_ids = data.get('transaction_ids', [])
        if not txn_ids:
            return {'error': 'No transaction IDs provided'}, 400
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM transactions WHERE id IN :ids"), {'ids': txn_ids})
            conn.commit()
            return {'message': f'{len(txn_ids)} transactions deleted successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/marks/<mark_id>', methods=['PUT', 'DELETE'])
def update_or_delete_mark(mark_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        if request.method == 'DELETE':
            with engine.connect() as conn:
                # Unmark transactions using this mark first? Or let it be NULL?
                # The DB should handle it if there's no FK constraint, but it's cleaner to NULL it
                conn.execute(text("UPDATE transactions SET mark_id = NULL WHERE mark_id = :id"), {'id': mark_id})
                conn.execute(text("DELETE FROM marks WHERE id = :id"), {'id': mark_id})
                conn.commit()
                return {'message': 'Mark deleted successfully'}
        
        data = request.json
        internal = data.get('internal_report')
        personal = data.get('personal_use')
        tax = data.get('tax_report')
        
        with engine.connect() as conn:
            query = text("""
                UPDATE marks 
                SET internal_report = :internal, personal_use = :personal, tax_report = :tax 
                WHERE id = :id
            """)
            conn.execute(query, {'id': mark_id, 'internal': internal, 'personal': personal, 'tax': tax})
            conn.commit()
            return {'message': 'Mark updated successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/companies', methods=['GET'])
def get_companies():
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM companies ORDER BY name ASC"))
            companies = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                companies.append(d)
            return {'companies': companies}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/companies', methods=['POST'])
def create_company():
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        data = request.json
        name = data.get('name')
        short_name = data.get('short_name')
        if not name:
            return {'error': 'Company name is required'}, 400
        
        company_id = str(uuid.uuid4())
        now = datetime.now()
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO companies (id, name, short_name, created_at, updated_at) VALUES (:id, :name, :short_name, :now, :now)"),
                {'id': company_id, 'name': name, 'short_name': short_name, 'now': now}
            )
            conn.commit()
            return {'id': company_id, 'name': name, 'short_name': short_name}, 201
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/companies/<company_id>', methods=['PUT', 'DELETE'])
def manage_company(company_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    
    if request.method == 'DELETE':
        try:
            with engine.connect() as conn:
                # Set transactions of this company to NULL before deleting company
                conn.execute(text("UPDATE transactions SET company_id = NULL WHERE company_id = :cid"), {'cid': company_id})
                conn.execute(text("DELETE FROM companies WHERE id = :id"), {'id': company_id})
                conn.commit()
                return {'message': 'Company deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500
    
    elif request.method == 'PUT':
        try:
            data = request.json
            name = data.get('name')
            short_name = data.get('short_name')
            if not name:
                return {'error': 'Company name is required'}, 400
            
            with engine.connect() as conn:
                conn.execute(
                    text("UPDATE companies SET name = :name, short_name = :short_name, updated_at = :now WHERE id = :id"),
                    {'id': company_id, 'name': name, 'short_name': short_name, 'now': datetime.now()}
                )
                conn.commit()
                return {'message': 'Company updated successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

# ============================================================================
# CHART OF ACCOUNTS (COA) ENDPOINTS
# ============================================================================

@app.route('/api/coa', methods=['GET'])
def get_chart_of_accounts():
    """Get all Chart of Accounts entries"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM chart_of_accounts 
                WHERE is_active = TRUE
                ORDER BY code ASC
            """))
            coa_list = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                coa_list.append(d)
            return {'coa': coa_list}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/coa', methods=['POST'])
def create_coa():
    """Create a new COA entry"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        data = request.json
        code = data.get('code')
        name = data.get('name')
        category = data.get('category')
        
        if not all([code, name, category]):
            return {'error': 'Code, name, and category are required'}, 400
        
        if category not in ['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE']:
            return {'error': 'Invalid category'}, 400
        
        coa_id = str(uuid.uuid4())
        now = datetime.now()
        
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO chart_of_accounts 
                (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at)
                VALUES (:id, :code, :name, :category, :subcategory, :description, :is_active, :parent_id, :created_at, :updated_at)
            """), {
                'id': coa_id,
                'code': code,
                'name': name,
                'category': category,
                'subcategory': data.get('subcategory'),
                'description': data.get('description'),
                'is_active': data.get('is_active', True),
                'parent_id': data.get('parent_id'),
                'created_at': now,
                'updated_at': now
            })
            conn.commit()
            return {'message': 'COA created successfully', 'id': coa_id}, 201
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/coa/<coa_id>', methods=['PUT'])
def update_coa(coa_id):
    """Update a COA entry"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        data = request.json
        now = datetime.now()
        
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE chart_of_accounts 
                SET code = :code, 
                    name = :name, 
                    category = :category,
                    subcategory = :subcategory,
                    description = :description,
                    is_active = :is_active,
                    parent_id = :parent_id,
                    updated_at = :updated_at
                WHERE id = :id
            """), {
                'id': coa_id,
                'code': data.get('code'),
                'name': data.get('name'),
                'category': data.get('category'),
                'subcategory': data.get('subcategory'),
                'description': data.get('description'),
                'is_active': data.get('is_active', True),
                'parent_id': data.get('parent_id'),
                'updated_at': now
            })
            conn.commit()
            return {'message': 'COA updated successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/coa/<coa_id>', methods=['DELETE'])
def delete_coa(coa_id):
    """Delete a COA entry (soft delete by setting is_active=FALSE)"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        with engine.connect() as conn:
            # Check if used in mappings
            usage = conn.execute(text("SELECT COUNT(*) FROM mark_coa_mapping WHERE coa_id = :id"), {'id': coa_id}).scalar()
            if usage > 0:
                # Soft delete instead of hard delete
                conn.execute(text("UPDATE chart_of_accounts SET is_active = FALSE WHERE id = :id"), {'id': coa_id})
                conn.commit()
                return {'message': 'COA deactivated (still used in mappings)'}
            
            conn.execute(text("DELETE FROM chart_of_accounts WHERE id = :id"), {'id': coa_id})
            conn.commit()
            return {'message': 'COA deleted successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

# ============================================================================
# MARK-COA MAPPING ENDPOINTS
# ============================================================================

@app.route('/api/marks/<mark_id>/coa-mappings', methods=['GET'])
def get_mark_coa_mappings(mark_id):
    """Get all COA mappings for a specific mark"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT mcm.*, coa.code, coa.name, coa.category
                FROM mark_coa_mapping mcm
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                WHERE mcm.mark_id = :mark_id
                ORDER BY coa.code
            """), {'mark_id': mark_id})
            
            mappings = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                mappings.append(d)
            return {'mappings': mappings}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/marks/<mark_id>/coa-mappings', methods=['POST'])
def create_mark_coa_mapping(mark_id):
    """Create a new mark-COA mapping"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        data = request.json
        coa_id = data.get('coa_id')
        mapping_type = data.get('mapping_type', 'DEBIT')
        
        if not coa_id:
            return {'error': 'COA ID is required'}, 400
        
        if mapping_type not in ['DEBIT', 'CREDIT']:
            return {'error': 'Invalid mapping type'}, 400
        
        mapping_id = str(uuid.uuid4())
        now = datetime.now()
        
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO mark_coa_mapping 
                (id, mark_id, coa_id, mapping_type, notes, created_at, updated_at)
                VALUES (:id, :mark_id, :coa_id, :mapping_type, :notes, :created_at, :updated_at)
            """), {
                'id': mapping_id,
                'mark_id': mark_id,
                'coa_id': coa_id,
                'mapping_type': mapping_type,
                'notes': data.get('notes'),
                'created_at': now,
                'updated_at': now
            })
            conn.commit()
            return {'message': 'Mapping created successfully', 'id': mapping_id}, 201
    except Exception as e:
        if 'Duplicate entry' in str(e):
            return {'error': 'This mapping already exists'}, 409
        return {'error': str(e)}, 500

# Fix expense mappings MUST come before the dynamic <mapping_id> route
@app.route('/api/mark-coa-mappings/fix-expense-mappings', methods=['POST'])
def fix_expense_mappings():
    """Auto-fix all EXPENSE mappings that are incorrectly set to CREDIT"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    
    try:
        with engine.begin() as conn:
            # Find all mappings where:
            # - COA category is EXPENSE (5xxx)
            # - mapping_type is CREDIT (should be DEBIT)
            query = text("""
                SELECT mcm.id, mcm.mark_id, mcm.coa_id, mcm.mapping_type, 
                       coa.code, coa.name, coa.category, m.personal_use
                FROM mark_coa_mapping mcm
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                INNER JOIN marks m ON mcm.mark_id = m.id
                WHERE coa.category IN ('EXPENSE', 'COGS', 'OTHER_EXPENSE')
                  AND mcm.mapping_type = 'CREDIT'
            """)
            
            result = conn.execute(query)
            incorrect_mappings = list(result)
            
            if not incorrect_mappings:
                return {
                    'message': 'No incorrect mappings found',
                    'fixed_count': 0,
                    'mappings': []
                }
            
            # Update all incorrect mappings to DEBIT
            update_query = text("""
                UPDATE mark_coa_mapping
                SET mapping_type = 'DEBIT'
                WHERE id = :mapping_id
            """)
            
            fixed_mappings = []
            for mapping in incorrect_mappings:
                conn.execute(update_query, {'mapping_id': mapping.id})
                fixed_mappings.append({
                    'id': mapping.id,
                    'mark': mapping.personal_use,
                    'coa_code': mapping.code,
                    'coa_name': mapping.name,
                    'old_type': 'CREDIT',
                    'new_type': 'DEBIT'
                })
            
            return {
                'message': f'Successfully fixed {len(fixed_mappings)} expense mappings',
                'fixed_count': len(fixed_mappings),
                'mappings': fixed_mappings
            }
            
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/mark-coa-mappings/fix-revenue-mappings', methods=['POST'])
def fix_revenue_mappings():
    """Auto-fix all REVENUE mappings that are incorrectly set to DEBIT"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    
    try:
        with engine.begin() as conn:
            # Find all mappings where:
            # - COA category is REVENUE
            # - mapping_type is DEBIT (should be CREDIT)
            query = text("""
                SELECT mcm.id, mcm.mark_id, mcm.coa_id, mcm.mapping_type, 
                       coa.code, coa.name, coa.category, m.personal_use
                FROM mark_coa_mapping mcm
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                INNER JOIN marks m ON mcm.mark_id = m.id
                WHERE coa.category IN ('REVENUE', 'OTHER_REVENUE')
                  AND mcm.mapping_type = 'DEBIT'
            """)
            
            result = conn.execute(query)
            incorrect_mappings = list(result)
            
            if not incorrect_mappings:
                return {
                    'message': 'No incorrect mappings found',
                    'fixed_count': 0,
                    'mappings': []
                }
            
            # Update all incorrect mappings to CREDIT
            update_query = text("""
                UPDATE mark_coa_mapping
                SET mapping_type = 'CREDIT'
                WHERE id = :mapping_id
            """)
            
            fixed_mappings = []
            for mapping in incorrect_mappings:
                conn.execute(update_query, {'mapping_id': mapping.id})
                fixed_mappings.append({
                    'id': mapping.id,
                    'mark': mapping.personal_use,
                    'coa_code': mapping.code,
                    'coa_name': mapping.name,
                    'old_type': 'DEBIT',
                    'new_type': 'CREDIT'
                })
            
            return {
                'message': f'Successfully fixed {len(fixed_mappings)} revenue mappings',
                'fixed_count': len(fixed_mappings),
                'mappings': fixed_mappings
            }
            
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/mark-coa-mappings/<mapping_id>', methods=['DELETE'])
def delete_mark_coa_mapping(mapping_id):
    """Delete a mark-COA mapping"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM mark_coa_mapping WHERE id = :id"), {'id': mapping_id})
            conn.commit()
            return {'message': 'Mapping deleted successfully'}
    except Exception as e:
        return {'error': str(e)}, 500

# ============================================================================
# FINANCIAL REPORTS ENDPOINTS
# ============================================================================

@app.route('/api/reports/income-statement', methods=['GET'])
def get_income_statement():
    """Generate Income Statement (Laba Rugi)"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        company_id = request.args.get('company_id')
        
        if not start_date or not end_date:
            return {'error': 'start_date and end_date are required'}, 400
        
        with engine.connect() as conn:
            data = fetch_income_statement_data(conn, start_date, end_date, company_id)
            data['period'] = {'start_date': start_date, 'end_date': end_date}
            return data

    except Exception as e:
        return {'error': str(e)}, 500

def fetch_income_statement_data(conn, start_date, end_date, company_id=None):
    """
    Helper function to fetch income statement data.
    Returns calculated values and lists of items.
    """
    query = text("""
        SELECT 
            coa.code,
            coa.name,
            coa.category,
            coa.subcategory,
            SUM(
                CASE 
                    WHEN t.db_cr = 'CR' AND mcm.mapping_type = 'CREDIT' THEN t.amount
                    WHEN t.db_cr = 'CR' AND mcm.mapping_type = 'DEBIT' THEN -t.amount
                    WHEN t.db_cr = 'DB' AND mcm.mapping_type = 'DEBIT' THEN t.amount
                    WHEN t.db_cr = 'DB' AND mcm.mapping_type = 'CREDIT' THEN -t.amount
                    ELSE 0
                END
            ) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
            AND coa.category IN ('REVENUE', 'EXPENSE')
            AND (:company_id IS NULL OR t.company_id = :company_id)
        GROUP BY coa.id, coa.code, coa.name, coa.category, coa.subcategory
        ORDER BY coa.code
    """)
    
    result = conn.execute(query, {
        'start_date': start_date,
        'end_date': end_date,
        'company_id': company_id
    })
    
    revenue = []
    expenses = []
    total_revenue = 0
    total_expenses = 0
    
    for row in result:
        d = dict(row._mapping)
        amount = float(d['total_amount']) if d['total_amount'] else 0
        
        item = {
            'code': d['code'],
            'name': d['name'],
            'subcategory': d['subcategory'],
            'amount': amount,
            'category': d['category'] 
        }
        
        if d['category'] == 'REVENUE':
            revenue.append(item)
            total_revenue += amount
        else:  # EXPENSE
            expenses.append(item)
            total_expenses += amount
    
    net_income = total_revenue - total_expenses
    
    # 2. Handle COGS (HPP) with Manual Inventory Adjustments
    beginning_inv = 0
    ending_inv = 0
    
    # We use start_date's year for the inventory balance
    year = datetime.strptime(start_date, '%Y-%m-%d').year
    
    try:
        inventory_query = text("""
            SELECT beginning_inventory_amount, ending_inventory_amount
            FROM inventory_balances
            WHERE year = :year AND (:company_id IS NULL OR company_id = :company_id)
            LIMIT 1
        """)
        inv_result = conn.execute(inventory_query, {'year': year, 'company_id': company_id}).fetchone()
        if inv_result:
            beginning_inv = float(inv_result[0] or 0)
            ending_inv = float(inv_result[1] or 0)
    except Exception as e:
        app.logger.error(f"Failed to fetch inventory balances: {e}")

    # Identify 'Purchases' and 'Other COGS' from expenses
    # In CoreTax 2025, '5001' is 'Pembelian'
    purchases = 0
    other_cogs_items = []
    
    # Filter out direct COGS accounts from total_expenses for separate HPP calculation
    # COGS accounts are in subcategory 'Cost of Goods Sold' (5xxx)
    cogs_items = [e for e in expenses if e.get('subcategory') == 'Cost of Goods Sold']
    
    for item in cogs_items:
        if item['code'] == '5001':
            purchases += item['amount']
        else:
            other_cogs_items.append(item)
    
    total_other_cogs = sum(item['amount'] for item in other_cogs_items)
    calculate_hpp = beginning_inv + purchases + total_other_cogs - ending_inv
    
    # Provide a specific breakdown for the UI
    cogs_breakdown = {
        'beginning_inventory': beginning_inv,
        'purchases': purchases,
        'other_cogs_items': other_cogs_items,
        'total_other_cogs': total_other_cogs,
        'ending_inventory': ending_inv,
        'total_cogs': calculate_hpp,
        'year': year
    }

    return {
        'revenue': revenue,
        'expenses': [e for e in expenses if e.get('subcategory') != 'Cost of Goods Sold'],
        'total_revenue': total_revenue,
        'total_expenses': total_expenses - sum(e['amount'] for e in cogs_items),
        'cogs_breakdown': cogs_breakdown,
        'net_income': total_revenue - (total_expenses - sum(e['amount'] for e in cogs_items)) - calculate_hpp
    }

def fetch_monthly_revenue_data(conn, year, company_id=None):
    """
    Fetch total revenue grouped by month for a specific year.
    Used for Coretax summary.
    """
    query = text("""
        SELECT 
            MONTH(t.txn_date) as month_num,
            SUM(
                CASE 
                    WHEN t.db_cr = 'CR' AND mcm.mapping_type = 'CREDIT' THEN t.amount
                    WHEN t.db_cr = 'CR' AND mcm.mapping_type = 'DEBIT' THEN -t.amount
                    WHEN t.db_cr = 'DB' AND mcm.mapping_type = 'DEBIT' THEN t.amount
                    WHEN t.db_cr = 'DB' AND mcm.mapping_type = 'CREDIT' THEN -t.amount
                    ELSE 0
                END
            ) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE YEAR(t.txn_date) = :year
            AND coa.category = 'REVENUE'
            AND (:company_id IS NULL OR t.company_id = :company_id)
        GROUP BY MONTH(t.txn_date)
        ORDER BY month_num
    """)
    
    result = conn.execute(query, {
        'year': year,
        'company_id': company_id
    })
    
    # Initialize all months with 0
    monthly_data = {i: 0.0 for i in range(1, 13)}
    
    for row in result:
        d = dict(row._mapping)
        if d['month_num']:
            monthly_data[int(d['month_num'])] = float(d['total_amount']) if d['total_amount'] else 0.0
            
    # Convert to list of objects for easier frontend consumption
    return [
        {'month': m, 'revenue': monthly_data[m]} 
        for m in range(1, 13)
    ]

@app.route('/api/reports/monthly-revenue', methods=['GET'])
def get_monthly_revenue():
    """Get monthly revenue summary for a specific year"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
        
    try:
        year = request.args.get('year')
        company_id = request.args.get('company_id')
        
        if not year:
            year = datetime.now().year
        else:
            year = int(year)
            
        with engine.connect() as conn:
            current_data = fetch_monthly_revenue_data(conn, year, company_id)
            prev_data = fetch_monthly_revenue_data(conn, year - 1, company_id)
            return {
                'year': year, 
                'data': current_data,
                'prev_year_data': prev_data
            }
            
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/reports/export', methods=['POST'])
def export_report():
    """Export financial reports to Excel or XML (CoreTax)"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
        
    try:
        data = request.json
        report_type = data.get('report_type')
        export_format = data.get('format')
        filters = data.get('filters', {})
        
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        company_id = filters.get('company_id')
        
        if not start_date or not end_date:
            return {'error': 'start_date and end_date are required'}, 400
            
        with engine.connect() as conn:
            # 1. Fetch Data
            if report_type == 'income-statement':
                report_data = fetch_income_statement_data(conn, start_date, end_date, company_id)
            else:
                return {'error': 'Unsupported report type'}, 400
                
            # 2. Generate File
            if export_format == 'excel':
                # Create DataFrame
                rows = []
                
                # Revenue Section
                rows.append({'Code': '', 'Account': 'REVENUE', 'Subcategory': '', 'Amount': ''})
                for item in report_data['revenue']:
                    rows.append({
                        'Code': item['code'], 
                        'Account': item['name'], 
                        'Subcategory': item['subcategory'], 
                        'Amount': item['amount']
                    })
                rows.append({'Code': '', 'Account': 'Total Revenue', 'Subcategory': '', 'Amount': report_data['total_revenue']})
                rows.append({}) # Empty row
                
                # Expenses Section
                rows.append({'Code': '', 'Account': 'EXPENSES', 'Subcategory': '', 'Amount': ''})
                for item in report_data['expenses']:
                    rows.append({
                        'Code': item['code'], 
                        'Account': item['name'], 
                        'Subcategory': item['subcategory'], 
                        'Amount': item['amount']
                    })
                rows.append({'Code': '', 'Account': 'Total Expenses', 'Subcategory': '', 'Amount': report_data['total_expenses']})
                rows.append({}) # Empty row
                
                # Net Income
                rows.append({'Code': '', 'Account': 'NET INCOME', 'Subcategory': '', 'Amount': report_data['net_income']})
                
                df = pd.DataFrame(rows)
                
                # Save to buffer
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Income Statement')
                output.seek(0)
                
                filename = f"Income_Statement_{start_date}_{end_date}.xlsx"
                return send_file(
                    output,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=filename
                )
                
            elif export_format == 'xml':
                # Generate CoreTax-like XML
                root = ET.Element("FinancialReport")
                
                # Header
                header = ET.SubElement(root, "Header")
                ET.SubElement(header, "ReportType").text = "IncomeStatement"
                ET.SubElement(header, "StartDate").text = start_date
                ET.SubElement(header, "EndDate").text = end_date
                ET.SubElement(header, "GeneratedAt").text = datetime.now().isoformat()
                
                # Accounts
                accounts_elem = ET.SubElement(root, "Accounts")
                
                # Combine all items
                all_items = report_data['revenue'] + report_data['expenses']
                for item in all_items:
                    acc_elem = ET.SubElement(accounts_elem, "Account")
                    ET.SubElement(acc_elem, "Code").text = str(item['code'])
                    ET.SubElement(acc_elem, "Name").text = str(item['name'])
                    ET.SubElement(acc_elem, "Category").text = str(item['category'])
                    ET.SubElement(acc_elem, "Amount").text = str(item['amount'])
                
                # Summary
                summary = ET.SubElement(root, "Summary")
                ET.SubElement(summary, "TotalRevenue").text = str(report_data['total_revenue'])
                ET.SubElement(summary, "TotalExpenses").text = str(report_data['total_expenses'])
                ET.SubElement(summary, "NetIncome").text = str(report_data['net_income'])
                
                # Convert to string
                xml_str = ET.tostring(root, encoding='utf-8', method='xml')
                output = io.BytesIO(xml_str)
                
                filename = f"CoreTax_IncomeStatement_{start_date}_{end_date}.xml"
                return send_file(
                    output,
                    mimetype='application/xml',
                    as_attachment=True,
                    download_name=filename
                )
                
            else:
                return {'error': 'Unsupported format'}, 400
                
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/reports/coa-detail', methods=['GET'])
def get_coa_detail_report():
    """Get detailed transaction list for a specific COA"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
    
    try:
        coa_id = request.args.get('coa_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        company_id = request.args.get('company_id')
        
        if not coa_id:
            return {'error': 'coa_id is required'}, 400
        
        with engine.connect() as conn:
            # Get COA info
            coa_result = conn.execute(text("SELECT * FROM chart_of_accounts WHERE id = :id"), {'id': coa_id})
            coa_row = coa_result.fetchone()
            if not coa_row:
                return {'error': 'COA not found'}, 404
            
            coa_info = dict(coa_row._mapping)
            
            # Get transactions
            query = text("""
                SELECT 
                    t.id,
                    t.txn_date,
                    t.description,
                    t.amount,
                    t.db_cr,
                    m.personal_use as mark_name,
                    c.name as company_name,
                    mcm.mapping_type
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
                LEFT JOIN companies c ON t.company_id = c.id
                WHERE mcm.coa_id = :coa_id
                  AND (:start_date IS NULL OR t.txn_date >= :start_date)
                  AND (:end_date IS NULL OR t.txn_date <= :end_date)
                  AND (:company_id IS NULL OR t.company_id = :company_id)
                ORDER BY t.txn_date DESC
            """)
            
            result = conn.execute(query, {
                'coa_id': coa_id,
                'start_date': start_date,
                'end_date': end_date,
                'company_id': company_id
            })
            
            transactions = []
            total = 0
            
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, Decimal):
                        d[key] = float(value)
                
                # Calculate effective amount based on mapping type
                amount = float(d['amount'])
                if d['db_cr'] == 'CR' and d['mapping_type'] == 'CREDIT':
                    effective_amount = amount
                elif d['db_cr'] == 'CR' and d['mapping_type'] == 'DEBIT':
                    effective_amount = -amount
                elif d['db_cr'] == 'DB' and d['mapping_type'] == 'DEBIT':
                    effective_amount = amount
                else:  # DB and CREDIT
                    effective_amount = -amount
                
                d['effective_amount'] = effective_amount
                total += effective_amount
                transactions.append(d)
            
            return {
                'coa': {
                    'code': coa_info['code'],
                    'name': coa_info['name'],
                    'category': coa_info['category']
                },
                'transactions': transactions,
                'total': total
            }
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/inventory-balances', methods=['GET'])
def get_inventory_balances():
    """Retrieve inventory balances for a specific year and company"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
        
    try:
        year = request.args.get('year')
        company_id = request.args.get('company_id')
        
        if not year or not company_id:
            return {'error': 'year and company_id are required'}, 400
            
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM inventory_balances WHERE year = :year AND company_id = :company"),
                {'year': year, 'company': company_id}
            )
            row = result.fetchone()
            if row:
                d = dict(row._mapping)
                # Convert Decimals to floats
                for key, value in d.items():
                    if isinstance(value, Decimal):
                        d[key] = float(value)
                    elif isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                return {'balance': d}
            return {'balance': {}}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/inventory-balances', methods=['POST'])
def save_inventory_balances():
    """Save or update inventory balances"""
    data = request.json
    company_id = data.get('company_id')
    year = data.get('year')
    
    if not company_id or not year:
        return {'error': 'company_id and year are required'}, 400
        
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
        
    try:
        balance_id = str(uuid.uuid4())
        with engine.begin() as conn:
            # UPSERT logic for MySQL
            conn.execute(
                text("""
                    INSERT INTO inventory_balances 
                        (id, company_id, year, beginning_inventory_amount, beginning_inventory_qty, 
                         ending_inventory_amount, ending_inventory_qty, is_manual) 
                    VALUES 
                        (:id, :company, :year, :beg_amt, :beg_qty, :end_amt, :end_qty, :is_manual)
                    ON DUPLICATE KEY UPDATE 
                        beginning_inventory_amount = VALUES(beginning_inventory_amount),
                        beginning_inventory_qty = VALUES(beginning_inventory_qty),
                        ending_inventory_amount = VALUES(ending_inventory_amount),
                        ending_inventory_qty = VALUES(ending_inventory_qty),
                        is_manual = VALUES(is_manual),
                        updated_at = NOW()
                """),
                {
                    'id': balance_id,
                    'company': company_id,
                    'year': year,
                    'beg_amt': data.get('beginning_inventory_amount', 0),
                    'beg_qty': data.get('beginning_inventory_qty', 0),
                    'end_amt': data.get('ending_inventory_amount', 0),
                    'end_qty': data.get('ending_inventory_qty', 0),
                    'is_manual': data.get('is_manual', True)
                }
            )
            return {'success': True}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/filters/<view_name>', methods=['GET'])
def get_view_filters(view_name):
    """Retrieve saved filters for a specific view"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
        
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT filters FROM user_filters WHERE view_name = :view"),
                {'view': view_name}
            )
            row = result.fetchone()
            if row:
                # SQLAlchemy JSON column might return dict or string depending on driver/version
                filters = row[0]
                if isinstance(filters, str):
                    import json
                    filters = json.loads(filters)
                return {'filters': filters}
            return {'filters': {}}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/filters', methods=['POST'])
def save_view_filters():
    """Save filters for a specific view"""
    data = request.json
    view_name = data.get('view_name')
    filters = data.get('filters')
    
    if not view_name or filters is None:
        return {'error': 'view_name and filters are required'}, 400
        
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
        
    try:
        import json
        filters_json = json.dumps(filters)
        with engine.connect() as conn:
            # UPSERT logic for MySQL
            conn.execute(
                text("""
                    INSERT INTO user_filters (view_name, filters) 
                    VALUES (:view, :filters)
                    ON DUPLICATE KEY UPDATE filters = :filters, updated_at = NOW()
                """),
                {'view': view_name, 'filters': filters_json}
            )
            conn.commit()
            return {'success': True}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/transactions/<transaction_id>/notes', methods=['PUT'])
def update_transaction_notes(transaction_id):
    data = request.json
    notes = data.get('notes')
    
    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}, 500
        
    try:
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE transactions SET notes = :notes, updated_at = NOW() WHERE id = :id"),
                {'notes': notes, 'id': transaction_id}
            )
            conn.commit()
            return {'success': True}
    except Exception as e:
        return {'error': str(e)}, 500

if __name__ == '__main__':
    # Run migrations on startup
    run_migrations()
    
    # Get port from environment variable with a default of 5001
    port = int(os.environ.get('PORT', 5001))
    # In production, disable debug mode
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
