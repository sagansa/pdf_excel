from sqlalchemy import bindparam, text


def get_batches(conn, company_id=None):
    return _legacy_get_batches(company_id)


def _legacy_get_batches(company_id=None):
    query = """
        SELECT b.*,
               (SELECT COUNT(*) FROM hpp_batch_transactions WHERE batch_id = b.id) AS txn_count,
               (SELECT COUNT(*) FROM hpp_batch_products WHERE batch_id = b.id) AS product_count,
               (SELECT COUNT(*) FROM hpp_batch_products WHERE batch_id = b.id) AS item_count
        FROM hpp_batches b
    """
    params = {}
    if company_id:
        query += " WHERE b.company_id = :company_id"
        params['company_id'] = company_id
    query += " ORDER BY b.batch_date DESC, b.created_at DESC"
    return text(query), params


def get_batches(conn, company_id=None):
    from backend.db.schema import get_table_columns

    hpp_batch_columns = get_table_columns(conn, 'hpp_batches')
    order_parts = []
    if 'batch_date' in hpp_batch_columns:
        order_parts.append("b.batch_date DESC")
    if 'created_at' in hpp_batch_columns:
        order_parts.append("b.created_at DESC")
    if not order_parts:
        order_parts.append("b.id DESC")

    query = """
        SELECT b.*,
               (SELECT COUNT(*) FROM hpp_batch_transactions WHERE batch_id = b.id) AS txn_count,
               (SELECT COUNT(*) FROM hpp_batch_products WHERE batch_id = b.id) AS product_count,
               (SELECT COUNT(*) FROM hpp_batch_products WHERE batch_id = b.id) AS item_count
        FROM hpp_batches b
    """
    params = {}
    if company_id:
        query += " WHERE b.company_id = :company_id"
        params['company_id'] = company_id
    query += f" ORDER BY {', '.join(order_parts)}"
    return text(query), params


def _hpp_reference_expr(conn, table_alias='bp'):
    from backend.db.schema import get_table_columns

    columns = get_table_columns(conn, 'hpp_batch_products')
    if 'stock_monitoring_id' in columns:
        return f"{table_alias}.stock_monitoring_id"
    return f"{table_alias}.id"


def _hpp_reference_context(conn, table_alias='bp'):
    from backend.db.schema import get_table_columns

    reference_expr = _hpp_reference_expr(conn, table_alias=table_alias)
    has_stock_monitorings = bool(get_table_columns(conn, 'stock_monitorings'))
    return {
        'reference_expr': reference_expr,
        'has_stock_monitorings': has_stock_monitorings,
    }


def get_batch_unit_prices(conn, batch_id):
    context = _hpp_reference_context(conn)
    reference_expr = context['reference_expr']
    joins = []
    item_name_parts = []

    if context['has_stock_monitorings']:
        joins.append(f"LEFT JOIN stock_monitorings sm ON {reference_expr} = sm.id")
        item_name_parts.append('sm.name')

    fallback_name = f"CAST({reference_expr} AS CHAR)"
    item_name_expr = "COALESCE(" + ", ".join([*item_name_parts, fallback_name]) + ")"
    result = conn.execute(text(f"""
        SELECT
            CAST({reference_expr} AS CHAR) AS stock_monitoring_id,
            {item_name_expr} AS item_name,
            bp.calculated_unit_idr_hpp AS unit_price
        FROM hpp_batch_products bp
        {' '.join(joins)}
        WHERE bp.batch_id = :batch_id
    """), {'batch_id': batch_id})
    return [
        {
            'stock_monitoring_id': str(row.stock_monitoring_id or ''),
            'item_name': row.item_name,
            'product_name': row.item_name,
            'unit_price': float(row.unit_price or 0.0),
        }
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


def get_batch_products(conn, batch_id):
    context = _hpp_reference_context(conn)
    reference_expr = context['reference_expr']
    joins = []
    item_name_parts = []

    if context['has_stock_monitorings']:
        joins.append(f"LEFT JOIN stock_monitorings sm ON {reference_expr} = sm.id")
        item_name_parts.append('sm.name')

    fallback_name = f"CAST({reference_expr} AS CHAR)"
    item_name_expr = "COALESCE(" + ", ".join([*item_name_parts, fallback_name]) + ")"
    monitoring_category_expr = 'sm.category' if context['has_stock_monitorings'] else 'NULL'
    return text(f"""
        SELECT
            bp.*,
            CAST({reference_expr} AS CHAR) AS stock_monitoring_id,
            {item_name_expr} AS product_name,
            {item_name_expr} AS item_name,
            {monitoring_category_expr} AS monitoring_category
        FROM hpp_batch_products bp
        {' '.join(joins)}
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


def insert_batch(conn):
    from backend.db.schema import get_table_columns

    hpp_batch_columns = get_table_columns(conn, 'hpp_batches')
    if 'batch_date' in hpp_batch_columns:
        return text("""
            INSERT INTO hpp_batches (id, company_id, memo, batch_date, total_amount)
            VALUES (:id, :company_id, :memo, :batch_date, :total_amount)
        """)
    return text("""
        INSERT INTO hpp_batches (id, company_id, memo, total_amount)
        VALUES (:id, :company_id, :memo, :total_amount)
    """)


def update_batch(conn):
    from backend.db.schema import get_table_columns

    hpp_batch_columns = get_table_columns(conn, 'hpp_batches')
    if 'batch_date' in hpp_batch_columns:
        return text("""
            UPDATE hpp_batches
            SET memo = :memo,
                batch_date = :batch_date,
                total_amount = :total_amount
            WHERE id = :id AND company_id = :company_id
        """)
    return text("""
        UPDATE hpp_batches
        SET memo = :memo,
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


def insert_batch_product(conn):
    from backend.db.schema import get_table_columns

    columns = get_table_columns(conn, 'hpp_batch_products')
    insert_columns = ['id', 'batch_id']
    insert_values = [':id', ':batch_id']

    if 'stock_monitoring_id' in columns:
        insert_columns.append('stock_monitoring_id')
        insert_values.append(':stock_monitoring_id')

    insert_columns.extend([
        'quantity',
        'foreign_currency',
        'foreign_price',
        'calculated_total_idr',
        'calculated_unit_idr_hpp',
    ])
    insert_values.extend([
        ':qty',
        ':currency',
        ':price',
        ':total_idr',
        ':unit_idr',
    ])

    return text(f"""
        INSERT INTO hpp_batch_products
        ({', '.join(insert_columns)})
        VALUES ({', '.join(insert_values)})
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
