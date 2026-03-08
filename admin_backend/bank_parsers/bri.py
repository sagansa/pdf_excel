import pandas as pd
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

def parse_statement(csv_path):
    """
    Parse BRI CSV statement file
    
    Supports both comma and semicolon delimiters.
    Handles multiple date formats and scientific notation.
    
    Args:
        csv_path: Path to BRI CSV file
        
    Returns:
        pandas.DataFrame with standardized columns
    """
    if not os.path.exists(csv_path):
        raise ValueError("CSV file not found")
        
    if not csv_path.lower().endswith('.csv'):
        raise ValueError("Invalid file format. Please provide a CSV file")
    
    conversion_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    source_file = os.path.basename(csv_path)
    
    try:
        # Auto-detect delimiter by reading first line
        with open(csv_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            delimiter = ';' if ';' in first_line else ','
        
        # Read CSV file with detected delimiter
        df = pd.read_csv(csv_path, delimiter=delimiter, encoding='utf-8')
        
        # Validate required columns
        required_cols = ['NOREK', 'TGL_TRAN', 'DESK_TRAN', 'MUTASI_DEBET', 'MUTASI_KREDIT', 'GLSIGN']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
        
        standard_rows = []
        bank_code = 'BRI'
        currency = 'IDR'
        account_no = ''
        
        for _, row in df.iterrows():
            # Get account number (handle scientific notation like 5.0501E+13)
            if not account_no and pd.notna(row.get('NOREK')):
                norek_value = row['NOREK']
                if isinstance(norek_value, float):
                    account_no = f"{norek_value:.0f}"
                else:
                    account_no = str(norek_value).strip()
            
            # Parse transaction date - handle both formats
            txn_date_raw = str(row.get('TGL_TRAN', '')).strip()
            txn_date = _parse_date(txn_date_raw)
            
            # Posting date
            posting_date_raw = str(row.get('TGL_EFEKTIF', txn_date_raw)).strip()
            posting_date = _parse_date(posting_date_raw)
            
            # Description (combine DESK_TRAN and REMARK_CUSTOM)
            desk_tran = str(row.get('DESK_TRAN', '')).strip()
            remark_custom = str(row.get('REMARK_CUSTOM', '')).strip()
            description = f"{desk_tran} {remark_custom}".strip() if remark_custom else desk_tran
            
            # Amount - use MUTASI_DEBET or MUTASI_KREDIT (whichever is non-zero)
            mutasi_debet = _parse_decimal(str(row.get('MUTASI_DEBET', '0')))
            mutasi_kredit = _parse_decimal(str(row.get('MUTASI_KREDIT', '0')))
            
            # Determine amount and DB/CR
            if mutasi_debet > 0:
                amount = mutasi_debet
                db_cr = 'DB'
            elif mutasi_kredit > 0:
                amount = mutasi_kredit
                db_cr = 'CR'
            else:
                # Fallback: check GLSIGN
                glsign = str(row.get('GLSIGN', '')).strip().upper()
                db_cr = 'DB' if glsign == 'DB' else 'CR'
                amount = Decimal('0')
            
            amount_str = format(amount, '.2f')
            
            # Balance
            balance = _parse_decimal(str(row.get('SALDO_AKHIR_MUTASI', '0')))
            balance_str = format(balance, '.2f')
            
            standard_rows.append({
                'bank_code': bank_code,
                'account_no': account_no,
                'txn_date': txn_date,
                'posting_date': posting_date,
                'description': description,
                'amount': amount_str,
                'db_cr': db_cr,
                'balance': balance_str,
                'currency': currency,
                'created_at': conversion_timestamp,
                'source_file': source_file
            })
        
        columns = ['bank_code', 'account_no', 'txn_date', 'posting_date', 'description', 'amount', 'db_cr', 'balance', 'currency', 'created_at', 'source_file']
        
        return pd.DataFrame(standard_rows, columns=columns)
        
    except Exception as e:
        raise ValueError(f"Error processing CSV: {str(e)}")


def _parse_date(date_str: str) -> str:
    """Parse date from various formats to YYYY-MM-DD HH:MM:SS."""
    if not date_str or date_str.lower() == 'nan':
        return ''
    
    # Try YYYY-MM-DD HH:MM:SS format first
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass
    
    # Try DD/MM/YYYY HH:MM format
    try:
        dt = datetime.strptime(date_str, '%d/%m/%Y %H:%M')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass
    
    # Return as-is if parsing fails
    return date_str


def _parse_decimal(value: str) -> Decimal:
    """Parse decimal value from string, handling BRI format"""
    if not value or value == '.00' or value.lower() == 'nan':
        return Decimal('0')
    
    cleaned = value.strip().replace(' ', '')
    
    # Remove any non-numeric characters except period and minus
    cleaned = ''.join(c for c in cleaned if c.isdigit() or c in '.-')
    
    if not cleaned or cleaned == '.':
        return Decimal('0')
    
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal('0')
