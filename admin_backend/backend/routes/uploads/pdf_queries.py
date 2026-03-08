from sqlalchemy import text


def count_transactions_by_source_file_query():
    return text("""
        SELECT COUNT(1) AS cnt
        FROM transactions
        WHERE source_file = :source_file
    """)


def find_transaction_by_file_hash_query():
    return text("""
        SELECT id
        FROM transactions
        WHERE file_hash = :hash
        LIMIT 1
    """)
