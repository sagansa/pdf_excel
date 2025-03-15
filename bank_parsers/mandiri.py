import re
import pdfplumber
import pandas as pd
from datetime import datetime

def parse_statement(pdf_path):
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("Invalid file format. Please provide a PDF file")

    transactions = []
    current_transaction = None
    header_found = False

    # Define header and footer markers
    header_markers = ['Transaction', 'Valuta']
    footer_markers = ['Saldo Awal', 'Mutasi Kredit', 'Mutasi Debit', 'Saldo Akhir']

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Reset header flag for each new page
                header_found = False
                
                # Extract text with position information
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3
                )

                # Group words by y-position (rows)
                rows = {}
                for word in words:
                    # Skip if line contains any footer markers
                    line_text = word['text']
                    if any(marker in line_text for marker in footer_markers):
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
                    line = ' '.join(w['text'] for w in row_words)

                    # Check for header row
                    if not header_found and all(marker in line for marker in header_markers):
                        header_found = True
                        continue

                    if not header_found:
                        continue

                    # Process each word based on x-position
                    transaction_date = ''
                    valuta_date = ''
                    transaction_details = []
                    amount = ''
                    balance = ''
                    db_cr = 'CR'  # Default to CR

                    for word in row_words:
                        text = word['text']
                        x = word['x0']

                        # Transaction date (leftmost position)
                        if x < 80 and re.match(r'\d{2}/\d{2}', text):
                            try:
                                day = int(text[:2])
                                month = int(text[3:])
                                if 1 <= day <= 31 and 1 <= month <= 12:
                                    transaction_date = text
                            except ValueError:
                                continue

                        # Valuta date (second position)
                        elif 80 <= x < 130 and re.match(r'\d{2}/\d{2}', text):
                            try:
                                day = int(text[:2])
                                month = int(text[3:])
                                if 1 <= day <= 31 and 1 <= month <= 12:
                                    valuta_date = text
                            except ValueError:
                                continue

                        # Transaction details (middle position)
                        elif 130 <= x < 450:
                            transaction_details.append(text)

                        # Amount (right position)
                        elif 450 <= x < 520:
                            amount = text.strip()

                        # DB/CR indicator
                        elif 520 <= x < 540:
                            db_cr = 'DB' if text.strip().upper() in ['D', 'DB'] else 'CR'

                        # Balance (rightmost position)
                        elif x >= 540:
                            balance = text

                    # If we found a date, create a new transaction
                    if transaction_date or valuta_date:
                        if current_transaction:
                            transactions.append(current_transaction)
                        
                        current_transaction = {
                            'transaction_date': transaction_date,
                            'valuta_date': valuta_date,
                            'transaction_details': ' '.join(transaction_details),
                            'amount': amount,
                            'db_cr': db_cr,
                            'balance': balance
                        }
                    # If no date found and we have a current transaction, append details
                    elif current_transaction and transaction_details:
                        current_details = current_transaction['transaction_details']
                        new_details = ' '.join(transaction_details)
                        current_transaction['transaction_details'] = f"{current_details} {new_details}".strip()
                        
                        # Update amount and balance if present in the continuation line
                        if amount:
                            current_transaction['amount'] = amount
                        if balance:
                            current_transaction['balance'] = balance

            # Add the last transaction if exists
            if current_transaction:
                transactions.append(current_transaction)

    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")

    return pd.DataFrame(transactions) if transactions else pd.DataFrame(
        columns=['transaction_date', 'valuta_date', 'transaction_details', 'amount', 'db_cr', 'balance']
    )