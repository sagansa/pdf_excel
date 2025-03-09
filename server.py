from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import os
from app import parse_bca_statement
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
        # Parse the PDF and get the dataframe
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
        
        # Clean up temporary files
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            
        return response
    
    except Exception as e:
        # Clean up temporary files
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            os.remove(pdf_path)
        return {'error': str(e)}, 500, {'Content-Type': 'application/json'}

if __name__ == '__main__':
    app.run(debug=True, port=5001)