import uuid
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from backend.db.session import get_db_engine

fiscal_corrections_bp = Blueprint('fiscal_corrections_bp', __name__, url_prefix='/api/fiscal-corrections')

@fiscal_corrections_bp.route('', methods=['GET'])
def get_corrections():
    company_id = request.args.get('company_id')
    period_date = request.args.get('period_date') # e.g. YYYY-MM-DD
    
    if not company_id:
        return jsonify({'error': 'company_id is required'}), 400
        
    engine, err = get_db_engine()
    if err:
        return jsonify({'error': err}), 500
        
    try:
        with engine.connect() as conn:
            query = """
                SELECT fc.id, fc.company_id, fc.coa_id, fc.period_date, 
                       fc.correction_type, fc.amount, fc.reason,
                       c.code as coa_code, c.name as coa_name
                FROM fiscal_corrections fc
                JOIN chart_of_accounts c ON fc.coa_id = c.id
                WHERE fc.company_id = :company_id
            """
            params = {'company_id': company_id}
            
            if period_date:
                # Optionally filter by year or exact date depending on requirement
                # Let's just return all for now or filter if provided exactly
                query += " AND fc.period_date = :period_date"
                params['period_date'] = period_date
                
            query += " ORDER BY fc.period_date DESC, c.code ASC"
            
            result = conn.execute(text(query), params).mappings().all()
            
            corrections = [
                {
                    'id': row['id'],
                    'company_id': row['company_id'],
                    'coa_id': row['coa_id'],
                    'coa_code': row['coa_code'],
                    'coa_name': row['coa_name'],
                    'period_date': str(row['period_date']),
                    'correction_type': row['correction_type'],
                    'amount': float(row['amount']),
                    'reason': row['reason']
                }
                for row in result
            ]
            
            return jsonify({'data': corrections}), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@fiscal_corrections_bp.route('', methods=['POST'])
def create_correction():
    data = request.json
    engine, err = get_db_engine()
    if err:
        return jsonify({'error': err}), 500
        
    required_fields = ['company_id', 'coa_id', 'period_date', 'correction_type', 'amount']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
            
    correction_id = str(uuid.uuid4())
    
    try:
        with engine.begin() as conn:
            query = text("""
                INSERT INTO fiscal_corrections 
                (id, company_id, coa_id, period_date, correction_type, amount, reason)
                VALUES (:id, :company_id, :coa_id, :period_date, :correction_type, :amount, :reason)
            """)
            conn.execute(query, {
                'id': correction_id,
                'company_id': data['company_id'],
                'coa_id': data['coa_id'],
                'period_date': data['period_date'],
                'correction_type': data['correction_type'],
                'amount': float(data['amount']),
                'reason': data.get('reason', '')
            })
            
            return jsonify({
                'message': 'Fiscal correction created successfully',
                'id': correction_id
            }), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@fiscal_corrections_bp.route('/<correction_id>', methods=['DELETE'])
def delete_correction(correction_id):
    engine, err = get_db_engine()
    if err:
        return jsonify({'error': err}), 500
        
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM fiscal_corrections WHERE id = :id"),
                {'id': correction_id}
            )
            
            if result.rowcount == 0:
                return jsonify({'error': 'Correction not found'}), 404
                
            return jsonify({'message': 'Fiscal correction deleted successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
