import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from backend.errors import BadRequestError
from backend.routes.accounting_utils import require_db_engine, serialize_result_rows

coa_bp = Blueprint('coa_bp', __name__)


@coa_bp.route('/api/coa', methods=['GET'])
def get_chart_of_accounts():
    engine = require_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT * FROM chart_of_accounts
            WHERE is_active = TRUE
            ORDER BY code ASC
        """))
        return jsonify({'coa': serialize_result_rows(result)})


@coa_bp.route('/api/coa', methods=['POST'])
def create_coa():
    engine = require_db_engine()
    data = request.json or {}
    code = data.get('code')
    name = data.get('name')
    category = data.get('category')

    if not all([code, name, category]):
        raise BadRequestError('Code, name, and category are required')

    coa_id = str(uuid.uuid4())
    now = datetime.now()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO chart_of_accounts
            (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at)
            VALUES (:id, :code, :name, :category, :subcategory, :description, :is_active, :parent_id, :created_at, :updated_at)
        """), {
            'id': coa_id,
            'code': code,
            'name': name,
            'category': category,
            'subcategory': data.get('subcategory'),
            'description': data.get('description'),
            'is_active': data.get('is_active', True),
            'parent_id': data.get('parent_id'),
            'created_at': now,
            'updated_at': now
        })
    return jsonify({'message': 'COA created successfully', 'id': coa_id}), 201
