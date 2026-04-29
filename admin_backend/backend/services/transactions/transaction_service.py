import logging
import uuid

import pandas as pd

from backend.db.schema import get_table_columns
from backend.db.session import get_db_engine
from backend.services.transactions.transaction_queries import insert_transactions_query
from backend.services.transactions.transaction_utils import build_transaction_record

logger = logging.getLogger(__name__)


def save_transactions_to_db(df: pd.DataFrame, bank_code: str, source_file: str, file_hash: str):
    engine, error_msg = get_db_engine()
    if engine is None:
        return False, error_msg or 'Failed to connect to database'

    records = []
    skipped_rows = 0
    for _, row in df.iterrows():
        try:
            record = build_transaction_record(row, bank_code, source_file, file_hash)
            record['id'] = str(uuid.uuid4())
            records.append(record)
        except (TypeError, ValueError, AttributeError) as exc:
            skipped_rows += 1
            logger.warning('Skipping transaction row due to normalization error: %s', exc)

    if not records:
        return False, (
            'No valid transactions were prepared for insert. '
            f'Parsed rows: {len(df)}, skipped rows: {skipped_rows}'
        )

    try:
        with engine.begin() as conn:
            transaction_columns = get_table_columns(conn, 'transactions')
            insert_columns = [
                column for column in [
                    'id',
                    'txn_date',
                    'description',
                    'amount',
                    'db_cr',
                    'bank_code',
                    'bank_account_number',
                    'source_file',
                    'file_hash',
                    'mark_id',
                    'company_id',
                    'created_at',
                    'updated_at',
                ]
                if column in transaction_columns
            ]
            insert_records = [
                {column: record.get(column) for column in insert_columns}
                for record in records
            ]
            conn.execute(insert_transactions_query(insert_columns), insert_records)
        return True, None
    except Exception as exc:
        return False, f'Database Error: {exc}'
