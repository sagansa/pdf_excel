import re
import os
import pdfplumber
import pandas as pd
from datetime import datetime

def parse_statement(pdf_path):
    if not os.path.exists(pdf_path):
        raise ValueError("PDF file not found")
        
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")
        
    transactions = []
    current_transaction = None
    header_found = False
    
    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                raise ValueError("PDF file is empty or corrupted. Please ensure the file is a valid BCA statement")
            
            # Additional validation for PDF integrity
            try:
                # Try to access PDF metadata to verify basic PDF structure
                _ = pdf.metadata
                # Verify that pages are accessible and contain content
                for page in pdf.pages:
                    if not hasattr(page, 'extract_words'):
                        raise ValueError("PDF file appears to be corrupted. Unable to extract content from pages.")
            except Exception as e:
                raise ValueError(f"PDF file validation failed. The file may be corrupted: {str(e)}")

                
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
                    'SALDO AWAL :',
                    'MUTASI CR :',
                    'MUTASI DB :',
                    'SALDO AKHIR :'
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
                    
                    # Skip header rows with more robust detection
                    header_line = ' '.join(w['text'].upper() for w in row_words)
                    if 'TANGGAL' in header_line and ('KETERANGAN' in header_line or 'MUTASI' in header_line):
                        header_found = True
                        continue
                    
                    if not header_found:
                        continue
                    
                    try:
                        # Process row words into transaction
                        line = ' '.join(w['text'] for w in row_words)
                        # Skip if line contains any footer markers
                        if any(marker.upper() in line.upper() for marker in footer_markers):
                            continue
                        
                        # Enhanced date pattern matching for DD/MM format
                        date_match = re.match(r'^s*([0-3][0-9]/[0-1][0-9])s*', line)
                        
                        if date_match and len(date_match.group(1)) == 5:  # Ensure exact DD/MM format
                            # Validate date components
                            day, month = map(int, date_match.group(1).split('/'))
                            if 1 <= day <= 31 and 1 <= month <= 12:
                                if current_transaction:
                                    process_transaction(transactions, current_transaction, conversion_timestamp)
                                
                                # Initialize new transaction with date
                                current_transaction = {
                                    'date': date_match.group(1),
                                    'keterangan1': '',
                                    'keterangan2': '',
                                    'cbg': '',
                                    'mutasi': '',
                                    'saldo': ''
                                }
                                
                                # Process fields for the row with date
                                for word in row_words:
                                    x = word['x0']
                                    text = word['text']
                                    if x < 75:  # Date field
                                        continue
                                    elif x >= 75 and x < 180:  # Keterangan1 field
                                        current_transaction['keterangan1'] = text[:36]
                                    elif x >= 180 and x < 300:  # Keterangan2 field
                                        current_transaction['keterangan2'] = text[:90]
                                    elif x >= 300 and x < 320:  # CBG field
                                        if current_transaction['cbg']:
                                            current_transaction['cbg'] += ' ' + text
                                        else:
                                            current_transaction['cbg'] = text
                                    elif x >= 320 and x < 430:  # Mutasi field
                                        if current_transaction['mutasi']:
                                            current_transaction['mutasi'] += ' ' + text
                                        else:
                                            current_transaction['mutasi'] = text
                                    elif x >= 430 and x < 500:  # DB/CR indicator field
                                        text_upper = text.strip().upper()
                                        if text_upper == 'D' or text_upper == 'DB':
                                            current_transaction['db_cr'] = 'DB'
                                        else:
                                            current_transaction['db_cr'] = 'CR'
                                    elif x >= 500:  # Saldo field
                                        if current_transaction['saldo']:
                                            current_transaction['saldo'] += ' ' + text
                                        else:
                                            current_transaction['saldo'] = text
                                        current_transaction['saldo'] = text[:20]
                        else:
                            # Handle rows without date by concatenating to current transaction
                            if current_transaction:
                                for word in row_words:
                                    x = word['x0']
                                    text = word['text'].strip()
                                    if x >= 75 and x < 180:
                                        if current_transaction['keterangan1']:
                                            current_transaction['keterangan1'] = (current_transaction['keterangan1'] + ' ' + text)[:36]
                                        else:
                                            current_transaction['keterangan1'] = text[:36]
                                    elif x >= 180 and x < 300:
                                        if current_transaction['keterangan2']:
                                            current_transaction['keterangan2'] = (current_transaction['keterangan2'] + ' ' + text)[:90]
                                        else:
                                            current_transaction['keterangan2'] = text[:90]
                                    elif x >= 300 and x < 320:  # CBG field
                                        if current_transaction['cbg']:
                                            current_transaction['cbg'] += ' ' + text
                                        else:
                                            current_transaction['cbg'] = text
                                    elif x >= 320 and x < 430:  # Mutasi field
                                        if current_transaction['mutasi']:
                                            current_transaction['mutasi'] += ' ' + text
                                        else:
                                            current_transaction['mutasi'] = text
                                    elif x >= 430 and x < 500:  # DB/CR indicator field
                                        if text.strip().upper() == 'D':
                                            current_transaction['db_cr'] = 'DB'
                                    elif x >= 500:  # Saldo field
                                        current_transaction['saldo'] = text[:20]
                    except (IndexError, ValueError) as e:
                        # Log the error and continue with next row
                        print(f"Error processing row: {str(e)}")
                        continue
                
                if current_transaction:
                    process_transaction(transactions, current_transaction, conversion_timestamp)
                    current_transaction = None
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    if not transactions:
        raise ValueError("No transaction data found in the PDF. Please ensure this is a valid BCA statement")
        
    return pd.DataFrame(transactions) if transactions else pd.DataFrame(columns=['Tanggal', 'Keterangan 1', 'Keterangan 2', 'CBG', 'Mutasi', 'DB/CR', 'Saldo'])

def process_transaction(transactions, transaction, conversion_timestamp):
    transactions.append({
        'Tanggal': transaction['date'],
        'Keterangan 1': transaction['keterangan1'].strip(),
        'Keterangan 2': transaction['keterangan2'].strip(),
        'CBG': transaction['cbg'].strip(),
        'Mutasi': transaction['mutasi'].strip(),
        'DB/CR': transaction.get('db_cr', 'CR'),  # Default to CR if not specified
        'Saldo': transaction['saldo'].strip(),
        'created_at': conversion_timestamp
    })
