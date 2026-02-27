from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from sqlalchemy import text
import uuid
from backend.db.session import get_db_engine

initial_capital_bp = Blueprint('initial_capital', __name__)

@initial_capital_bp.route('/api/initial-capital', methods=['GET'])
def get_initial_capital():
    """Get initial capital setting for a company"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    company_id = request.args.get('company_id')
    current_app.logger.info(f"GET /api/initial-capital - company_id: {company_id}")
    
    if not company_id or company_id == 'null' or company_id == 'undefined':
        return jsonify({'error': 'company_id is required and must be a valid value'}), 400
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, company_id, amount, start_year, description, created_at, updated_at
                FROM initial_capital_settings
                WHERE company_id = :company_id
            """)
            
            result = conn.execute(query, {'company_id': company_id}).fetchone()
            
            if result:
                d = dict(result._mapping)
                d['amount'] = float(d['amount']) if d['amount'] else 0.0
                d['start_year'] = int(d['start_year']) if d['start_year'] else datetime.now().year
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                return jsonify({'setting': d})
            else:
                return jsonify({'setting': None})
    except Exception as e:
        current_app.logger.error(f"Error getting initial capital: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@initial_capital_bp.route('/api/initial-capital', methods=['POST'])
def save_initial_capital():
    """Save or update initial capital setting"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        company_id = data.get('company_id')
        amount = data.get('amount')
        start_year = data.get('start_year')
        description = data.get('description', '')
        
        current_app.logger.info(f"POST /api/initial-capital - company_id: {company_id}, amount: {amount}")
        
        if not company_id or company_id in ['null', 'undefined', '']:
            return jsonify({'error': 'company_id is required and must be a valid value'}), 400
        
        if amount is None:
            return jsonify({'error': 'amount is required'}), 400
        
        try:
            amount = float(amount)
            start_year = int(start_year) if start_year else datetime.now().year
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid data format: {str(e)}'}), 400
        
        with engine.begin() as conn:
            # Check if setting exists
            existing = conn.execute(
                text("SELECT id FROM initial_capital_settings WHERE company_id = :company_id"),
                {'company_id': company_id}
            ).fetchone()
            
            if existing:
                # Update existing
                conn.execute(
                    text("""
                        UPDATE initial_capital_settings
                        SET amount = :amount,
                            start_year = :start_year,
                            description = :description,
                            updated_at = NOW()
                        WHERE company_id = :company_id
                    """),
                    {
                        'company_id': company_id,
                        'amount': amount,
                        'start_year': start_year,
                        'description': description
                    }
                )
            else:
                # Insert new
                conn.execute(
                    text("""
                        INSERT INTO initial_capital_settings
                        (id, company_id, amount, start_year, description, created_at, updated_at)
                        VALUES (:id, :company_id, :amount, :start_year, :description, NOW(), NOW())
                    """),
                    {
                        'id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'amount': amount,
                        'start_year': start_year,
                        'description': description
                    }
                )
            
            return jsonify({'message': 'Initial capital setting saved successfully', 'success': True})
    except Exception as e:
        current_app.logger.error(f"Error saving initial capital: {e}")
        return jsonify({'error': str(e)}), 500

@initial_capital_bp.route('/api/initial-capital', methods=['DELETE'])
def delete_initial_capital():
    """Delete initial capital setting"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    company_id = request.args.get('company_id')
    
    if not company_id:
        return jsonify({'error': 'company_id is required'}), 400
    
    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM initial_capital_settings WHERE company_id = :company_id"),
                {'company_id': company_id}
            )
            return jsonify({'message': 'Initial capital setting deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
