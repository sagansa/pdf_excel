import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from backend.errors import BadRequestError
from backend.routes.accounting_utils import (
    build_inventory_balance_with_carry,
    require_db_engine,
    to_float,
)
from backend.routes.inventory.inventory_queries import (
    insert_carry_forward_inventory_balance_query,
    insert_inventory_balance_query,
    inventory_balance_id_query,
    update_inventory_balance_query,
)

inventory_bp = Blueprint('inventory_bp', __name__)


@inventory_bp.route('/api/inventory-balances', methods=['GET'])
@inventory_bp.route('/api/reports/inventory-balances', methods=['GET'])
def get_inventory_balances():
    engine = require_db_engine()

    year_raw = request.args.get('year') or datetime.now().year
    try:
        year = int(year_raw)
    except (TypeError, ValueError):
        raise BadRequestError('year must be numeric')

    company_id = request.args.get('company_id')
    if not company_id:
        raise BadRequestError('company_id is required')

    with engine.connect() as conn:
        balance = build_inventory_balance_with_carry(conn, year, company_id)
        return jsonify({'balance': balance})


@inventory_bp.route('/api/inventory-balances', methods=['POST'])
@inventory_bp.route('/api/reports/inventory-balances', methods=['POST'])
def save_inventory_balances():
    engine = require_db_engine()

    payload = request.json or {}
    for field in ['year', 'company_id']:
        if field not in payload:
            raise BadRequestError(f'{field} is required')

    try:
        year = int(payload.get('year'))
    except (TypeError, ValueError):
        raise BadRequestError('year must be numeric')
    company_id = payload.get('company_id')

    beginning_amount = to_float(payload.get('beginning_inventory_amount'), 0.0)
    beginning_qty = to_float(payload.get('beginning_inventory_qty'), 0.0)
    ending_amount = to_float(payload.get('ending_inventory_amount'), 0.0)
    ending_qty = to_float(payload.get('ending_inventory_qty'), 0.0)
    base_value = to_float(payload.get('base_value'), 0.0)

    with engine.begin() as conn:
        now = datetime.now()

        existing = conn.execute(inventory_balance_id_query(), {
            'year': year,
            'company_id': company_id
        }).fetchone()

        if existing:
            conn.execute(update_inventory_balance_query(), {
                'beginning_amount': beginning_amount,
                'beginning_qty': beginning_qty,
                'ending_amount': ending_amount,
                'ending_qty': ending_qty,
                'base_value': base_value,
                'year': year,
                'company_id': company_id,
                'updated_at': now
            })
        else:
            conn.execute(insert_inventory_balance_query(), {
                'id': str(uuid.uuid4()),
                'company_id': company_id,
                'year': year,
                'beginning_amount': beginning_amount,
                'beginning_qty': beginning_qty,
                'ending_amount': ending_amount,
                'ending_qty': ending_qty,
                'base_value': base_value,
                'created_at': now,
                'updated_at': now
            })

        next_year = year + 1
        next_existing = conn.execute(inventory_balance_id_query(), {
            'year': next_year,
            'company_id': company_id
        }).fetchone()

        if not next_existing:
            conn.execute(insert_carry_forward_inventory_balance_query(), {
                'id': str(uuid.uuid4()),
                'company_id': company_id,
                'year': next_year,
                'beginning_amount': ending_amount,
                'beginning_qty': ending_qty,
                'base_value': ending_amount,
                'created_at': now,
                'updated_at': now
            })

        balance = build_inventory_balance_with_carry(conn, year, company_id)

    return jsonify({
        'success': True,
        'message': 'Inventory balance saved successfully',
        'balance': balance
    })
