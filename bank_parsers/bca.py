import re
import os
import pdfplumber
import pandas as pd

def parse_statement(pdf_path):
    if not os.path.exists(pdf_path):
        raise ValueError("PDF file not found")
        
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")
        
    transactions = []
    current_transaction = None
    header_found = False
    
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
                    except (IndexError, ValueError) as e:
                        # Log the error and continue with next row
                        print(f"Error processing row: {str(e)}")
                        continue
                
                if current_transaction:
                    process_transaction(transactions, current_transaction)
                    current_transaction = None
    except pdfplumber.PDFSyntaxError as e:
        raise ValueError(f"Invalid PDF format: {str(e)}")
    except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as e:
        raise ValueError(f"PDF parsing error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    if not transactions:
        raise ValueError("No transaction data found in the PDF. Please ensure this is a valid BCA statement")
        
    return pd.DataFrame(transactions) if transactions else pd.DataFrame(columns=['Tanggal', 'Keterangan 1', 'Keterangan 2', 'CBG', 'Mutasi', 'DB/CR', 'Saldo'])

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