import uuid
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from backend.db.session import get_db_engine

def save_transactions_to_db(df: pd.DataFrame, bank_code: str, source_file: str, file_hash: str):
    engine, error_msg = get_db_engine()
    if engine is None:
        return False, error_msg or "Failed to connect to database"
    
    records = []
    now = datetime.now()
    for _, row in df.iterrows():
        try:
            txn_id = str(uuid.uuid4())
            txn_date = row.get('txn_date') or row.get('Transaction Date') or row.get('Tanggal')
            description = row.get('description') or row.get('Transaction Details') or row.get('Keterangan')
            amount = row.get('amount') or row.get('Amount')
            db_cr = row.get('db_cr') or row.get('DB/CR') or 'DB'
            created_at = row.get('created_at') or now
            
            if isinstance(amount, float):
                 amount_val = amount
            elif isinstance(amount, str):
                amount_val = amount.replace(',', '')
                try:
                    amount_val = float(amount_val) if amount_val else 0.0
                except (ValueError, TypeError):
                    amount_val = 0.0
            else:
                amount_val = float(amount or 0.0)
            
            records.append({
                'id': txn_id,
                'txn_date': txn_date,
                'description': str(description or '')[:1000],
                'amount': amount_val,
                'db_cr': str(db_cr or 'DB')[:2].upper(),
                'bank_code': bank_code,
                'source_file': source_file,
                'file_hash': file_hash,
                'mark_id': None, # Default to None
                'company_id': row.get('company_id'),
                'created_at': created_at,
                'updated_at': now
            })
        except Exception as e:
            continue
            
    if records:
        try:
            with engine.connect() as conn:
                query = text("""
                    INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, source_file, file_hash, mark_id, company_id, created_at, updated_at)
                    VALUES (:id, :txn_date, :description, :amount, :db_cr, :bank_code, :source_file, :file_hash, :mark_id, :company_id, :created_at, :updated_at)
                """)
                conn.execute(query, records)
                conn.commit()
                return True, None
        except Exception as e:
            return False, f"Database Error: {str(e)}"
    return True, None
