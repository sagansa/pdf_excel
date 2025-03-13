from flask import Flask, render_template, request, send_file
import os
import pandas as pd
import pdfplumber
from bank_parsers import bca, mandiri, dbs

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert_pdf', methods=['POST'])
def convert_pdf():
    if 'pdf_file' not in request.files:
        return {'error': 'No file uploaded'}, 400
    
    file = request.files['pdf_file']
    if file.filename == '':
        return {'error': 'No file selected'}, 400
    
    if not file.filename.lower().endswith('.pdf'):
        return {'error': 'Invalid file type. Please upload a PDF file'}, 400
    
    # Get bank type from form data (default to BCA if not specified)
    bank_type = request.form.get('bank_type', 'bca')
    
    # Validate bank type first
    if bank_type.lower() not in ['bca', 'mandiri', 'dbs']:
        return {'error': 'Invalid bank type. Please ensure you are using the correct converter page.'}, 400
    
    # Create necessary directories
    os.makedirs('pdfs', exist_ok=True)
    os.makedirs('excel', exist_ok=True)
    
    pdf_path = os.path.join('pdfs', file.filename)
    excel_path = None
    
    try:
        # Save uploaded file
        file.save(pdf_path)
        
        # Parse statement based on bank type
        if bank_type.lower() == 'mandiri':
            df = mandiri.parse_statement(pdf_path)
        elif bank_type.lower() == 'dbs':
            password = request.form.get('password')
            df = dbs.parse_statement(pdf_path, password)
        else:  # Default to BCA
            df = bca.parse_statement(pdf_path)
        
        # Generate output filename
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        excel_path = os.path.join('excel', f'{base_name}.xlsx')
        
        # Save to Excel
        df.to_excel(excel_path, index=False)
        
        return send_file(excel_path, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    except pdfplumber.PDFSyntaxError:
        return {'error': 'The PDF file appears to be corrupted or invalid. Please ensure you are uploading a valid bank statement.'}, 400
    except pd.errors.EmptyDataError:
        return {'error': 'No transaction data could be extracted from the PDF. Please ensure this is a valid bank statement.'}, 400
    except ValueError as e:
        return {'error': str(e)}, 400
    except Exception as e:
        return {'error': f'An unexpected error occurred while processing your PDF: {str(e)}'}, 400
    finally:
        # Clean up temporary files
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

if __name__ == '__main__':
    app.run(debug=True)