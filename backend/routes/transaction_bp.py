import uuid
from flask import Blueprint, request, jsonify
from datetime import datetime
from decimal import Decimal
from sqlalchemy import text
import uuid
from backend.db.session import get_db_engine

transaction_bp = Blueprint('transaction_bp', __name__)

@transaction_bp.route('/api/transactions', methods=['GET'])
def get_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT t.*, m.internal_report, m.personal_use, m.tax_report, 
                       c.name as company_name, c.short_name as company_short_name
                FROM transactions t 
                LEFT JOIN marks m ON t.mark_id = m.id 
                LEFT JOIN companies c ON t.company_id = c.id
                ORDER BY t.txn_date DESC, t.created_at DESC
            """)
            result = conn.execute(query)
            transactions = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, Decimal):
                        d[key] = float(value)
                transactions.append(d)
            return jsonify({'transactions': transactions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/upload-summary', methods=['GET'])
def get_upload_summary():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT t.source_file, 
                       COUNT(*) as transaction_count, 
                       MIN(t.txn_date) as start_date, 
                       MAX(t.txn_date) as end_date,
                       t.bank_code,
                       c.name as company_name,
                       t.company_id,
                       SUM(CASE WHEN t.db_cr = 'DB' THEN t.amount ELSE 0 END) as total_debit,
                       SUM(CASE WHEN t.db_cr = 'CR' THEN t.amount ELSE 0 END) as total_credit,
                       MAX(t.created_at) as last_upload
                FROM transactions t
                LEFT JOIN companies c ON t.company_id = c.id
                GROUP BY t.source_file, t.bank_code, t.company_id
                ORDER BY last_upload DESC
            """)
            result = conn.execute(query)
            summary = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, Decimal):
                        d[key] = float(value)
                summary.append(d)
            return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/delete-by-source', methods=['POST'])
def delete_by_source():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    data = request.json
    source_file = data.get('source_file')
    bank_code = data.get('bank_code')
    company_id = data.get('company_id')
    
    if not source_file:
        return jsonify({'error': 'source_file is required'}), 400
        
    try:
        with engine.begin() as conn:
            where_clauses = ["source_file = :source_file"]
            params = {"source_file": source_file}
            
            if bank_code:
                where_clauses.append("bank_code = :bank_code")
                params["bank_code"] = bank_code
            if company_id:
                where_clauses.append("company_id = :company_id")
                params["company_id"] = company_id
            else:
                where_clauses.append("company_id IS NULL")
                
            query = text(f"DELETE FROM transactions WHERE {' AND '.join(where_clauses)}")
            result = conn.execute(query, params)
            return jsonify({'message': f'Deleted {result.rowcount} transactions'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/marks', methods=['GET'])
def get_marks():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM marks ORDER BY personal_use ASC"))
            marks = []
            marks_dict = {}
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                d['mappings'] = []
                marks.append(d)
                marks_dict[d['id']] = d

            mapping_query = text("""
                SELECT mcm.mark_id, mcm.mapping_type, coa.code, coa.name
                FROM mark_coa_mapping mcm
                JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            """)
            mapping_result = conn.execute(mapping_query)
            
            for row in mapping_result:
                m = dict(row._mapping)
                mark_id = m['mark_id']
                if mark_id in marks_dict:
                    marks_dict[mark_id]['mappings'].append({
                        'code': m['code'],
                        'name': m['name'],
                        'type': m['mapping_type']
                    })

            return jsonify({'marks': marks})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/marks', methods=['POST'])
def create_mark():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        now = datetime.now()
        mark_id = str(uuid.uuid4())
        new_row = {
            'id': mark_id,
            'internal_report': data.get('internal_report', ''),
            'personal_use': data.get('personal_use', ''),
            'tax_report': data.get('tax_report', ''),
            'created_at': now,
            'updated_at': now
        }
        with engine.connect() as conn:
            query = text("""
                INSERT INTO marks (id, internal_report, personal_use, tax_report, created_at, updated_at)
                VALUES (:id, :internal_report, :personal_use, :tax_report, :created_at, :updated_at)
            """)
            conn.execute(query, new_row)
            conn.commit()
            return jsonify({'message': 'Mark created successfully', 'id': mark_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/marks/<mark_id>', methods=['PUT', 'DELETE'])
def update_or_delete_mark(mark_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        if request.method == 'DELETE':
            with engine.connect() as conn:
                conn.execute(text("UPDATE transactions SET mark_id = NULL WHERE mark_id = :id"), {'id': mark_id})
                conn.execute(text("DELETE FROM marks WHERE id = :id"), {'id': mark_id})
                conn.commit()
                return jsonify({'message': 'Mark deleted successfully'})
        
        data = request.json
        internal = data.get('internal_report')
        personal = data.get('personal_use')
        tax = data.get('tax_report')
        
        with engine.connect() as conn:
            query = text("""
                UPDATE marks 
                SET internal_report = :internal, personal_use = :personal, tax_report = :tax 
                WHERE id = :id
            """)
            conn.execute(query, {'id': mark_id, 'internal': internal, 'personal': personal, 'tax': tax})
            conn.commit()
            return jsonify({'message': 'Mark updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/<txn_id>/assign-mark', methods=['POST'])
def assign_mark_transaction(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        mark_id = data.get('mark_id')
        now = datetime.now()
        with engine.connect() as conn:
            query = text("UPDATE transactions SET mark_id = :mark_id, updated_at = :updated_at WHERE id = :id")
            conn.execute(query, {'id': txn_id, 'mark_id': mark_id, 'updated_at': now})
            conn.commit()
            return jsonify({'message': 'Transaction marked successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/<txn_id>/assign-company', methods=['POST'])
def assign_company_transaction(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        company_id = data.get('company_id')
        now = datetime.now()
        with engine.connect() as conn:
            query = text("UPDATE transactions SET company_id = :company_id, updated_at = :updated_at WHERE id = :id")
            conn.execute(query, {'id': txn_id, 'company_id': company_id, 'updated_at': now})
            conn.commit()
            return jsonify({'message': 'Company assigned successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/bulk-mark', methods=['POST'])
def bulk_mark_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        txn_ids = data.get('transaction_ids', [])
        mark_id = data.get('mark_id') or None
        
        if not txn_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400
            
        now = datetime.now()
        with engine.connect() as conn:
            query = text("UPDATE transactions SET mark_id = :mark_id, updated_at = :updated_at WHERE id IN :ids")
            conn.execute(query, {'ids': txn_ids, 'mark_id': mark_id, 'updated_at': now})
            conn.commit()
            return jsonify({'message': f'{len(txn_ids)} transactions updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/bulk-assign-company', methods=['POST'])
def bulk_assign_company_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        txn_ids = data.get('transaction_ids', [])
        company_id = data.get('company_id') or None
        
        if not txn_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400
            
        now = datetime.now()
        with engine.connect() as conn:
            query = text("UPDATE transactions SET company_id = :company_id, updated_at = :updated_at WHERE id IN :ids")
            conn.execute(query, {'ids': txn_ids, 'company_id': company_id, 'updated_at': now})
            conn.commit()
            return jsonify({'message': f'{len(txn_ids)} transactions updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/<txn_id>', methods=['DELETE'])
def delete_transaction(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM transactions WHERE id = :id"), {'id': txn_id})
            conn.commit()
            return jsonify({'message': 'Transaction deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/bulk-delete', methods=['POST'])
def bulk_delete_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        txn_ids = data.get('transaction_ids', [])
        if not txn_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM transactions WHERE id IN :ids"), {'ids': txn_ids})
            conn.commit()
            return jsonify({'message': f'{len(txn_ids)} transactions deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/<transaction_id>/notes', methods=['PUT'])
def update_transaction_notes(transaction_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        notes = data.get('notes')
        with engine.connect() as conn:
            query = text("UPDATE transactions SET notes = :notes, updated_at = :now WHERE id = :id")
            conn.execute(query, {'id': transaction_id, 'notes': notes, 'now': datetime.now()})
            conn.commit()
            return jsonify({'message': 'Notes updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Marking - COA Mappings
@transaction_bp.route('/api/marks/<mark_id>/coa-mappings', methods=['GET'])
def get_mark_coa_mappings(mark_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT mcm.*, coa.code, coa.name, coa.category
                FROM mark_coa_mapping mcm
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                WHERE mcm.mark_id = :mark_id
                ORDER BY coa.code
            """), {'mark_id': mark_id})
            
            mappings = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                mappings.append(d)
            return jsonify({'mappings': mappings})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/marks/<mark_id>/coa-mappings', methods=['POST'])
def create_mark_coa_mapping(mark_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        coa_id = data.get('coa_id')
        mapping_type = data.get('mapping_type', 'DEBIT')
        
        if not coa_id:
            return jsonify({'error': 'COA ID is required'}), 400
        
        if mapping_type not in ['DEBIT', 'CREDIT']:
            return jsonify({'error': 'Invalid mapping type'}), 400
        
        mapping_id = str(uuid.uuid4())
        now = datetime.now()
        
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO mark_coa_mapping 
                (id, mark_id, coa_id, mapping_type, notes, created_at, updated_at)
                VALUES (:id, :mark_id, :coa_id, :mapping_type, :notes, :created_at, :updated_at)
            """), {
                'id': mapping_id,
                'mark_id': mark_id,
                'coa_id': coa_id,
                'mapping_type': mapping_type,
                'notes': data.get('notes'),
                'created_at': now,
                'updated_at': now
            })
            conn.commit()
            return jsonify({'message': 'Mapping created successfully', 'id': mapping_id}), 201
    except Exception as e:
        if 'Duplicate entry' in str(e):
            return jsonify({'error': 'This mapping already exists'}), 409
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/mark-coa-mappings/fix-expense-mappings', methods=['POST'])
def fix_expense_mappings():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.begin() as conn:
            query = text("""
                SELECT mcm.id, mcm.mark_id, mcm.coa_id, mcm.mapping_type, 
                       coa.code, coa.name, coa.category, m.personal_use
                FROM mark_coa_mapping mcm
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                INNER JOIN marks m ON mcm.mark_id = m.id
                WHERE coa.category IN ('EXPENSE', 'COGS', 'OTHER_EXPENSE')
                  AND mcm.mapping_type = 'CREDIT'
            """)
            
            result = conn.execute(query)
            incorrect_mappings = list(result)
            
            if not incorrect_mappings:
                return jsonify({
                    'message': 'No incorrect mappings found',
                    'fixed_count': 0,
                    'mappings': []
                })
            
            update_query = text("""
                UPDATE mark_coa_mapping
                SET mapping_type = 'DEBIT'
                WHERE id = :mapping_id
            """)
            
            fixed_mappings = []
            for mapping in incorrect_mappings:
                conn.execute(update_query, {'mapping_id': mapping.id})
                fixed_mappings.append({
                    'id': mapping.id,
                    'mark': mapping.personal_use,
                    'coa_code': mapping.code,
                    'coa_name': mapping.name,
                    'old_type': 'CREDIT',
                    'new_type': 'DEBIT'
                })
            
            return jsonify({
                'message': f'Successfully fixed {len(fixed_mappings)} expense mappings',
                'fixed_count': len(fixed_mappings),
                'mappings': fixed_mappings
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/mark-coa-mappings/fix-revenue-mappings', methods=['POST'])
def fix_revenue_mappings():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.begin() as conn:
            query = text("""
                SELECT mcm.id, mcm.mark_id, mcm.coa_id, mcm.mapping_type, 
                       coa.code, coa.name, coa.category, m.personal_use
                FROM mark_coa_mapping mcm
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                INNER JOIN marks m ON mcm.mark_id = m.id
                WHERE coa.category IN ('REVENUE', 'OTHER_REVENUE')
                  AND mcm.mapping_type = 'DEBIT'
            """)
            
            result = conn.execute(query)
            incorrect_mappings = list(result)
            
            if not incorrect_mappings:
                return jsonify({
                    'message': 'No incorrect mappings found',
                    'fixed_count': 0,
                    'mappings': []
                })
            
            update_query = text("""
                UPDATE mark_coa_mapping
                SET mapping_type = 'CREDIT'
                WHERE id = :mapping_id
            """)
            
            fixed_mappings = []
            for mapping in incorrect_mappings:
                conn.execute(update_query, {'mapping_id': mapping.id})
                fixed_mappings.append({
                    'id': mapping.id,
                    'mark': mapping.personal_use,
                    'coa_code': mapping.code,
                    'coa_name': mapping.name,
                    'old_type': 'DEBIT',
                    'new_type': 'CREDIT'
                })
            
            return jsonify({
                'message': f'Successfully fixed {len(fixed_mappings)} revenue mappings',
                'fixed_count': len(fixed_mappings),
                'mappings': fixed_mappings
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/mark-coa-mappings/<mapping_id>', methods=['DELETE'])
def delete_mark_coa_mapping(mapping_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM mark_coa_mapping WHERE id = :id"), {'id': mapping_id})
            conn.commit()
            return jsonify({'message': 'Mapping deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/<txn_id>/splits', methods=['GET'])
def get_transaction_splits(txn_id):
    """Get splits for a specific transaction"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            # Get main transaction
            main_query = text("""
                SELECT id, description, amount, db_cr, txn_date, mark_id, company_id, notes
                FROM transactions 
                WHERE id = :txn_id
            """)
            main_result = conn.execute(main_query, {'txn_id': txn_id}).fetchone()
            
            if not main_result:
                return jsonify({'error': 'Transaction not found'}), 404
            
            # Get split transactions
            splits_query = text("""
                SELECT id, description, amount, db_cr, txn_date, mark_id, notes
                FROM transactions 
                WHERE parent_id = :txn_id
                ORDER BY txn_date
            """)
            splits_result = conn.execute(splits_query, {'txn_id': txn_id}).fetchall()
            
            main_transaction = dict(main_result._mapping)
            split_transactions = [dict(row._mapping) for row in splits_result]
            
            # Format amounts
            if main_transaction.get('amount'):
                main_transaction['amount'] = float(main_transaction['amount'])
            for split in split_transactions:
                if split.get('amount'):
                    split['amount'] = float(split['amount'])
            
            return jsonify({
                'main_transaction': main_transaction,
                'splits': split_transactions,
                'total_split_amount': sum(split.get('amount', 0) for split in split_transactions)
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/<txn_id>/splits', methods=['POST'])
def save_transaction_splits(txn_id):
    """Save splits for a specific transaction"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        data = request.json
        splits = data.get('splits', [])
        
        with engine.connect() as conn:
            # Delete existing splits
            conn.execute(text("DELETE FROM transactions WHERE parent_id = :txn_id"), {'txn_id': txn_id})
            
            # Insert new splits
            for split in splits:
                split_query = text("""
                    INSERT INTO transactions (
                        id, parent_id, description, amount, db_cr, txn_date, 
                        mark_id, notes, company_id, created_at, updated_at
                    ) VALUES (
                        :id, :parent_id, :description, :amount, :db_cr, :txn_date,
                        :mark_id, :notes, :company_id, NOW(), NOW()
                    )
                """)
                
                # Get parent transaction details
                parent_query = text("SELECT company_id, txn_date, mark_id FROM transactions WHERE id = :txn_id")
                parent_result = conn.execute(parent_query, {'txn_id': txn_id}).fetchone()
                
                if parent_result:
                    parent_data = dict(parent_result._mapping)
                    
                    conn.execute(split_query, {
                        'id': str(uuid.uuid4()),
                        'parent_id': txn_id,
                        'description': split.get('description', ''),
                        'amount': split.get('amount', 0),
                        'db_cr': split.get('db_cr', 'DB'),
                        'txn_date': parent_data.get('txn_date'),
                        'mark_id': split.get('mark_id'),  # BUG FIX: Use split mark_id, not parent mark_id
                        'notes': split.get('notes', ''),
                        'company_id': parent_data.get('company_id')
                    })
            
            conn.commit()
            return jsonify({'message': 'Splits saved successfully', 'splits_count': len(splits)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
