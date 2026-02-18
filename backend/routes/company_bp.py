import uuid
import json
from flask import Blueprint, request, jsonify
from datetime import datetime
from sqlalchemy import text
from backend.db.session import get_db_engine

company_bp = Blueprint('company_bp', __name__)

@company_bp.route('/api/companies', methods=['GET'])
def get_companies():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM companies ORDER BY name ASC"))
            companies = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                companies.append(d)
            return jsonify({'companies': companies})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@company_bp.route('/api/companies', methods=['POST'])
def create_company():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        name = data.get('name')
        short_name = data.get('short_name')
        if not name:
            return jsonify({'error': 'Company name is required'}), 400
        
        company_id = str(uuid.uuid4())
        now = datetime.now()
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO companies (id, name, short_name, created_at, updated_at) VALUES (:id, :name, :short_name, :now, :now)"),
                {'id': company_id, 'name': name, 'short_name': short_name, 'now': now}
            )
            conn.commit()
            return jsonify({'id': company_id, 'name': name, 'short_name': short_name}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@company_bp.route('/api/companies/<company_id>', methods=['PUT', 'DELETE'])
def manage_company(company_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    if request.method == 'DELETE':
        try:
            with engine.connect() as conn:
                conn.execute(text("UPDATE transactions SET company_id = NULL WHERE company_id = :cid"), {'cid': company_id})
                conn.execute(text("DELETE FROM companies WHERE id = :id"), {'id': company_id})
                conn.commit()
                return jsonify({'message': 'Company deleted successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'PUT':
        try:
            data = request.json
            name = data.get('name')
            short_name = data.get('short_name')
            if not name:
                return jsonify({'error': 'Company name is required'}), 400
            
            with engine.connect() as conn:
                conn.execute(
                    text("UPDATE companies SET name = :name, short_name = :short_name, updated_at = :now WHERE id = :id"),
                    {'id': company_id, 'name': name, 'short_name': short_name, 'now': datetime.now()}
                )
                conn.commit()
                return jsonify({'message': 'Company updated successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@company_bp.route('/api/filters/<view_name>', methods=['GET'])
def get_view_filters(view_name):
    """Retrieve saved filters for a specific view"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
        
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT filters FROM user_filters WHERE view_name = :view"),
                {'view': view_name}
            )
            row = result.fetchone()
            if row:
                filters = row[0]
                if isinstance(filters, str):
                    filters = json.loads(filters)
                return jsonify({'filters': filters})
            return jsonify({'filters': {}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@company_bp.route('/api/filters', methods=['POST'])
def save_view_filters():
    """Save filters for a specific view"""
    data = request.json
    view_name = data.get('view_name')
    filters = data.get('filters')
    
    if not view_name or filters is None:
        return jsonify({'error': 'view_name and filters are required'}), 400
        
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
        
    try:
        filters_json = json.dumps(filters)
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO user_filters (view_name, filters) 
                    VALUES (:view, :filters)
                    ON DUPLICATE KEY UPDATE filters = :filters, updated_at = NOW()
                """),
                {'view': view_name, 'filters': filters_json}
            )
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
