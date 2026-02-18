from flask import Blueprint, request, jsonify
from sqlalchemy import text
from backend.db.session import get_db_engine
import uuid
import datetime
from backend.services.rental_service import create_or_update_prepaid_from_contract

rental_bp = Blueprint('rental_bp', __name__)

@rental_bp.route('/api/rental-locations', methods=['GET'])
def get_locations():
    company_id = request.args.get('company_id')
    engine, _ = get_db_engine()
    
    with engine.connect() as conn:
        query = text("""
            SELECT l.*, c.name as company_name 
            FROM rental_locations l
            JOIN companies c ON l.company_id = c.id
            WHERE (:company_id IS NULL OR l.company_id = :company_id)
            ORDER BY l.location_name
        """)
        result = conn.execute(query, {'company_id': company_id})
        locations = [dict(row._mapping) for row in result]
        
        # Convert date/time objects to strings
        for loc in locations:
            for key, val in loc.items():
                if isinstance(val, (datetime.date, datetime.datetime)):
                    loc[key] = val.isoformat()
                    
    return jsonify({'locations': locations})

@rental_bp.route('/api/rental-locations', methods=['POST'])
def create_location():
    data = request.json
    engine, _ = get_db_engine()
    location_id = str(uuid.uuid4())
    
    with engine.begin() as conn:
        query = text("""
            INSERT INTO rental_locations (
                id, company_id, location_name, address, city, province, 
                postal_code, latitude, longitude, area_sqm, notes
            ) VALUES (
                :id, :company_id, :location_name, :address, :city, :province,
                :postal_code, :latitude, :longitude, :area_sqm, :notes
            )
        """)
        conn.execute(query, {
            'id': location_id,
            'company_id': data['company_id'],
            'location_name': data['location_name'],
            'address': data['address'],
            'city': data.get('city'),
            'province': data.get('province'),
            'postal_code': data.get('postal_code'),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'area_sqm': data.get('area_sqm'),
            'notes': data.get('notes')
        })
        
    return jsonify({'id': location_id, 'message': 'Location created successfully'})

@rental_bp.route('/api/rental-locations/<location_id>', methods=['PUT'])
def update_location(location_id):
    data = request.json
    engine, _ = get_db_engine()
    
    with engine.begin() as conn:
        query = text("""
            UPDATE rental_locations SET 
                location_name = :location_name, 
                address = :address, 
                city = :city, 
                province = :province,
                postal_code = :postal_code, 
                latitude = :latitude, 
                longitude = :longitude, 
                area_sqm = :area_sqm, 
                notes = :notes,
                updated_at = NOW()
            WHERE id = :id
        """)
        conn.execute(query, {
            'id': location_id,
            'location_name': data['location_name'],
            'address': data['address'],
            'city': data.get('city'),
            'province': data.get('province'),
            'postal_code': data.get('postal_code'),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'area_sqm': data.get('area_sqm'),
            'notes': data.get('notes')
        })
        
    return jsonify({'message': 'Location updated successfully'})

@rental_bp.route('/api/rental-locations/<location_id>', methods=['DELETE'])
def delete_location(location_id):
    engine, _ = get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM rental_locations WHERE id = :id"), {'id': location_id})
    return jsonify({'message': 'Location deleted successfully'})

# --- STORES ---
@rental_bp.route('/api/stores', methods=['GET'])
def get_stores():
    company_id = request.args.get('company_id')
    engine, _ = get_db_engine()
    
    with engine.connect() as conn:
        query = text("""
            SELECT s.*, l.location_name 
            FROM rental_stores s
            LEFT JOIN rental_locations l ON s.current_location_id = l.id
            WHERE (:company_id IS NULL OR s.company_id = :company_id)
            ORDER BY s.store_name
        """)
        result = conn.execute(query, {'company_id': company_id})
        stores = [dict(row._mapping) for row in result]
        for s in stores:
            for key, val in s.items():
                if isinstance(val, (datetime.date, datetime.datetime)):
                    s[key] = val.isoformat()
    return jsonify({'stores': stores})

@rental_bp.route('/api/stores', methods=['POST'])
def create_store():
    data = request.json
    engine, _ = get_db_engine()
    store_id = str(uuid.uuid4())
    
    with engine.begin() as conn:
        query = text("""
            INSERT INTO rental_stores (id, company_id, store_code, store_name, current_location_id, status, notes)
            VALUES (:id, :company_id, :store_code, :store_name, :current_location_id, :status, :notes)
        """)
        conn.execute(query, {
            'id': store_id,
            'company_id': data['company_id'],
            'store_code': data['store_code'],
            'store_name': data['store_name'],
            'current_location_id': data.get('current_location_id'),
            'status': data.get('status', 'active'),
            'notes': data.get('notes')
        })
    return jsonify({'id': store_id, 'message': 'Store created successfully'})

# --- CONTRACTS ---
@rental_bp.route('/api/rental-contracts', methods=['GET'])
def get_contracts():
    company_id = request.args.get('company_id')
    status = request.args.get('status')
    engine, _ = get_db_engine()
    
    with engine.connect() as conn:
        query = text("""
            SELECT c.*, s.store_name, l.location_name
            FROM rental_contracts c
            JOIN rental_stores s ON c.store_id = s.id
            JOIN rental_locations l ON c.location_id = l.id
            WHERE (:company_id IS NULL OR c.company_id = :company_id)
            AND (:status IS NULL OR c.status = :status)
            ORDER BY c.start_date DESC
        """)
        result = conn.execute(query, {'company_id': company_id, 'status': status})
        contracts = [dict(row._mapping) for row in result]
        for c in contracts:
            for key, val in c.items():
                if isinstance(val, (datetime.date, datetime.datetime)):
                    c[key] = val.isoformat()
    return jsonify({'contracts': contracts})

@rental_bp.route('/api/rental-contracts', methods=['POST'])
def create_contract():
    data = request.json
    engine, _ = get_db_engine()
    contract_id = str(uuid.uuid4())
    
    with engine.begin() as conn:
        query = text("""
            INSERT INTO rental_contracts (
                id, company_id, store_id, location_id, contract_number, landlord_name,
                start_date, end_date, total_amount, status, notes
            ) VALUES (
                :id, :company_id, :store_id, :location_id, :contract_number, :landlord_name,
                :start_date, :end_date, :total_amount, :status, :notes
            )
        """)
        conn.execute(query, {
            'id': contract_id,
            'company_id': data['company_id'],
            'store_id': data['store_id'],
            'location_id': data['location_id'],
            'contract_number': data.get('contract_number'),
            'landlord_name': data.get('landlord_name'),
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'total_amount': data.get('total_amount'),
            'status': data.get('status', 'active'),
            'notes': data.get('notes')
        })
        
        # Link transactions if provided
        linked_ids = data.get('linked_transaction_ids', [])
        for txn_id in linked_ids:
            conn.execute(text("UPDATE transactions SET rental_contract_id = :contract_id WHERE id = :txn_id"),
                        {'contract_id': contract_id, 'txn_id': txn_id})
            
    # Auto-create/update prepaid expense
    prepaid_info = create_or_update_prepaid_from_contract(contract_id, data['company_id'])
    
    return jsonify({
        'id': contract_id, 
        'message': 'Contract created successfully',
        'prepaid_auto_created': prepaid_info.get('created', False),
        'prepaid_expense_id': prepaid_info.get('prepaid_id'),
        'total_amount': prepaid_info.get('total_amount')
    })

# --- TRANSACTION LINKING ---
@rental_bp.route('/api/rental-contracts/<contract_id>/transactions', methods=['GET'])
def get_contract_transactions(contract_id):
    engine, _ = get_db_engine()
    with engine.connect() as conn:
        query = text("""
            SELECT * FROM transactions 
            WHERE rental_contract_id = :contract_id
            ORDER BY txn_date DESC
        """)
        result = conn.execute(query, {'contract_id': contract_id})
        transactions = [dict(row._mapping) for row in result]
        for t in transactions:
            for key, val in t.items():
                if isinstance(val, (datetime.date, datetime.datetime)):
                    t[key] = val.isoformat()
    return jsonify({'transactions': transactions})

@rental_bp.route('/api/rental-contracts/<contract_id>/link-transaction', methods=['POST'])
def link_transaction(contract_id):
    txn_id = request.json.get('transaction_id')
    engine, _ = get_db_engine()
    
    with engine.begin() as conn:
        conn.execute(text("UPDATE transactions SET rental_contract_id = :contract_id WHERE id = :txn_id"),
                    {'contract_id': contract_id, 'txn_id': txn_id})
        
        # Get company_id from contract
        contract = conn.execute(text("SELECT company_id FROM rental_contracts WHERE id = :id"), {'id': contract_id}).fetchone()
        company_id = contract[0] if contract else None
            
    # Update prepaid expense
    create_or_update_prepaid_from_contract(contract_id, company_id)
    return jsonify({'message': 'Transaction linked successfully', 'prepaid_updated': True})

@rental_bp.route('/api/rental-contracts/linkable-transactions', methods=['GET'])
def get_linkable_transactions():
    company_id = request.args.get('company_id')
    current_contract_id = request.args.get('current_contract_id')
    engine, _ = get_db_engine()
    
    with engine.connect() as conn:
        query = text("""
            SELECT * FROM transactions
            WHERE (company_id = :company_id OR :company_id IS NULL)
            AND (rental_contract_id IS NULL OR rental_contract_id = :current_id)
            AND (LOWER(description) LIKE '%%sewa%%' OR LOWER(description) LIKE '%%rent%%' OR LOWER(description) LIKE '%%kontrak%%')
            ORDER BY txn_date DESC
        """)
        result = conn.execute(query, {'company_id': company_id, 'current_id': current_contract_id})
        transactions = [dict(row._mapping) for row in result]
        for t in transactions:
            for key, val in t.items():
                if isinstance(val, (datetime.date, datetime.datetime)):
                    t[key] = val.isoformat()
    return jsonify({'transactions': transactions})
