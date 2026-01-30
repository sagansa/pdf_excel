import pdfplumber
import pandas as pd
import re
from datetime import datetime

def parse_statement(pdf_path, password=None):
    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    transactions = []
    header_found = False
    current_transaction = None
    last_y = 0
    MAX_Y_GAP = 15  # Maximum vertical space to consider a line a continuation
    
    # Text fragments that indicate a line is footer/info text, not transaction detail
    BLACKLIST = [
        'CONTINUE TO NEXT PAGE', 'IMPORTANT!', 'USE YOUR PIN', 'TO SET OR CHANGE',
        'LOG IN TO YOUR', 'VISIT HTTPS', 'DBS CUSTOMER CENTRE', 'TOTAL TRANSAKSI',
        'POIN SEKARANG', 'BUNGA DAN', 'PEMBAYARAN DAN KREDIT'
    ]
    
    try:
        # Open PDF with password if provided
        with pdfplumber.open(pdf_path, password=password) as pdf:
            for page in pdf.pages:
                # Reset vertical tracking for each page
                last_y = 0
                
                # Extract text with position information
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3
                )
                
                # Group words by y-position (rows)
                rows = {}
                for word in words:
                    y = round(word['top'], 1)
                    if y not in rows:
                        rows[y] = []
                    rows[y].append(word)
                
                # Sort rows by y-position
                sorted_rows = sorted(rows.items())
                
                for y, row_words in sorted_rows:
                    # Sort words in row by x-position
                    row_words.sort(key=lambda w: w['x0'])
                    line_text = ' '.join(w['text'] for w in row_words).strip()
                    
                    # Detect potential date (MM/DD) at the start (x < 100)
                    row_date = None
                    for word in row_words:
                        text = word['text']
                        x = word['x0']
                        if len(text) == 5 and text[2] == '/' and 0 < x < 100:
                            try:
                                month = int(text[:2])
                                day = int(text[3:])
                                if 1 <= day <= 31 and 1 <= month <= 12:
                                    row_date = text
                                    break
                            except ValueError:
                                continue
                    
                    if row_date:
                        # If a new date is found, save the previous transaction if it exists
                        if current_transaction:
                            transactions.append(current_transaction)
                        
                        current_transaction = {
                            'Transaction Date': row_date,
                            'Posting Date': '',
                            'Transaction Details': '',
                            'Amount': '',
                            'DB/CR': 'DB',
                            'created_at': conversion_timestamp
                        }
                        
                        # Process fields for the current row
                        for word in row_words:
                            x = word['x0']
                            text = word['text']
                            
                            # Posting Date (approx x=169)
                            if 100 <= x < 200:
                                if len(text) == 5 and text[2] == '/':
                                    current_transaction['Posting Date'] = text
                            # Details (approx x=242)
                            elif 200 <= x < 450:
                                if not current_transaction['Transaction Details']:
                                    current_transaction['Transaction Details'] = text
                                else:
                                    current_transaction['Transaction Details'] += ' ' + text
                            # Amount (approx x >= 479)
                            elif x >= 479:
                                val = text.replace(',', '').strip()
                                if 'CR' in val:
                                    val = val.replace('CR', '').strip()
                                    current_transaction['DB/CR'] = 'CR'
                                # Skip "Rp." label but keep the value
                                if val.upper() != 'RP.':
                                    current_transaction['Amount'] = val
                        
                        last_y = y  # Update last vertical position
                    
                    elif current_transaction:
                        # Skip explicit navigation/footer lines
                        is_blacklist = any(item in line_text.upper() for item in BLACKLIST)
                        is_too_far = (y - last_y) > MAX_Y_GAP
                        
                        if is_blacklist or is_too_far:
                            # If we hit garbage or wide gap, finalize current transaction
                            transactions.append(current_transaction)
                            current_transaction = None
                            continue

                        # This line has no date, check if it's a detail continuation
                        detail_parts = []
                        has_amount = False
                        for word in row_words:
                            x = word['x0']
                            text = word['text']
                            if 200 <= x < 450:
                                detail_parts.append(text)
                            elif x >= 479 and any(c.isdigit() for c in text):
                                has_amount = True
                        
                        # If it only has details and no new amount, it's a continuation
                        if detail_parts and not has_amount:
                            current_transaction['Transaction Details'] += ' ' + ' '.join(detail_parts)
                            last_y = y  # Only update last_y for successful continuation
                        # If it has a new amount but no date, it shouldn't happen in DBS, 
                        # but we save previous and handle this as a weird case?
                        # For now, let's just ignore non-transaction lines like headers.
                
                # Save last transaction of the page
                if current_transaction:
                    transactions.append(current_transaction)
                    current_transaction = None
    
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    if not transactions:
        return pd.DataFrame(columns=['Transaction Date', 'Posting Date', 'Transaction Details', 'Amount', 'DB/CR', 'created_at'])

    df = pd.DataFrame(transactions)
    expected_columns = ['Transaction Date', 'Posting Date', 'Transaction Details', 'Amount', 'DB/CR', 'created_at']
    for column in expected_columns:
        if column not in df.columns:
            df[column] = ''
    return df[expected_columns]
