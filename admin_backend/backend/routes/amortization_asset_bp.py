import uuid
from flask import Blueprint, request, jsonify
from datetime import date
from backend.errors import BadRequestError, NotFoundError
from backend.routes.accounting_utils import require_db_engine, serialize_row_values
from backend.routes.amortization_queries import (
    delete_amortization_asset_query,
    insert_amortization_asset_query,
    pending_amortization_transactions_query,
    transaction_total_for_ids_query,
    unlink_transactions_by_asset_query,
    update_amortization_asset_query,
    update_transactions_asset_link_query,
)

amortization_asset_bp = Blueprint('amortization_asset_bp', __name__)

@amortization_asset_bp.route('/api/reports/pending-amortization', methods=['GET'])
def get_pending_amortization_transactions():
    """Retrieve transactions marked as assets that are not yet linked to an amortization_assets record"""
    engine = require_db_engine()
    company_id = request.args.get('company_id')
    year = request.args.get('year')
    current_asset_id = request.args.get('current_asset_id')

    if not company_id:
        raise BadRequestError('company_id is required')

    year_int = None
    if year not in (None, ''):
        try:
            year_int = int(year)
        except (TypeError, ValueError):
            pass

    with engine.connect() as conn:
        params = {'company_id': company_id}
        if year_int:
            params['year'] = year_int
        if current_asset_id:
            params['current_asset_id'] = current_asset_id

        query = pending_amortization_transactions_query(
            include_year=bool(year_int),
            include_current_asset=bool(current_asset_id),
        )
        result = conn.execute(query, params)
        transactions = []

        for row in result:
            d = serialize_row_values(row._mapping, datetime_format='%Y-%m-%d')
            transactions.append(d)

        return jsonify({
            'transactions': transactions,
            'total_count': len(transactions)
        })

@amortization_asset_bp.route('/api/amortization-assets', methods=['POST'])
def create_amortization_asset():
    """Create a new amortization asset and link transactions to it"""
    data = request.json or {}
    company_id = data.get('company_id')
    asset_name = data.get('asset_name')
    asset_group_id = data.get('asset_group_id')
    acquisition_date = data.get('acquisition_date')
    transaction_ids = data.get('transaction_ids', [])

    if not all([company_id, asset_name, asset_group_id, acquisition_date, transaction_ids]):
        raise BadRequestError('Missing required fields or transactions')

    engine = require_db_engine()
    with engine.begin() as conn:
        params = {'company_id': company_id, 'transaction_ids': transaction_ids}
        result = conn.execute(transaction_total_for_ids_query(), params).fetchone()
        if not result or not result[0]:
            raise NotFoundError('Selected transactions not found or have zero value')

        acquisition_cost = result[0]
        asset_id = str(uuid.uuid4())
        conn.execute(insert_amortization_asset_query(), {
            'id': asset_id,
            'company_id': company_id,
            'asset_group_id': asset_group_id,
            'asset_name': asset_name,
            'acquisition_date': acquisition_date,
            'acquisition_cost': acquisition_cost
        })

        conn.execute(update_transactions_asset_link_query(), {
            **params,
            'asset_id': asset_id,
        })

    return jsonify({
        'message': 'Amortization asset created successfully',
        'asset_id': asset_id,
        'acquisition_cost': float(acquisition_cost)
    }), 201

@amortization_asset_bp.route('/api/amortization-assets/<asset_id>', methods=['PUT'])
def update_amortization_asset(asset_id):
    """Update an amortization asset's metadata"""
    data = request.json or {}
    asset_name = data.get('asset_name')
    asset_group_id = data.get('asset_group_id')
    acquisition_date = data.get('acquisition_date')
    transaction_ids = data.get('transaction_ids')

    if not asset_name:
        raise BadRequestError('asset_name is required')

    engine = require_db_engine()
    with engine.begin() as conn:
        set_fields = ["asset_name = :asset_name"]
        params = {'asset_id': asset_id, 'asset_name': asset_name}

        if asset_group_id:
            set_fields.append("asset_group_id = :asset_group_id")
            params['asset_group_id'] = asset_group_id
        if acquisition_date:
            set_fields.append("acquisition_date = :acquisition_date")
            set_fields.append("amortization_start_date = :acquisition_date")
            params['acquisition_date'] = acquisition_date

        if transaction_ids is not None:
            conn.execute(unlink_transactions_by_asset_query(), {'asset_id': asset_id})

            new_cost = 0
            if len(transaction_ids) > 0:
                cost_params = {
                    'company_id': data.get('company_id'),
                    'transaction_ids': transaction_ids,
                }
                result = conn.execute(transaction_total_for_ids_query(), cost_params).fetchone()
                if not result or not result[0]:
                    raise NotFoundError('Selected transactions not found or have zero value')

                new_cost = result[0]
                conn.execute(update_transactions_asset_link_query(), {
                    **cost_params,
                    'asset_id': asset_id,
                })

            set_fields.append("acquisition_cost = :acquisition_cost")
            params['acquisition_cost'] = new_cost

        result = conn.execute(update_amortization_asset_query(', '.join(set_fields)), params)

    if result.rowcount == 0:
        raise NotFoundError('Asset not found')
    return jsonify({'message': 'Amortization asset updated successfully'}), 200

@amortization_asset_bp.route('/api/amortization-assets/<asset_id>', methods=['DELETE'])
def delete_amortization_asset(asset_id):
    """Delete an amortization asset and unlink its transactions"""
    engine = require_db_engine()
    with engine.begin() as conn:
        conn.execute(unlink_transactions_by_asset_query(), {'asset_id': asset_id})

        result = conn.execute(delete_amortization_asset_query(), {'asset_id': asset_id})

    if result.rowcount == 0:
        raise NotFoundError('Asset not found')
    return jsonify({'message': 'Amortization asset deleted and transactions unlinked successfully'}), 200
