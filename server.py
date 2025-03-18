from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import os
from bank_parsers import bca, mandiri, dbs, bca_cc, mandiri_cc
import pandas as pd
import pdfplumber
from flask_cors import CORS

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
        
        # Create necessary directories
        os.makedirs('pdfs', exist_ok=True)
        os.makedirs('excel', exist_ok=True)
        
        # Save the uploaded PDF
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)
        
        # Process the PDF and create Excel file
        excel_output = os.path.join('excel', f'{os.path.splitext(filename)[0]}.xlsx')
        
        try:
            # Parse the PDF based on bank type
            if bank_type.lower() == 'mandiri':
                df = mandiri.parse_statement(pdf_path)
            elif bank_type.lower() == 'dbs':
                df = dbs.parse_statement(pdf_path)
            elif bank_type.lower() == 'ccbca':
                df = bca_cc.parse_statement(pdf_path)
            elif bank_type.lower() == 'ccmandiri':
                df = mandiri_cc.parse_statement(pdf_path)
            else:  # Default to BCA
                df = bca.parse_statement(pdf_path)
                
            # Save to Excel
            df.to_excel(excel_output, index=False)
            
            # Send the Excel file back to the client
            response = send_file(
                excel_output,
                as_attachment=True,
                download_name=f'{os.path.splitext(filename)[0]}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            return response
            
        except ValueError as e:
            return {'error': str(e)}, 400, {'Content-Type': 'application/json'}
        except pdfplumber.PDFSyntaxError:
            return {'error': 'Invalid or corrupted PDF file. Please ensure this is a valid bank statement in PDF format.'}, 400, {'Content-Type': 'application/json'}
        except pd.errors.EmptyDataError:
            return {'error': 'Could not extract data from the PDF file. Please ensure this is a valid bank statement with transaction data.'}, 400, {'Content-Type': 'application/json'}
        except PermissionError:
            return {'error': 'Permission denied while processing the file. Please try again.'}, 500, {'Content-Type': 'application/json'}
        except Exception as e:
            app.logger.error(f'Unexpected error processing PDF: {str(e)}')
            return {'error': 'An unexpected error occurred while processing the PDF. Please try again or contact support if the issue persists.'}, 500, {'Content-Type': 'application/json'}
            
    except Exception as e:
        return {'error': f'Server error: {str(e)}'}, 500, {'Content-Type': 'application/json'}
        
    finally:
        # Clean up temporary files
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception:
                pass
            
        if 'excel_output' in locals() and os.path.exists(excel_output):
            try:
                os.remove(excel_output)
            except Exception:
                pass

if __name__ == '__main__':
    # Get port from environment variable with a default of 5001
    port = int(os.environ.get('PORT', 5001))
    # In production, disable debug mode
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)