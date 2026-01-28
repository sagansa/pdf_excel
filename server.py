from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import os
import re
from datetime import datetime
from typing import Dict, List, Optional
from bank_parsers import bca, mandiri, dbs, bca_cc, mandiri_cc
import pandas as pd
import pdfplumber
from flask_cors import CORS
import PyPDF2
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

def standardize_bca_dates(df: pd.DataFrame, pdf_path: str, default_year: Optional[int] = None) -> pd.DataFrame:
    """Convert BCA statement dates (DD/MM) into ISO format with inferred year."""
    if df is None or df.empty or 'Tanggal' not in df.columns:
        return df

    inferred_year = default_year or infer_year_from_pdf(pdf_path) or infer_year_from_filename(pdf_path)
    current_year = inferred_year or datetime.now().year
    last_month = None
    iso_dates: List[str] = []

    for raw_value in df['Tanggal']:
        if raw_value is None:
            iso_dates.append(raw_value)
            continue

        match = re.match(r'^\s*([0-3]\d)/([0-1]\d)\s*$', str(raw_value))
        if not match:
            iso_dates.append(raw_value)
            continue

        day = int(match.group(1))
        month = int(match.group(2))

        if not (1 <= day <= 31 and 1 <= month <= 12):
            iso_dates.append(raw_value)
            continue

        if last_month is not None and month < last_month:
            current_year += 1
        last_month = month

        try:
            iso_dates.append(datetime(current_year, month, day).strftime('%Y-%m-%d'))
        except ValueError:
            iso_dates.append(raw_value)

    df = df.copy()
    df['Tanggal'] = iso_dates
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

    # Already in ISO format
    match_iso = re.match(r'^(\d{4})[-/](\d{2})[-/](\d{2})$', text)
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
            return {'error': 'No file uploaded. Please select a PDF file.'}, 400, {'Content-Type': 'application/json'}
        
        file = request.files['pdf_file']
        if file.filename == '':
            return {'error': 'No file selected. Please choose a PDF file to upload.'}, 400, {'Content-Type': 'application/json'}
        
        if not file.filename.lower().endswith('.pdf'):
            return {'error': 'Invalid file type. Please upload a PDF file.'}, 400, {'Content-Type': 'application/json'}
            
        # Validate file size (max 10MB)
        if len(file.read()) > 10 * 1024 * 1024:  # 10MB in bytes
            return {'error': 'File size too large. Maximum file size is 10MB.'}, 400, {'Content-Type': 'application/json'}
        file.seek(0)  # Reset file pointer after reading

        # Get bank type from form data
        bank_type = request.form.get('bank_type', 'bca')
        
        # Ensure upload directory exists
        os.makedirs('pdfs', exist_ok=True)
        
        # Save the uploaded PDF
        filename = secure_filename(file.filename)
        original_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(original_pdf_path)
        pdf_path = original_pdf_path
        
        # Handle password-protected PDFs (optional)
        password = request.form.get('password', '')
        password = password.strip() if password else None
        requires_password = False

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

        inferred_year = infer_year_from_pdf(pdf_path) or infer_year_from_filename(original_pdf_path)
        
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

        base_name = os.path.splitext(filename)[0]
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
        
        try:
            # Parse the PDF based on bank type
            bank_key = bank_type.lower()
            if bank_key == 'mandiri':
                df = mandiri.parse_statement(pdf_path)
            elif bank_key == 'dbs':
                df = dbs.parse_statement(pdf_path)
            elif bank_key == 'ccbca':
                df = bca_cc.parse_statement(pdf_path)
            elif bank_key == 'ccmandiri':
                df = mandiri_cc.parse_statement(pdf_path)
            else:  # Default to BCA
                df = bca.parse_statement(pdf_path)
                df = standardize_bca_dates(df, pdf_path, inferred_year)

            original_name = os.path.basename(original_pdf_path)
            if 'source_file' in df.columns:
                df['source_file'] = original_name
                
            if bank_key not in {'dbs'}:
                df = normalize_date_columns(df, inferred_year)
                
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

if __name__ == '__main__':
    # Get port from environment variable with a default of 5001
    port = int(os.environ.get('PORT', 5001))
    # In production, disable debug mode
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
