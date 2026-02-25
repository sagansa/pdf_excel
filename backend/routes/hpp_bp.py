import uuid
from flask import Blueprint, request, jsonify
from datetime import datetime
from sqlalchemy import text
from decimal import Decimal
from backend.db.session import get_db_engine

hpp_bp = Blueprint('hpp_bp', __name__)

@hpp_bp.route('/api/products', methods=['GET'])
def get_products():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
        
    company_id = request.args.get('company_id')
    try:
        with engine.connect() as conn:
            query = "SELECT * FROM products"
            params = {}
            if company_id:
                query += " WHERE company_id = :company_id OR company_id IS NULL"
                params['company_id'] = company_id
            
            query += " ORDER BY name ASC"
            
            result = conn.execute(text(query), params)
            products = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, Decimal):
                        d[key] = float(value)
                products.append(d)
            return jsonify({'products': products})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hpp_bp.route('/api/products', methods=['POST'])
def create_product():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
        
    try:
        data = request.json
        name = data.get('name')
        if not name:
            return jsonify({'error': 'Product name is required'}), 400
            
        product_id = str(uuid.uuid4())
        now = datetime.now()
        
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO products 
                    (id, company_id, code, name, category, default_currency, default_price, created_at, updated_at) 
                    VALUES (:id, :company_id, :code, :name, :category, :default_currency, :default_price, :now, :now)
                """),
                {
                    'id': product_id,
                    'company_id': data.get('company_id') or None,
                    'code': data.get('code') or None,
                    'name': name,
                    'category': data.get('category') or None,
                    'default_currency': data.get('default_currency') or 'USD',
                    'default_price': float(data.get('default_price') or 0.0),
                    'now': now
                }
            )
            return jsonify({'message': 'Product created successfully', 'id': product_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hpp_bp.route('/api/products/<product_id>', methods=['PUT', 'DELETE'])
def manage_product(product_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
        
    if request.method == 'DELETE':
        try:
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM products WHERE id = :id"), {'id': product_id})
                return jsonify({'message': 'Product deleted successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    elif request.method == 'PUT':
        try:
            data = request.json
            name = data.get('name')
            if not name:
                return jsonify({'error': 'Product name is required'}), 400
                
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE products 
                        SET company_id = :company_id, code = :code, name = :name, 
                            category = :category, default_currency = :default_currency, 
                            default_price = :default_price, updated_at = :now 
                        WHERE id = :id
                    """),
                    {
                        'id': product_id,
                        'company_id': data.get('company_id') or None,
                        'code': data.get('code') or None,
                        'name': name,
                        'category': data.get('category') or None,
                        'default_currency': data.get('default_currency') or 'USD',
                        'default_price': float(data.get('default_price') or 0.0),
                        'now': datetime.now()
                    }
                )
                return jsonify({'message': 'Product updated successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@hpp_bp.route('/api/hpp-batches', methods=['GET'])
def get_batches():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
        
    company_id = request.args.get('company_id')
    try:
        with engine.connect() as conn:
            query = """
                SELECT b.*, 
                       (SELECT COUNT(*) FROM hpp_batch_transactions WHERE batch_id = b.id) as txn_count,
                       (SELECT COUNT(*) FROM hpp_batch_products WHERE batch_id = b.id) as product_count
                FROM hpp_batches b
            """
            params = {}
            if company_id:
                query += " WHERE b.company_id = :company_id"
                params['company_id'] = company_id
            
            # Order by batch_date descending (newest first)
            query += " ORDER BY b.batch_date DESC, b.created_at DESC"
            
            result = conn.execute(text(query), params)
            batches = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, Decimal):
                        d[key] = float(value)
                
                # Get unit prices for products in this batch
                unit_prices_query = text("""
                    SELECT p.name as product_name, bp.calculated_unit_idr_hpp as unit_price
                    FROM hpp_batch_products bp
                    JOIN products p ON bp.product_id = p.id
                    WHERE bp.batch_id = :batch_id
                """)
                unit_prices_result = conn.execute(unit_prices_query, {'batch_id': d['id']})
                d['unit_prices'] = [
                    {'product_name': row.product_name, 'unit_price': float(row.unit_price)}
                    for row in unit_prices_result
                ]
                
                batches.append(d)
            return jsonify({'batches': batches})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hpp_bp.route('/api/hpp-batches/<batch_id>', methods=['GET'])
def get_batch_details(batch_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.connect() as conn:
            # Get Batch Info
            batch_res = conn.execute(
                text("SELECT * FROM hpp_batches WHERE id = :id"),
                {'id': batch_id}
            ).fetchone()
            
            if not batch_res:
                return jsonify({'error': 'Batch not found'}), 404
                
            batch_data = dict(batch_res._mapping)
            for k, v in batch_data.items():
                if isinstance(v, Decimal): batch_data[k] = float(v)
                elif isinstance(v, datetime): batch_data[k] = v.strftime('%Y-%m-%d %H:%M:%S')

            # Get linked transactions
            txns_res = conn.execute(
                text("""
                    SELECT t.id, t.txn_date, 
                           COALESCE(t.description, parent.description, '') as description, 
                           t.amount, t.db_cr,
                           COALESCE(ts_mark.personal_use, m.personal_use, t.mark, '') as mark
                    FROM hpp_batch_transactions bt
                    JOIN transactions t ON bt.transaction_id = t.id
                    LEFT JOIN transactions parent ON t.parent_id = parent.id
                    LEFT JOIN marks m ON t.mark_id = m.id
                    LEFT JOIN transaction_splits ts ON ts.transaction_id = t.id
                    LEFT JOIN marks ts_mark ON ts.mark_id = ts_mark.id
                    WHERE bt.batch_id = :batch_id
                """),
                {'batch_id': batch_id}
            )
            transactions = [dict(row._mapping) for row in txns_res]
            for t in transactions:
                if isinstance(t['amount'], Decimal): t['amount'] = float(t['amount'])
                if isinstance(t['txn_date'], datetime): t['txn_date'] = t['txn_date'].strftime('%Y-%m-%d')

            # Get linked products
            prods_res = conn.execute(
                text("""
                    SELECT bp.*, p.name as product_name, p.code as product_code 
                    FROM hpp_batch_products bp
                    JOIN products p ON bp.product_id = p.id
                    WHERE bp.batch_id = :batch_id
                """),
                {'batch_id': batch_id}
            )
            products = []
            for row in prods_res:
                d = dict(row._mapping)
                for k, v in d.items():
                    if isinstance(v, Decimal): d[k] = float(v)
                products.append(d)

            return jsonify({
                'batch': batch_data,
                'transactions': transactions,
                'products': products
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hpp_bp.route('/api/hpp-batches', methods=['POST'])
def save_batch():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
        
    try:
        data = request.json
        company_id = data.get('company_id')
        memo = data.get('memo', '')
        batch_date = data.get('batch_date')
        transaction_ids = data.get('transaction_ids', [])
        products = data.get('products', [])
        batch_id = data.get('id') # If provided, it's an update
        
        print(f"[COGS Batch] Received: company_id={company_id}, batch_date={batch_date}, transactions={len(transaction_ids)}")
        
        if not company_id:
            return jsonify({'error': 'Company ID is required'}), 400
        if not transaction_ids:
            return jsonify({'error': 'At least one transaction must be selected'}), 400
        
        # If batch_date not provided, use the earliest transaction date from selected transactions
        if not batch_date and transaction_ids:
            print(f"[COGS Batch] No batch_date provided, calculating from transactions...")
            with engine.connect() as conn:
                txn_placeholders = ', '.join([f":t_{i}" for i in range(len(transaction_ids))])
                params = {f"t_{i}": tid for i, tid in enumerate(transaction_ids)}
                
                date_res = conn.execute(
                    text(f"SELECT MIN(txn_date) as earliest_date FROM transactions WHERE id IN ({txn_placeholders})"),
                    params
                ).fetchone()
                
                if date_res and date_res[0]:
                    batch_date = date_res[0].strftime('%Y-%m-%d')
                    print(f"[COGS Batch] Calculated batch_date: {batch_date}")
        
        if not batch_date:
            batch_date = datetime.now().strftime('%Y-%m-%d')
            print(f"[COGS Batch] Using current date as batch_date: {batch_date}")
        
        print(f"[COGS Batch] Final batch_date: {batch_date}")

        with engine.begin() as conn:
            # 1. Calculate Total Amount of selected transactions
            txn_placeholders = ', '.join([f":t_{i}" for i in range(len(transaction_ids))])
            params = {f"t_{i}": tid for i, tid in enumerate(transaction_ids)}
            
            txn_res = conn.execute(
                text(f"SELECT SUM(ABS(amount)) as total FROM transactions WHERE id IN ({txn_placeholders})"),
                params
            ).fetchone()
            
            total_idr_amount = float(txn_res[0] or 0.0)
            
            # Calculate total foreign equivalent for proportionality
            total_foreign_value = sum(float(item.get('quantity', 0)) * float(item.get('foreign_price', 0)) for item in products)
            
            is_new = False
            if not batch_id:
                batch_id = str(uuid.uuid4())
                is_new = True
                
            # 2. Upsert Batch Header
            if is_new:
                conn.execute(
                    text("""
                        INSERT INTO hpp_batches (id, company_id, memo, batch_date, total_amount) 
                        VALUES (:id, :company_id, :memo, :batch_date, :total_amount)
                    """),
                    {
                        'id': batch_id,
                        'company_id': company_id,
                        'memo': memo,
                        'batch_date': batch_date,
                        'total_amount': total_idr_amount
                    }
                )
            else:
                print(f"[COGS Batch] UPDATING batch {batch_id} with batch_date={batch_date}")
                conn.execute(
                    text("""
                        UPDATE hpp_batches 
                        SET memo = :memo, batch_date = :batch_date, total_amount = :total_amount 
                        WHERE id = :id AND company_id = :company_id
                    """),
                    {
                        'id': batch_id,
                        'company_id': company_id,
                        'memo': memo,
                        'batch_date': batch_date,
                        'total_amount': total_idr_amount
                    }
                )
                print(f"[COGS Batch] UPDATE executed successfully")
                
            # 3. Re-link Transactions
            conn.execute(text("DELETE FROM hpp_batch_transactions WHERE batch_id = :batch_id"), {'batch_id': batch_id})
            for tid in transaction_ids:
                conn.execute(
                    text("INSERT INTO hpp_batch_transactions (batch_id, transaction_id) VALUES (:batch_id, :txn_id)"),
                    {'batch_id': batch_id, 'txn_id': tid}
                )
                
            # 4. Save Products with Proportion Math
            conn.execute(text("DELETE FROM hpp_batch_products WHERE batch_id = :batch_id"), {'batch_id': batch_id})
            for item in products:
                qty = float(item.get('quantity', 0))
                price = float(item.get('foreign_price', 0))
                item_foreign_value = qty * price
                
                # Math Logic:
                # 1. Portion of total pool = (this item's foreign value / total foreign value of all items)
                # 2. calculated_total_idr = total_idr_amount * portion
                # 3. unit_hpp = calculated_total_idr / qty
                
                if total_foreign_value > 0:
                    calculated_total_idr = total_idr_amount * (item_foreign_value / total_foreign_value)
                else:
                    calculated_total_idr = 0.0
                    
                calculated_unit_idr = calculated_total_idr / qty if qty > 0 else 0.0
                
                conn.execute(
                    text("""
                        INSERT INTO hpp_batch_products 
                        (id, batch_id, product_id, quantity, foreign_currency, foreign_price, calculated_total_idr, calculated_unit_idr_hpp)
                        VALUES (:id, :batch_id, :product_id, :qty, :currency, :price, :total_idr, :unit_idr)
                    """),
                    {
                        'id': str(uuid.uuid4()),
                        'batch_id': batch_id,
                        'product_id': item.get('product_id'),
                        'qty': qty,
                        'currency': item.get('foreign_currency', 'USD'),
                        'price': price,
                        'total_idr': calculated_total_idr,
                        'unit_idr': calculated_unit_idr
                    }
                )
                
            return jsonify({
                'message': 'Batch saved successfully', 
                'batch_id': batch_id,
                'total_amount': total_idr_amount
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hpp_bp.route('/api/hpp-batches/<batch_id>', methods=['DELETE'])
def delete_batch(batch_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
        
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM hpp_batches WHERE id = :id"), {'id': batch_id})
            return jsonify({'message': 'Batch deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hpp_bp.route('/api/transactions/linkable-to-hpp', methods=['GET'])
def get_linkable_transactions():
    """
    Returns transactions that can be linked to a batch (possibly excluding already linked ones if strict).
    Currently returns transactions for the chosen company/dates.
    """
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
        
    company_id = request.args.get('company_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        with engine.connect() as conn:
            query = """
                SELECT t.id, t.txn_date, 
                       COALESCE(t.description, parent.description, '') as description, 
                       t.amount, t.db_cr, 
                       COALESCE(ts_mark.personal_use, m.personal_use, t.mark, '') as mark,
                       (SELECT 1 FROM hpp_batch_transactions bt WHERE bt.transaction_id = t.id LIMIT 1) as is_linked
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
            
            result = conn.execute(text(query), params)
            txns = []
            for row in result:
                d = dict(row._mapping)
                if isinstance(d['amount'], Decimal): d['amount'] = float(d['amount'])
                if isinstance(d['txn_date'], datetime): d['txn_date'] = d['txn_date'].strftime('%Y-%m-%d')
                txns.append(d)
                
            return jsonify({'transactions': txns})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
