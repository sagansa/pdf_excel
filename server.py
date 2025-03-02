from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import os
from app import process_statement

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'pdfs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert_pdf', methods=['POST'])
def convert_pdf():
    if 'pdf_file' not in request.files:
        return 'No file uploaded', 400
    
    file = request.files['pdf_file']
    if file.filename == '':
        return 'No file selected', 400
    
    if not file.filename.lower().endswith('.pdf'):
        return 'Invalid file type. Please upload a PDF file', 400
    
    try:
        # Save the uploaded PDF
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)
        
        # Process the PDF and create Excel file
        excel_output = os.path.join('excel', f'{os.path.splitext(filename)[0]}.xlsx')
        process_statement(pdf_path, excel_output)
        
        # Send the Excel file back to the client
        return send_file(excel_output, as_attachment=True)
    
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)