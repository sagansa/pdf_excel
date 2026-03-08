from sqlalchemy import text


def insert_transactions_query():
    return text("""
        INSERT INTO transactions (
            id, txn_date, description, amount, db_cr,
            bank_code, source_file, file_hash, mark_id,
            company_id, created_at, updated_at
        )
        VALUES (
            :id, :txn_date, :description, :amount, :db_cr,
            :bank_code, :source_file, :file_hash, :mark_id,
            :company_id, :created_at, :updated_at
        )
    """)
