import uuid
import re
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from backend.db.session import get_db_engine


def _null_if_nan(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def _normalize_company_id(value):
    raw = _null_if_nan(value)
    if raw is None:
        return None

    candidate = str(raw).strip()
    if not candidate or candidate.lower() in {'none', 'null'}:
        return None

    # Accept direct UUID or UUID embedded in noisy strings/newlines.
    match = re.search(
        r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})',
        candidate
    )
    if match:
        return match.group(1)

    # transactions.company_id is CHAR(36); reject invalid/oversized values.
    if len(candidate) != 36:
        return None
    return candidate


def save_transactions_to_db(df: pd.DataFrame, bank_code: str, source_file: str, file_hash: str):
    engine, error_msg = get_db_engine()
    if engine is None:
        return False, error_msg or "Failed to connect to database"
    
    records = []
    skipped_rows = 0
    now = datetime.now()
    for _, row in df.iterrows():
        try:
            txn_id = str(uuid.uuid4())
            txn_date = _null_if_nan(row.get('txn_date')) or _null_if_nan(row.get('Transaction Date')) or _null_if_nan(row.get('Tanggal'))
            description = _null_if_nan(row.get('description')) or _null_if_nan(row.get('Transaction Details')) or _null_if_nan(row.get('Keterangan'))
            amount = _null_if_nan(row.get('amount')) or _null_if_nan(row.get('Amount'))
            db_cr = _null_if_nan(row.get('db_cr')) or _null_if_nan(row.get('DB/CR')) or 'DB'
            created_at = _null_if_nan(row.get('created_at')) or now
            company_id = _normalize_company_id(row.get('company_id'))
            
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
                'company_id': company_id,
                'created_at': created_at,
                'updated_at': now
            })
        except Exception as e:
            skipped_rows += 1
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
    return False, (
        f"No valid transactions were prepared for insert. "
        f"Parsed rows: {len(df)}, skipped rows: {skipped_rows}"
    )
