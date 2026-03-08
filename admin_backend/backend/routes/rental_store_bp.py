import datetime
import uuid

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from backend.db.schema import get_table_columns
from backend.errors import BadRequestError, NotFoundError
from backend.routes.accounting_utils import require_db_engine, serialize_result_rows
from backend.routes.rental_queries import build_stores_query

rental_store_bp = Blueprint('rental_store_bp', __name__)


@rental_store_bp.route('/api/stores', methods=['GET'])
def get_stores():
    company_id = request.args.get('company_id')
    engine = require_db_engine()
    with engine.connect() as conn:
        store_columns = get_table_columns(conn, 'rental_stores')
        store_name_expr = 's.store_name' if 'store_name' in store_columns else 's.name'
        store_code_expr = 's.store_code' if 'store_code' in store_columns else 'NULL'
        location_join = (
            'LEFT JOIN rental_locations l ON s.current_location_id = l.id'
            if 'current_location_id' in store_columns else
            'LEFT JOIN rental_locations l ON 1 = 0'
        )
        result = conn.execute(
            build_stores_query(store_name_expr, store_code_expr, location_join),
            {'company_id': company_id}
        )
        stores = serialize_result_rows(result, datetime_format='%Y-%m-%dT%H:%M:%S')
    return jsonify({'stores': stores})


@rental_store_bp.route('/api/stores', methods=['POST'])
def create_store():
    data = request.json or {}
    engine = require_db_engine()

    if not data.get('company_id') or not data.get('store_name'):
        raise BadRequestError('company_id and store_name are required')

    store_id = str(uuid.uuid4())
    now = datetime.datetime.now()

    with engine.begin() as conn:
        store_columns = get_table_columns(conn, 'rental_stores')
        payload = {
            'id': store_id,
            'company_id': data['company_id'],
            'store_code': data.get('store_code'),
            'store_name': data.get('store_name'),
            'name': data.get('store_name'),
            'current_location_id': data.get('current_location_id'),
            'status': data.get('status', 'active'),
            'notes': data.get('notes'),
            'created_at': now,
            'updated_at': now
        }

        insert_columns = [column for column in payload.keys() if column in store_columns]
        columns_sql = ', '.join(insert_columns)
        values_sql = ', '.join(f":{column}" for column in insert_columns)
        conn.execute(text(f"""
            INSERT INTO rental_stores ({columns_sql})
            VALUES ({values_sql})
        """), payload)
    return jsonify({'id': store_id, 'message': 'Store created successfully'}), 201


@rental_store_bp.route('/api/stores/<store_id>', methods=['PUT'])
def update_store(store_id):
    data = request.json or {}
    engine = require_db_engine()
    now = datetime.datetime.now()

    with engine.begin() as conn:
        store_columns = get_table_columns(conn, 'rental_stores')
        payload = {
            'id': store_id,
            'store_code': data.get('store_code'),
            'store_name': data.get('store_name'),
            'name': data.get('store_name'),
            'status': data.get('status'),
            'notes': data.get('notes'),
            'updated_at': now
        }
        update_columns = [column for column in payload.keys() if column in store_columns and column != 'id']
        if update_columns:
            set_clause = ', '.join(f"{column} = :{column}" for column in update_columns)
            result = conn.execute(text(f"""
                UPDATE rental_stores
                SET {set_clause}
                WHERE id = :id
            """), payload)
            if int(result.rowcount or 0) == 0:
                raise NotFoundError('Store not found')
    return jsonify({'message': 'Store updated successfully'})


@rental_store_bp.route('/api/stores/<store_id>', methods=['DELETE'])
def delete_store(store_id):
    engine = require_db_engine()
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM rental_stores WHERE id = :id"), {'id': store_id})
        if int(result.rowcount or 0) == 0:
            raise NotFoundError('Store not found')
    return jsonify({'message': 'Store deleted successfully'})
