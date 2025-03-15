import pdfplumber
import pandas as pd
import re

def parse_statement(pdf_path, password=None):
    transactions = []
    header_found = False
    current_transaction = None
    processed_transactions = set()  # Track processed transactions
    
    try:
        # Open PDF with password if provided
        with pdfplumber.open(pdf_path, password=password) as pdf:
            for page in pdf.pages:
                # Extract text with position information
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3
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
                    line = ' '.join(w['text'] for w in row_words)
                    
                    # Look for transaction date pattern MM/DD
                    for word in row_words:
                        text = word['text']
                        x = word['x0']
                        
                        # Check for MM/DD pattern and validate date
                        if len(text) == 5 and text[2] == '/' and 0 < x < 100:
                            try:
                                month = int(text[:2])
                                day = int(text[3:])
                                
                                # Validate day and month values
                                if not (1 <= day <= 31 and 1 <= month <= 12):
                                    continue
                                    
                                # Additional validation for days in each month
                                days_in_month = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                                if day > days_in_month[month]:
                                    continue
                                
                                # Create transaction key for deduplication
                                transaction_key = f"{text}_{line}"  # Combine date and full line text
                                
                                # Skip if we've already processed this transaction
                                if transaction_key in processed_transactions:
                                    continue
                                    
                                if current_transaction:
                                    transactions.append(current_transaction)
                                
                                current_transaction = {
                                    'Transaction Date': text,
                                    'Posting Date': '',
                                    'Transaction Details': '',
                                    'Amount': '',
                                    'DB/CR': 'DB'  # Default to DB
                                }
                                
                                # Process remaining fields based on x-position
                                details_found = False
                                for detail_word in row_words:
                                    detail_x = detail_word['x0']
                                    detail_text = detail_word['text']
                                    
                                    if 100 <= detail_x < 200:
                                        # Check for posting date pattern MM/DD
                                        if len(detail_text) == 5 and detail_text[2] == '/':
                                            try:
                                                p_month = int(detail_text[:2])
                                                p_day = int(detail_text[3:])
                                                if 1 <= p_day <= 31 and 1 <= p_month <= 12:
                                                    current_transaction['Posting Date'] = detail_text
                                            except ValueError:
                                                pass
                                    elif 200 <= detail_x < 450:
                                        # Add to transaction details
                                        if not details_found:
                                            current_transaction['Transaction Details'] = detail_text
                                            details_found = True
                                        else:
                                            current_transaction['Transaction Details'] += ' ' + detail_text
                                    # elif 450 <= detail_x < 510:
                                    #     # Store Rp. prefix
                                    #     current_transaction['Rp'] = detail_text.strip()
                                    elif detail_x >= 510:
                                        # Process amount and DB/CR indicator
                                        amount_text = detail_text.replace(',', '').strip()
                                        if 'CR' in amount_text:
                                            amount_text = amount_text.replace('CR', '').strip()
                                            current_transaction['DB/CR'] = 'CR'
                                        current_transaction['Amount'] = amount_text
                                
                                # Mark this transaction as processed
                                processed_transactions.add(transaction_key)
                                break  # Exit the date search loop once we've found and processed a date
                            except ValueError:
                                continue
                
                # Add the last transaction of the page
                if current_transaction:
                    transactions.append(current_transaction)
                    current_transaction = None
    
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    return pd.DataFrame(transactions) if transactions else pd.DataFrame(columns=['Transaction Date', 'Posting Date', 'Transaction Details', 'Amount', 'DB/CR'])