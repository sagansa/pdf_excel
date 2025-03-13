import pdfplumber
import pandas as pd

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
                        if len(text) == 5 and text[2] == '/' and x < 100:
                            try:
                                # Simple validation of date format
                                month = int(text[:2])
                                day = int(text[3:])
                                
                                if 1 <= day <= 31 and 1 <= month <= 12:
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
                                    for detail_word in row_words:
                                        detail_x = detail_word['x0']
                                        detail_text = detail_word['text']
                                        
                                        if detail_x > 100 and detail_x < 300:
                                            # Check for posting date pattern
                                            if len(detail_text) == 5 and detail_text[2] == '/':
                                                try:
                                                    p_month = int(detail_text[:2])
                                                    p_day = int(detail_text[3:])
                                                    if 1 <= p_day <= 31 and 1 <= p_month <= 12:
                                                        current_transaction['Posting Date'] = detail_text
                                                        continue
                                                except ValueError:
                                                    pass
                                            # Add to transaction details if not a date
                                            if current_transaction['Transaction Details']:
                                                current_transaction['Transaction Details'] += ' ' + detail_text
                                            else:
                                                current_transaction['Transaction Details'] = detail_text
                                        elif detail_x >= 300:
                                            # Assume amount is in the rightmost position
                                            current_transaction['Amount'] = detail_text.replace('CR', '').strip()
                                            # Set DB/CR based on amount field content
                                            if 'CR' in detail_text:
                                                current_transaction['DB/CR'] = 'CR'
                                    
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