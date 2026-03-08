from sqlalchemy import bindparam, text


def get_products(company_id=None):
    query = "SELECT * FROM products"
    params = {}
    if company_id:
        query += " WHERE company_id = :company_id OR company_id IS NULL"
        params['company_id'] = company_id
    query += " ORDER BY name ASC"
    return text(query), params


def insert_product():
    return text("""
        INSERT INTO products
        (id, company_id, code, name, category, default_currency, default_price, created_at, updated_at)
        VALUES (:id, :company_id, :code, :name, :category, :default_currency, :default_price, :now, :now)
    """)


def update_product():
    return text("""
        UPDATE products
        SET company_id = :company_id,
            code = :code,
            name = :name,
            category = :category,
            default_currency = :default_currency,
            default_price = :default_price,
            updated_at = :now
        WHERE id = :id
    """)


def get_batches(company_id=None):
    query = """
        SELECT b.*,
               (SELECT COUNT(*) FROM hpp_batch_transactions WHERE batch_id = b.id) AS txn_count,
               (SELECT COUNT(*) FROM hpp_batch_products WHERE batch_id = b.id) AS product_count
        FROM hpp_batches b
    """
    params = {}
    if company_id:
        query += " WHERE b.company_id = :company_id"
        params['company_id'] = company_id
    query += " ORDER BY b.batch_date DESC, b.created_at DESC"
    return text(query), params


def get_batch_unit_prices(conn, batch_id):
    result = conn.execute(text("""
        SELECT p.name AS product_name, bp.calculated_unit_idr_hpp AS unit_price
        FROM hpp_batch_products bp
        JOIN products p ON bp.product_id = p.id
        WHERE bp.batch_id = :batch_id
    """), {'batch_id': batch_id})
    return [
        {'product_name': row.product_name, 'unit_price': float(row.unit_price or 0.0)}
        for row in result
    ]


def get_batch_by_id(batch_id):
    return text("SELECT * FROM hpp_batches WHERE id = :id"), {'id': batch_id}


def get_batch_transactions(batch_id):
    return text("""
        SELECT t.id,
               t.txn_date,
               COALESCE(t.description, parent.description, '') AS description,
               t.amount,
               t.db_cr,
               COALESCE(ts_mark.personal_use, m.personal_use, t.mark, '') AS mark
        FROM hpp_batch_transactions bt
        JOIN transactions t ON bt.transaction_id = t.id
        LEFT JOIN transactions parent ON t.parent_id = parent.id
        LEFT JOIN marks m ON t.mark_id = m.id
        LEFT JOIN transaction_splits ts ON ts.transaction_id = t.id
        LEFT JOIN marks ts_mark ON ts.mark_id = ts_mark.id
        WHERE bt.batch_id = :batch_id
    """), {'batch_id': batch_id}


def get_batch_products(batch_id):
    return text("""
        SELECT bp.*, p.name AS product_name, p.code AS product_code
        FROM hpp_batch_products bp
        JOIN products p ON bp.product_id = p.id
        WHERE bp.batch_id = :batch_id
    """), {'batch_id': batch_id}


def get_earliest_transaction_date(conn, transaction_ids):
    result = conn.execute(
        text("""
            SELECT MIN(txn_date) AS earliest_date
            FROM transactions
            WHERE id IN :transaction_ids
        """).bindparams(bindparam('transaction_ids', expanding=True)),
        {'transaction_ids': transaction_ids},
    ).fetchone()
    return result[0] if result else None


def get_total_transaction_amount(conn, transaction_ids):
    result = conn.execute(
        text("""
            SELECT SUM(ABS(amount)) AS total
            FROM transactions
            WHERE id IN :transaction_ids
        """).bindparams(bindparam('transaction_ids', expanding=True)),
        {'transaction_ids': transaction_ids},
    ).fetchone()
    return float(result[0] or 0.0) if result else 0.0


def insert_batch():
    return text("""
        INSERT INTO hpp_batches (id, company_id, memo, batch_date, total_amount)
        VALUES (:id, :company_id, :memo, :batch_date, :total_amount)
    """)


def update_batch():
    return text("""
        UPDATE hpp_batches
        SET memo = :memo,
            batch_date = :batch_date,
            total_amount = :total_amount
        WHERE id = :id AND company_id = :company_id
    """)


def delete_batch_transactions():
    return text("DELETE FROM hpp_batch_transactions WHERE batch_id = :batch_id")


def insert_batch_transaction():
    return text("""
        INSERT INTO hpp_batch_transactions (batch_id, transaction_id)
        VALUES (:batch_id, :txn_id)
    """)


def delete_batch_products():
    return text("DELETE FROM hpp_batch_products WHERE batch_id = :batch_id")


def insert_batch_product():
    return text("""
        INSERT INTO hpp_batch_products
        (id, batch_id, product_id, quantity, foreign_currency, foreign_price, calculated_total_idr, calculated_unit_idr_hpp)
        VALUES (:id, :batch_id, :product_id, :qty, :currency, :price, :total_idr, :unit_idr)
    """)


def delete_batch_by_id():
    return text("DELETE FROM hpp_batches WHERE id = :id")


def get_linkable_transactions(company_id=None, start_date=None, end_date=None):
    query = """
        SELECT t.id,
               t.txn_date,
               COALESCE(t.description, parent.description, '') AS description,
               t.amount,
               t.db_cr,
               COALESCE(ts_mark.personal_use, m.personal_use, t.mark, '') AS mark,
               (SELECT 1 FROM hpp_batch_transactions bt WHERE bt.transaction_id = t.id LIMIT 1) AS is_linked
        FROM transactions t
        LEFT JOIN transactions parent ON t.parent_id = parent.id
        LEFT JOIN marks m ON t.mark_id = m.id
        LEFT JOIN transaction_splits ts ON ts.transaction_id = t.id
        LEFT JOIN marks ts_mark ON ts.mark_id = ts_mark.id
        WHERE 1=1
    """
    params = {}
    if company_id:
        query += " AND t.company_id = :company_id"
        params['company_id'] = company_id
    if start_date:
        query += " AND t.txn_date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        query += " AND t.txn_date <= :end_date"
        params['end_date'] = end_date
    query += " ORDER BY t.txn_date DESC, t.id"
    return text(query), params
