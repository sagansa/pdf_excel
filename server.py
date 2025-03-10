from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import os
from app import parse_bca_statement, parse_mandiri_statement
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
    return render_template('index.html')

@app.route('/convert_pdf', methods=['POST', 'OPTIONS'])
def convert_pdf():
    # Handle preflight OPTIONS request for CORS
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
        
    if 'pdf_file' not in request.files:
        return {'error': 'No file uploaded'}, 400, {'Content-Type': 'application/json'}
    
    file = request.files['pdf_file']
    if file.filename == '':
        return {'error': 'No file selected'}, 400, {'Content-Type': 'application/json'}
    
    if not file.filename.lower().endswith('.pdf'):
        return {'error': 'Invalid file type. Please upload a PDF file'}, 400, {'Content-Type': 'application/json'}
    
    # Get bank type from form data (default to BCA if not specified)
    bank_type = request.form.get('bank_type', 'bca')
    
    try:
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
                df = parse_mandiri_statement(pdf_path)
            else:  # Default to BCA
                df = parse_bca_statement(pdf_path)
                
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
            
        except pdfplumber.PDFSyntaxError:
            return {'error': 'Invalid or corrupted PDF file'}, 400, {'Content-Type': 'application/json'}
        except pd.errors.EmptyDataError:
            return {'error': 'Could not extract data from the PDF file'}, 400, {'Content-Type': 'application/json'}
        except Exception as e:
            return {'error': f'Error processing PDF: {str(e)}'}, 500, {'Content-Type': 'application/json'}
            
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
    app.run(debug=True, port=5001)