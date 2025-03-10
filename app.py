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
        return {'error': 'No file uploaded'}, 400
    
    file = request.files['pdf_file']
    if file.filename == '':
        return {'error': 'No file selected'}, 400
    
    if not file.filename.lower().endswith('.pdf'):
        return {'error': 'Invalid file type. Please upload a PDF file'}, 400
    
    # Create necessary directories
    os.makedirs('pdfs', exist_ok=True)
    os.makedirs('excel', exist_ok=True)
    
    pdf_path = os.path.join('pdfs', file.filename)
    excel_path = None
    
    try:
        # Save uploaded file
        file.save(pdf_path)
        
        # Parse statement
        df = parse_bca_statement(pdf_path)
        
        # Generate output filename
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        excel_path = os.path.join('excel', f'{base_name}.xlsx')
        
        # Save to Excel
        df.to_excel(excel_path, index=False)
        
        return send_file(excel_path, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    except pdfplumber.PDFSyntaxError:
        return {'error': 'Invalid or corrupted PDF file'}, 400
    except pd.errors.EmptyDataError:
        return {'error': 'Could not extract data from the PDF file'}, 400
    except Exception as e:
        return {'error': f'Error processing file: {str(e)}'}, 400
    finally:
        # Clean up temporary files
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

            # Add footer markers
            footer_markers = [
                'TRANSAKSI TIDAK TERSEDIA',
                'bersambung ke halaman berikut',
            ]
            
            # Group words by y-position (rows)
            rows = {}
            for word in words:
                # Skip if line contains any footer markers
                line_text = word['text'].upper()  # Convert to uppercase for better matching
                if any(marker.upper() in line_text for marker in footer_markers):
                    header_found = False  # Reset header flag when footer is found
                    continue
                    
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
                            text = word['text']
                            if x < 50:  # Date field
                                continue
                            elif x > 50 and x < 175:  # Keterangan1 field
                                current_transaction['keterangan1'] = text[:36]
                            elif x > 175 and x < 300:  # Keterangan2 field
                                current_transaction['keterangan2'] = text[:90]
                            elif x > 300 and x < 500:  # Mutasi field
                                if current_transaction['mutasi']:
                                    current_transaction['mutasi'] += ' ' + text
                                else:
                                    current_transaction['mutasi'] = text
                                
                                if 'DB' in current_transaction['mutasi']:
                                    amount = current_transaction['mutasi'].replace('DB', '').strip()
                                    current_transaction['mutasi'] = amount
                                    current_transaction['db_cr'] = 'DB'
                                else:
                                    current_transaction['mutasi'] = current_transaction['mutasi'].strip()
                                    current_transaction['db_cr'] = 'CR'
                            elif x > 500:  # Saldo field
                                current_transaction['saldo'] = text[:20]
                    else:
                        # Handle rows without date by concatenating to current transaction
                        if current_transaction:
                            for word in row_words:
                                x = word['x0']
                                text = word['text'].strip()
                                if x > 50 and x < 175:
                                    if current_transaction['keterangan1']:
                                        current_transaction['keterangan1'] = (current_transaction['keterangan1'] + ' ' + text)[:36]
                                    else:
                                        current_transaction['keterangan1'] = text[:36]
                                elif x > 175 and x < 300:
                                    if current_transaction['keterangan2']:
                                        current_transaction['keterangan2'] = (current_transaction['keterangan2'] + ' ' + text)[:90]
                                    else:
                                        current_transaction['keterangan2'] = text[:90]
                                elif x > 300 and x < 500:  # Mutasi field
                                    if current_transaction['mutasi']:
                                        current_transaction['mutasi'] += ' ' + text
                                    else:
                                        current_transaction['mutasi'] = text
                                elif x > 500:  # Saldo field
                                    current_transaction['saldo'] = text[:20]
                            
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

def parse_mandiri_statement(pdf_path):
    transactions = []
    current_transaction = None
    header_found = False
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extract text with position information
            words = page.extract_words(
                keep_blank_chars=True,
                x_tolerance=3,
                y_tolerance=3,
                use_text_flow=True
            )

            # Add footer markers for Mandiri statements
            footer_markers = [
                'HALAMAN BERIKUTNYA',
                'SALDO AKHIR',
                'INFORMASI TAMBAHAN'
            ]
            
            # Group words by y-position (rows)
            rows = {}
            for word in words:
                # Skip if line contains any footer markers
                line_text = word['text'].upper()  # Convert to uppercase for better matching
                if any(marker.upper() in line_text for marker in footer_markers):
                    header_found = False  # Reset header flag when footer is found
                    continue
                    
                y = round(word['top'])
                if y not in rows:
                    rows[y] = []
                rows[y].append(word)
            
            # Sort rows by y-position
            sorted_rows = sorted(rows.items())
            
            for y, row_words in sorted_rows:
                # Sort words in row by x-position
                row_words.sort(key=lambda w: w['x0'])
                
                # Skip header rows - Mandiri specific headers
                if any(header in ' '.join(w['text'] for w in row_words) 
                      for header in ['TANGGAL', 'KETERANGAN', 'DEBET', 'KREDIT', 'SALDO']):
                    header_found = True
                    continue
                
                if not header_found:
                    continue
                
                try:
                    # Process row words into transaction
                    line = ' '.join(w['text'] for w in row_words)
                    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', line[:12])
                    
                    if date_match:
                        if current_transaction:
                            process_mandiri_transaction(transactions, current_transaction)
                        
                        # Use x-positions to determine field boundaries for Mandiri format
                        current_transaction = {
                            'date': date_match.group(1),
                            'keterangan': '',
                            'debet': '',
                            'kredit': '',
                            'saldo': ''
                        }
                        
                        # Group words into fields based on x-position - adjusted for Mandiri format
                        for word in row_words:
                            x = word['x0']
                            text = word['text']
                            if x < 80:  # Date field
                                continue
                            elif x > 80 and x < 300:  # Keterangan field
                                current_transaction['keterangan'] = text[:120]
                            elif x > 300 and x < 400:  # Debet field
                                current_transaction['debet'] = text[:20]
                            elif x > 400 and x < 500:  # Kredit field
                                current_transaction['kredit'] = text[:20]
                            elif x > 500:  # Saldo field
                                current_transaction['saldo'] = text[:20]
                    else:
                        # Handle rows without date by concatenating to current transaction
                        if current_transaction:
                            for word in row_words:
                                x = word['x0']
                                text = word['text'].strip()
                                if x > 80 and x < 300:
                                    if current_transaction['keterangan']:
                                        current_transaction['keterangan'] = (current_transaction['keterangan'] + ' ' + text)[:120]
                                    else:
                                        current_transaction['keterangan'] = text[:120]
                                elif x > 300 and x < 400:  # Debet field
                                    current_transaction['debet'] = text[:20]
                                elif x > 400 and x < 500:  # Kredit field
                                    current_transaction['kredit'] = text[:20]
                                elif x > 500:  # Saldo field
                                    current_transaction['saldo'] = text[:20]
                            
                except (IndexError, ValueError):
                    continue
            
            if current_transaction:
                process_mandiri_transaction(transactions, current_transaction)
                current_transaction = None
    
    return pd.DataFrame(transactions) if transactions else pd.DataFrame(columns=['Tanggal', 'Keterangan', 'Debet', 'Kredit', 'Saldo'])

def process_mandiri_transaction(transactions, transaction):
    transactions.append({
        'Tanggal': transaction['date'],
        'Keterangan': transaction['keterangan'].strip(),
        'Debet': transaction['debet'].strip(),
        'Kredit': transaction['kredit'].strip(),
        'Saldo': transaction['saldo'].strip()
    })

if __name__ == '__main__':
    app.run(debug=True)