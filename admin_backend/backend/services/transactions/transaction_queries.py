from sqlalchemy import text


def insert_transactions_query(columns=None):
    default_columns = [
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
    insert_columns = columns or default_columns
    return text(f"""
        INSERT INTO transactions (
            {', '.join(insert_columns)}
        )
        VALUES (
            {', '.join(f":{column}" for column in insert_columns)}
        )
    """)
