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
    fiscal_category = data.get('fiscal_category', 'DEDUCTIBLE')

    if not all([code, name, category]):
        raise BadRequestError('Code, name, and category are required')

    coa_id = str(uuid.uuid4())
    now = datetime.now()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO chart_of_accounts
            (id, code, name, category, subcategory, description, fiscal_category, is_active, parent_id, created_at, updated_at)
            VALUES (:id, :code, :name, :category, :subcategory, :description, :fiscal_category, :is_active, :parent_id, :created_at, :updated_at)
        """), {
            'id': coa_id,
            'code': code,
            'name': name,
            'category': category,
            'subcategory': data.get('subcategory'),
            'description': data.get('description'),
            'fiscal_category': fiscal_category,
            'is_active': data.get('is_active', True),
            'parent_id': data.get('parent_id'),
            'created_at': now,
            'updated_at': now
        })
    return jsonify({'message': 'COA created successfully', 'id': coa_id}), 201


@coa_bp.route('/api/coa/<coa_id>', methods=['PUT'])
def update_coa(coa_id):
    engine = require_db_engine()
    data = request.json or {}
    now = datetime.now()
    
    # Allowed fields to update
    fields = ['code', 'name', 'category', 'subcategory', 'description', 'fiscal_category', 'is_active']
    update_parts = []
    params = {'id': coa_id, 'updated_at': now}
    
    for field in fields:
        if field in data:
            update_parts.append(f"{field} = :{field}")
            params[field] = data[field]
            
    if not update_parts:
        return jsonify({'message': 'No changes provided'}), 200
        
    update_stmt = f"""
        UPDATE chart_of_accounts 
        SET {', '.join(update_parts)}, updated_at = :updated_at 
        WHERE id = :id
    """
    
    with engine.begin() as conn:
        conn.execute(text(update_stmt), params)
        
    return jsonify({'message': 'COA updated successfully'})
