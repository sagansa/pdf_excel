import logging
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from backend.errors import BadRequestError, NotFoundError
from backend.routes.hpp_helpers import (
    normalize_product_payload,
    require_db_engine,
    serialize_row,
    serialize_rows,
)
from backend.routes.hpp_queries import (
    delete_batch_by_id as q_delete_batch_by_id,
    delete_batch_products as q_delete_batch_products,
    delete_batch_transactions as q_delete_batch_transactions,
    get_batch_by_id as q_get_batch_by_id,
    get_batch_products as q_get_batch_products,
    get_batch_transactions as q_get_batch_transactions,
    get_batch_unit_prices as q_get_batch_unit_prices,
    get_batches as q_get_batches,
    get_earliest_transaction_date as q_get_earliest_transaction_date,
    get_linkable_transactions as q_get_linkable_transactions,
    get_products as q_get_products,
    get_total_transaction_amount as q_get_total_transaction_amount,
    insert_batch as q_insert_batch,
    insert_batch_product as q_insert_batch_product,
    insert_batch_transaction as q_insert_batch_transaction,
    insert_product as q_insert_product,
    update_batch as q_update_batch,
    update_product as q_update_product,
)

hpp_bp = Blueprint('hpp_bp', __name__)
logger = logging.getLogger(__name__)

@hpp_bp.route('/api/products', methods=['GET'])
def get_products():
    engine = require_db_engine()
    company_id = request.args.get('company_id')
    with engine.connect() as conn:
        result = conn.execute(*q_get_products(company_id))
        return jsonify({'products': serialize_rows(result)})

@hpp_bp.route('/api/products', methods=['POST'])
def create_product():
    engine = require_db_engine()
    data = request.get_json(silent=True) or {}
    name = str(data.get('name') or '').strip()
    if not name:
        raise BadRequestError('Product name is required')

    product_id = str(uuid.uuid4())
    now = datetime.now()

    with engine.begin() as conn:
        conn.execute(q_insert_product(), {
            'id': product_id,
            'company_id': data.get('company_id') or None,
            'code': data.get('code') or None,
            'name': name,
            'category': data.get('category') or None,
            'default_currency': data.get('default_currency') or 'USD',
            'default_price': float(data.get('default_price') or 0.0),
            'now': now,
        })
    return jsonify({'message': 'Product created successfully', 'id': product_id}), 201

@hpp_bp.route('/api/products/<product_id>', methods=['PUT', 'DELETE'])
def manage_product(product_id):
    engine = require_db_engine()
    if request.method == 'DELETE':
        with engine.begin() as conn:
            result = conn.execute(text("DELETE FROM products WHERE id = :id"), {'id': product_id})
            if result.rowcount == 0:
                raise NotFoundError('Product not found')
            return jsonify({'message': 'Product deleted successfully'})

    data = request.get_json(silent=True) or {}
    name = str(data.get('name') or '').strip()
    if not name:
        raise BadRequestError('Product name is required')

    with engine.begin() as conn:
        result = conn.execute(q_update_product(), {
            'id': product_id,
            'company_id': data.get('company_id') or None,
            'code': data.get('code') or None,
            'name': name,
            'category': data.get('category') or None,
            'default_currency': data.get('default_currency') or 'USD',
            'default_price': float(data.get('default_price') or 0.0),
            'now': datetime.now(),
        })
        if result.rowcount == 0:
            raise NotFoundError('Product not found')
    return jsonify({'message': 'Product updated successfully'})

@hpp_bp.route('/api/hpp-batches', methods=['GET'])
def get_batches():
    engine = require_db_engine()
    company_id = request.args.get('company_id')
    with engine.connect() as conn:
        result = conn.execute(*q_get_batches(company_id))
        batches = []
        for row in result:
            batch = serialize_row(row)
            batch['unit_prices'] = [
                {
                    'product_name': unit_price['product_name'],
                    'unit_price': unit_price['unit_price'],
                }
                for unit_price in q_get_batch_unit_prices(conn, batch['id'])
            ]
            batches.append(batch)
        return jsonify({'batches': batches})

@hpp_bp.route('/api/hpp-batches/<batch_id>', methods=['GET'])
def get_batch_details(batch_id):
    engine = require_db_engine()

    with engine.connect() as conn:
        batch_res = conn.execute(*q_get_batch_by_id(batch_id)).fetchone()
        if not batch_res:
            raise NotFoundError('Batch not found')

        batch_data = serialize_row(batch_res)
        transactions = serialize_rows(
            conn.execute(*q_get_batch_transactions(batch_id)),
            date_format='%Y-%m-%d',
        )
        products = serialize_rows(conn.execute(*q_get_batch_products(batch_id)))

        return jsonify({
            'batch': batch_data,
            'transactions': transactions,
            'products': products,
        })

@hpp_bp.route('/api/hpp-batches', methods=['POST'])
def save_batch():
    engine = require_db_engine()
    data = request.get_json(silent=True) or {}
    company_id = data.get('company_id')
    memo = data.get('memo', '')
    batch_date = data.get('batch_date')
    transaction_ids = data.get('transaction_ids') or []
    products = [normalize_product_payload(item) for item in (data.get('products') or [])]
    batch_id = data.get('id')

    logger.info(
        "[COGS Batch] Received request company_id=%s batch_date=%s transactions=%s",
        company_id,
        batch_date,
        len(transaction_ids),
    )

    if not company_id:
        raise BadRequestError('Company ID is required')
    if not transaction_ids:
        raise BadRequestError('At least one transaction must be selected')
    if any(not item.get('product_id') for item in products):
        raise BadRequestError('Each product must include product_id')

    if not batch_date:
        logger.debug("[COGS Batch] No batch_date provided, calculating from selected transactions")
        with engine.connect() as conn:
            earliest_date = q_get_earliest_transaction_date(conn, transaction_ids)
        if earliest_date:
            batch_date = earliest_date.strftime('%Y-%m-%d')
            logger.debug("[COGS Batch] Calculated batch_date=%s", batch_date)

    if not batch_date:
        batch_date = datetime.now().strftime('%Y-%m-%d')
        logger.debug("[COGS Batch] Falling back to current date batch_date=%s", batch_date)

    logger.debug("[COGS Batch] Final batch_date=%s", batch_date)

    with engine.begin() as conn:
        total_idr_amount = q_get_total_transaction_amount(conn, transaction_ids)
        total_foreign_value = sum(item['quantity'] * item['foreign_price'] for item in products)

        is_new = not batch_id
        if is_new:
            batch_id = str(uuid.uuid4())
            conn.execute(q_insert_batch(), {
                'id': batch_id,
                'company_id': company_id,
                'memo': memo,
                'batch_date': batch_date,
                'total_amount': total_idr_amount,
            })
        else:
            logger.info("[COGS Batch] Updating batch id=%s batch_date=%s", batch_id, batch_date)
            result = conn.execute(q_update_batch(), {
                'id': batch_id,
                'company_id': company_id,
                'memo': memo,
                'batch_date': batch_date,
                'total_amount': total_idr_amount,
            })
            if result.rowcount == 0:
                raise NotFoundError('Batch not found')

        conn.execute(q_delete_batch_transactions(), {'batch_id': batch_id})
        for transaction_id in transaction_ids:
            conn.execute(q_insert_batch_transaction(), {'batch_id': batch_id, 'txn_id': transaction_id})

        conn.execute(q_delete_batch_products(), {'batch_id': batch_id})
        for item in products:
            item_foreign_value = item['quantity'] * item['foreign_price']
            calculated_total_idr = (
                total_idr_amount * (item_foreign_value / total_foreign_value)
                if total_foreign_value > 0 else 0.0
            )
            calculated_unit_idr = (
                calculated_total_idr / item['quantity']
                if item['quantity'] > 0 else 0.0
            )
            conn.execute(q_insert_batch_product(), {
                'id': str(uuid.uuid4()),
                'batch_id': batch_id,
                'product_id': item['product_id'],
                'qty': item['quantity'],
                'currency': item['foreign_currency'],
                'price': item['foreign_price'],
                'total_idr': calculated_total_idr,
                'unit_idr': calculated_unit_idr,
            })

    return jsonify({
        'message': 'Batch saved successfully',
        'batch_id': batch_id,
        'total_amount': total_idr_amount,
    })

@hpp_bp.route('/api/hpp-batches/<batch_id>', methods=['DELETE'])
def delete_batch(batch_id):
    engine = require_db_engine()
    with engine.begin() as conn:
        result = conn.execute(q_delete_batch_by_id(), {'id': batch_id})
        if result.rowcount == 0:
            raise NotFoundError('Batch not found')
    return jsonify({'message': 'Batch deleted successfully'})

@hpp_bp.route('/api/transactions/linkable-to-hpp', methods=['GET'])
def get_linkable_transactions():
    """
    Returns transactions that can be linked to a batch (possibly excluding already linked ones if strict).
    Currently returns transactions for the chosen company/dates.
    """
    engine = require_db_engine()
    company_id = request.args.get('company_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    with engine.connect() as conn:
        result = conn.execute(*q_get_linkable_transactions(company_id, start_date, end_date))
        return jsonify({
            'transactions': serialize_rows(result, date_format='%Y-%m-%d')
        })
