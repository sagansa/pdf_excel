import json
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from backend.errors import ApiError, BadRequestError, NotFoundError
from backend.routes.accounting_utils import (
    current_timestamp_expression,
    require_db_engine,
    serialize_result_rows,
)
from backend.routes.company_queries import (
    clear_company_transactions_query,
    delete_company_query,
    get_companies_query,
    get_view_filters_query,
    insert_company_query,
    update_company_query,
    upsert_view_filters_query,
)

company_bp = Blueprint('company_bp', __name__)


@company_bp.route('/api/companies', methods=['GET'])
def get_companies():
    engine = require_db_engine()
    with engine.connect() as conn:
        result = conn.execute(get_companies_query())
        return jsonify({'companies': serialize_result_rows(result)})

@company_bp.route('/api/companies', methods=['POST'])
def create_company():
    engine = require_db_engine()
    data = request.json or {}
    name = str(data.get('name') or '').strip()
    short_name = data.get('short_name')
    if not name:
        raise BadRequestError('Company name is required')

    company_id = str(uuid.uuid4())
    now = datetime.now()
    with engine.begin() as conn:
        conn.execute(insert_company_query(), {
            'id': company_id,
            'name': name,
            'short_name': short_name,
            'now': now,
        })
    return jsonify({'id': company_id, 'name': name, 'short_name': short_name}), 201

@company_bp.route('/api/companies/<company_id>', methods=['PUT', 'DELETE'])
def manage_company(company_id):
    engine = require_db_engine()
    if request.method == 'DELETE':
        with engine.begin() as conn:
            conn.execute(clear_company_transactions_query(), {'cid': company_id})
            result = conn.execute(delete_company_query(), {'id': company_id})
            if result.rowcount == 0:
                raise NotFoundError('Company not found')
        return jsonify({'message': 'Company deleted successfully'})

    data = request.json or {}
    name = str(data.get('name') or '').strip()
    short_name = data.get('short_name')
    if not name:
        raise BadRequestError('Company name is required')

    with engine.begin() as conn:
        result = conn.execute(update_company_query(), {
            'id': company_id,
            'name': name,
            'short_name': short_name,
            'now': datetime.now(),
        })
        if result.rowcount == 0:
            raise NotFoundError('Company not found')
    return jsonify({'message': 'Company updated successfully'})

@company_bp.route('/api/filters/<view_name>', methods=['GET'])
def get_view_filters(view_name):
    engine = require_db_engine()
    with engine.connect() as conn:
        row = conn.execute(get_view_filters_query(), {'view': view_name}).fetchone()
        if not row:
            return jsonify({'filters': {}})

        filters = row[0]
        if isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except json.JSONDecodeError as exc:
                raise ApiError(f'Invalid stored filters JSON: {exc}', status_code=500, code='invalid_filters')
        return jsonify({'filters': filters or {}})

@company_bp.route('/api/filters', methods=['POST'])
def save_view_filters():
    data = request.json or {}
    view_name = data.get('view_name')
    filters = data.get('filters')

    if not view_name or filters is None:
        raise BadRequestError('view_name and filters are required')

    engine = require_db_engine()
    filters_json = json.dumps(filters)
    with engine.begin() as conn:
        conn.execute(
            upsert_view_filters_query(current_timestamp_expression(conn)),
            {'view': view_name, 'filters': filters_json}
        )
    return jsonify({'success': True})
