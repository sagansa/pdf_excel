from flask import Flask, render_template, request, send_file
import os
import pandas as pd
import re
import pdfplumber

app = Flask(__name__)

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
    
    # Create necessary directories
    os.makedirs('pdfs', exist_ok=True)
    os.makedirs('excel', exist_ok=True)
    
    pdf_path = os.path.join('pdfs', file.filename)
    file.save(pdf_path)
    
    try:
        # Parse statement
        df = parse_bca_statement(pdf_path)
        
        # Generate output filename
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join('excel', f'{base_name}.xlsx')
        
        # Save to Excel
        df.to_excel(output_path, index=False)
        
        return send_file(output_path, as_attachment=True)
    
    except Exception as e:
        return f'Error: {str(e)}', 400
    finally:
        # Clean up
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

def parse_bca_statement(pdf_path):
    transactions = []
    current_transaction = None
    header_found = False
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Debug table structure
            table_settings = {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "min_words_vertical": 3,
                "min_words_horizontal": 2,
                "snap_tolerance": 3,
                "snap_x_tolerance": 2,
                "snap_y_tolerance": 3,
                "join_tolerance": 3,
                "edge_min_length": 3,
                "min_words_horizontal": 2
            }
            
            # Get table structure for debugging
            tables = page.debug_tablefinder(table_settings)
            
            # Extract text with position information
            words = page.extract_words(
                keep_blank_chars=True,
                x_tolerance=3,
                y_tolerance=3,
                use_text_flow=True
            )

            # Group words by y-position (rows)
            rows = {}
            for word in words:
                y = round(word['top'])
                if y not in rows:
                    rows[y] = []
                rows[y].append(word)
            
            # Sort rows by y-position
            sorted_rows = sorted(rows.items())
            
            for y, row_words in sorted_rows:
                # Sort words in row by x-position
                row_words.sort(key=lambda w: w['x0'])
                
                # Skip header rows
                if any(header in ' '.join(w['text'] for w in row_words) 
                      for header in ['TANGGAL', 'KETERANGAN', 'CBG', 'MUTASI', 'SALDO']):
                    header_found = True
                    continue
                
                if not header_found:
                    continue
                
                try:
                    # Process row words into transaction
                    line = ' '.join(w['text'] for w in row_words)
                    date_match = re.search(r'(\d{2}/\d{2})', line[:6])
                    
                    if date_match:
                        if current_transaction:
                            process_transaction(transactions, current_transaction)
                        
                        # Use x-positions to determine field boundaries
                        current_transaction = {
                            'date': date_match.group(1),
                            'keterangan1': '',
                            'keterangan2': '',
                            'cbg': '',
                            'mutasi': '',
                            'saldo': ''
                        }
                        
                        # Group words into fields based on x-position
                        for word in row_words:
                            x = word['x0']
                            if x < 50:  # Date field
                                continue
                            elif x > 50 and x < 300:  # Keterangan fields
                                if not current_transaction['keterangan1']:
                                    current_transaction['keterangan1'] = word['text'][:18]
                                else:
                                    current_transaction['keterangan2'] = word['text'][:18]
                            elif x > 300 and x < 500:  # Mutasi field
                                # Collect all parts of the mutasi value
                                if current_transaction['mutasi']:
                                    current_transaction['mutasi'] += ' ' + word['text']
                                else:
                                    current_transaction['mutasi'] = word['text']
                                
                                # Format the complete mutasi value
                                if current_transaction['mutasi']:
                                    if 'DB' in current_transaction['mutasi']:
                                        # Handle debit transactions
                                        amount = current_transaction['mutasi'].replace('DB', '').strip()
                                        current_transaction['mutasi'] = amount
                                        current_transaction['db_cr'] = 'DB'
                                    else:
                                        # Handle credit transactions
                                        current_transaction['mutasi'] = current_transaction['mutasi'].strip()
                                        current_transaction['db_cr'] = 'CR'

                            elif x > 500:  # Saldo field
                                current_transaction['saldo'] = word['text'][:20]
                    elif current_transaction and line.strip():
                        current_transaction['keterangan2'] = (current_transaction['keterangan2'] + ' ' + line.strip())[:18]
                
                except (IndexError, ValueError):
                    continue
            
            if current_transaction:
                process_transaction(transactions, current_transaction)
                current_transaction = None
    
    return pd.DataFrame(transactions) if transactions else pd.DataFrame(columns=['Tanggal', 'Keterangan 1', 'Keterangan 2', 'CBG', 'Mutasi', 'Saldo'])

def process_transaction(transactions, transaction):
    transactions.append({
        'Tanggal': transaction['date'],
        'Keterangan 1': transaction['keterangan1'].strip(),
        'Keterangan 2': transaction['keterangan2'].strip(),
        'CBG': transaction['cbg'].strip(),
        'Mutasi': transaction['mutasi'].strip(),
        'DB/CR': transaction.get('db_cr', 'CR'),  # Default to CR if not specified
        'Saldo': transaction['saldo'].strip()
    })

if __name__ == '__main__':
    app.run(debug=True)