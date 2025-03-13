import re
import pdfplumber
import pandas as pd

def parse_statement(pdf_path):
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
                            process_transaction(transactions, current_transaction)
                        
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
                process_transaction(transactions, current_transaction)
                current_transaction = None
    
    return pd.DataFrame(transactions) if transactions else pd.DataFrame(columns=['Tanggal', 'Keterangan', 'Debet', 'Kredit', 'Saldo'])

def process_transaction(transactions, transaction):
    transactions.append({
        'Tanggal': transaction['date'],
        'Keterangan': transaction['keterangan'].strip(),
        'Debet': transaction['debet'].strip(),
        'Kredit': transaction['kredit'].strip(),
        'Saldo': transaction['saldo'].strip()
    })