import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from backend.errors import BadRequestError
from backend.routes.accounting_utils import (
    current_timestamp_expression,
    require_db_engine,
    serialize_row_values,
)
from backend.routes.master_data.initial_capital_queries import (
    delete_initial_capital_by_company_query,
    get_initial_capital_by_company_query,
    get_initial_capital_id_by_company_query,
    insert_initial_capital_query,
    update_initial_capital_query,
)

initial_capital_bp = Blueprint('initial_capital', __name__)

def _normalize_company_id(value):
    company_id = str(value or '').strip()
    if not company_id or company_id in {'null', 'undefined'}:
        raise BadRequestError('company_id is required and must be a valid value')
    return company_id


def _serialize_initial_capital_row(row):
    if not row:
        return None

    data = serialize_row_values(row._mapping)
    data['amount'] = float(data.get('amount') or 0.0)
    data['previous_retained_earnings_amount'] = float(data.get('previous_retained_earnings_amount') or 0.0)
    data['start_year'] = int(data['start_year']) if data.get('start_year') else datetime.now().year
    return data

@initial_capital_bp.route('/api/initial-capital', methods=['GET'])
def get_initial_capital():
    engine = require_db_engine()
    company_id = _normalize_company_id(request.args.get('company_id'))

    with engine.connect() as conn:
        result = conn.execute(
            get_initial_capital_by_company_query(),
            {'company_id': company_id}
        ).fetchone()
        return jsonify({'setting': _serialize_initial_capital_row(result)})

@initial_capital_bp.route('/api/initial-capital', methods=['POST'])
def save_initial_capital():
    engine = require_db_engine()
    data = request.get_json(silent=True)
    if not data:
        raise BadRequestError('Request body must be JSON')

    company_id = _normalize_company_id(data.get('company_id'))
    amount_raw = data.get('amount')
    if amount_raw is None:
        raise BadRequestError('amount is required')
    previous_retained_earnings_raw = data.get('previous_retained_earnings_amount', 0)

    try:
        amount = float(amount_raw)
        previous_retained_earnings_amount = float(previous_retained_earnings_raw or 0)
        start_year = int(data.get('start_year')) if data.get('start_year') else datetime.now().year
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f'Invalid data format: {exc}')

    description = data.get('description', '')

    with engine.begin() as conn:
        now_expr = current_timestamp_expression(conn)
        existing = conn.execute(
            get_initial_capital_id_by_company_query(),
            {'company_id': company_id}
        ).fetchone()

        params = {
            'company_id': company_id,
            'amount': amount,
            'previous_retained_earnings_amount': previous_retained_earnings_amount,
            'start_year': start_year,
            'description': description,
        }

        if existing:
            conn.execute(update_initial_capital_query(now_expr), params)
        else:
            conn.execute(insert_initial_capital_query(now_expr), {
                'id': str(uuid.uuid4()),
                **params,
            })

    return jsonify({'message': 'Initial capital setting saved successfully', 'success': True})

@initial_capital_bp.route('/api/initial-capital', methods=['DELETE'])
def delete_initial_capital():
    engine = require_db_engine()
    company_id = _normalize_company_id(request.args.get('company_id'))

    with engine.begin() as conn:
        conn.execute(
            delete_initial_capital_by_company_query(),
            {'company_id': company_id}
        )
    return jsonify({'message': 'Initial capital setting deleted successfully'})
