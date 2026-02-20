import uuid
import datetime
import json
from decimal import Decimal
from flask import Blueprint, request, jsonify
from sqlalchemy import text, bindparam

from backend.db.session import get_db_engine
from backend.services.rental_service import (
    create_or_update_prepaid_from_contract,
    generate_contract_journal_preview
)

rental_bp = Blueprint('rental_bp', __name__)
RENT_CFG_PREFIX = '[RENT_CFG]'


def _serialize_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


def _serialize_row(row):
    data = dict(row._mapping)
    return {k: _serialize_value(v) for k, v in data.items()}


def _table_columns(conn, table_name):
    if conn.dialect.name == 'sqlite':
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return {str(row[1]) for row in rows}

    rows = conn.execute(text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
    """), {'table_name': table_name}).fetchall()
    return {str(row[0]) for row in rows}


def _normalize_ids(values):
    if not isinstance(values, list):
        return []
    return [str(v).strip() for v in values if str(v).strip()]


def _split_notes_and_cfg(notes_value):
    text_value = str(notes_value or '')
    if RENT_CFG_PREFIX not in text_value:
        return text_value.strip(), {}

    base, _, tail = text_value.partition(RENT_CFG_PREFIX)
    cfg = {}
    try:
        cfg = json.loads(tail.strip())
        if not isinstance(cfg, dict):
            cfg = {}
    except Exception:
        cfg = {}
    return base.strip(), cfg


def _merge_notes_with_cfg(base_notes, cfg):
    cleaned_notes, _ = _split_notes_and_cfg(base_notes)
    normalized_cfg = {
        'calculation_method': str(cfg.get('calculation_method') or 'BRUTO').upper(),
        'pph42_rate': float(cfg.get('pph42_rate') or 10),
        'pph42_payment_timing': str(cfg.get('pph42_payment_timing') or 'same_period'),
        'pph42_payment_date': cfg.get('pph42_payment_date')
    }
    cfg_blob = f"{RENT_CFG_PREFIX}{json.dumps(normalized_cfg, separators=(',', ':'))}"
    return f"{cleaned_notes}\n{cfg_blob}".strip() if cleaned_notes else cfg_blob


def _filter_rent_transaction_ids(conn, transaction_ids, company_id):
    if not transaction_ids:
        return []

    query = text("""
        SELECT DISTINCT t.id
        FROM transactions t
        LEFT JOIN marks m ON t.mark_id = m.id
        WHERE t.id IN :txn_ids
          AND (
            :company_id IS NULL
            OR t.company_id = :company_id
            OR t.company_id IS NULL
          )
          AND (
            LOWER(COALESCE(m.personal_use, '')) LIKE '%%sewa tempat%%'
            OR LOWER(COALESCE(m.internal_report, '')) LIKE '%%sewa tempat%%'
            OR LOWER(COALESCE(m.tax_report, '')) LIKE '%%sewa tempat%%'
            OR LOWER(COALESCE(m.personal_use, '')) LIKE '%%sewa%%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%%sewa%%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%%rent%%'
            OR EXISTS (
              SELECT 1
              FROM mark_coa_mapping mcm
              INNER JOIN chart_of_accounts coa ON coa.id = mcm.coa_id
              WHERE mcm.mark_id = t.mark_id
                AND coa.code IN ('5315', '5105')
            )
          )
    """).bindparams(bindparam('txn_ids', expanding=True))

    result = conn.execute(query, {
        'txn_ids': transaction_ids,
        'company_id': company_id
    })
    return [str(row.id) for row in result]


@rental_bp.route('/api/rental-locations', methods=['GET'])
def get_locations():
    company_id = request.args.get('company_id')
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT l.*, c.name AS company_name
                FROM rental_locations l
                LEFT JOIN companies c ON l.company_id = c.id
                WHERE (:company_id IS NULL OR l.company_id = :company_id)
                ORDER BY l.location_name
            """), {'company_id': company_id})
            locations = [_serialize_row(row) for row in result]
        return jsonify({'locations': locations})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-locations', methods=['POST'])
def create_location():
    data = request.json or {}
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    if not data.get('company_id') or not data.get('location_name'):
        return jsonify({'error': 'company_id and location_name are required'}), 400

    location_id = str(uuid.uuid4())
    now = datetime.datetime.now()

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO rental_locations (
                    id, company_id, location_name, address, city, province,
                    postal_code, latitude, longitude, area_sqm, notes, created_at, updated_at
                ) VALUES (
                    :id, :company_id, :location_name, :address, :city, :province,
                    :postal_code, :latitude, :longitude, :area_sqm, :notes, :created_at, :updated_at
                )
            """), {
                'id': location_id,
                'company_id': data['company_id'],
                'location_name': data['location_name'],
                'address': data.get('address'),
                'city': data.get('city'),
                'province': data.get('province'),
                'postal_code': data.get('postal_code'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'area_sqm': data.get('area_sqm'),
                'notes': data.get('notes'),
                'created_at': now,
                'updated_at': now
            })
        return jsonify({'id': location_id, 'message': 'Location created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-locations/<location_id>', methods=['PUT'])
def update_location(location_id):
    data = request.json or {}
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    now = datetime.datetime.now()
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE rental_locations
                SET location_name = :location_name,
                    address = :address,
                    city = :city,
                    province = :province,
                    postal_code = :postal_code,
                    latitude = :latitude,
                    longitude = :longitude,
                    area_sqm = :area_sqm,
                    notes = :notes,
                    updated_at = :updated_at
                WHERE id = :id
            """), {
                'id': location_id,
                'location_name': data.get('location_name'),
                'address': data.get('address'),
                'city': data.get('city'),
                'province': data.get('province'),
                'postal_code': data.get('postal_code'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'area_sqm': data.get('area_sqm'),
                'notes': data.get('notes'),
                'updated_at': now
            })
        return jsonify({'message': 'Location updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-locations/<location_id>', methods=['DELETE'])
def delete_location(location_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM rental_locations WHERE id = :id"), {'id': location_id})
        return jsonify({'message': 'Location deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/stores', methods=['GET'])
def get_stores():
    company_id = request.args.get('company_id')
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.connect() as conn:
            store_columns = _table_columns(conn, 'rental_stores')
            store_name_expr = 's.store_name' if 'store_name' in store_columns else 's.name'
            store_code_expr = 's.store_code' if 'store_code' in store_columns else 'NULL'
            location_join = 'LEFT JOIN rental_locations l ON s.current_location_id = l.id' if 'current_location_id' in store_columns else 'LEFT JOIN rental_locations l ON 1 = 0'
            result = conn.execute(text("""
                SELECT
                    s.*,
                    """ + store_name_expr + """ AS store_name,
                    """ + store_code_expr + """ AS store_code,
                    l.location_name
                FROM rental_stores s
                """ + location_join + """
                WHERE (:company_id IS NULL OR s.company_id = :company_id)
                ORDER BY """ + store_name_expr + """ ASC
            """), {'company_id': company_id})
            stores = [_serialize_row(row) for row in result]
        return jsonify({'stores': stores})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/stores', methods=['POST'])
def create_store():
    data = request.json or {}
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    if not data.get('company_id') or not data.get('store_name'):
        return jsonify({'error': 'company_id and store_name are required'}), 400

    store_id = str(uuid.uuid4())
    now = datetime.datetime.now()

    try:
        with engine.begin() as conn:
            store_columns = _table_columns(conn, 'rental_stores')
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/stores/<store_id>', methods=['PUT'])
def update_store(store_id):
    data = request.json or {}
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    now = datetime.datetime.now()
    try:
        with engine.begin() as conn:
            store_columns = _table_columns(conn, 'rental_stores')
            payload = {
                'id': store_id,
                'store_code': data.get('store_code'),
                'store_name': data.get('store_name'),
                'name': data.get('store_name'),
                'current_location_id': data.get('current_location_id'),
                'status': data.get('status'),
                'notes': data.get('notes'),
                'updated_at': now
            }
            update_columns = [column for column in payload.keys() if column in store_columns and column != 'id']
            if update_columns:
                set_clause = ', '.join(f"{column} = :{column}" for column in update_columns)
                conn.execute(text(f"""
                    UPDATE rental_stores
                    SET {set_clause}
                    WHERE id = :id
                """), payload)
        return jsonify({'message': 'Store updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/stores/<store_id>', methods=['DELETE'])
def delete_store(store_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM rental_stores WHERE id = :id"), {'id': store_id})
        return jsonify({'message': 'Store deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-contracts', methods=['GET'])
def get_contracts():
    company_id = request.args.get('company_id')
    status = request.args.get('status')
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.connect() as conn:
            contract_columns = _table_columns(conn, 'rental_contracts')
            store_columns = _table_columns(conn, 'rental_stores')

            calculation_method_sql = "COALESCE(c.calculation_method, 'BRUTO')" if 'calculation_method' in contract_columns else "'BRUTO'"
            pph42_rate_sql = "COALESCE(c.pph42_rate, 10)" if 'pph42_rate' in contract_columns else "10"
            pph42_timing_sql = "COALESCE(c.pph42_payment_timing, 'same_period')" if 'pph42_payment_timing' in contract_columns else "'same_period'"
            pph42_date_sql = "c.pph42_payment_date" if 'pph42_payment_date' in contract_columns else "NULL"
            store_name_sql = "s.store_name" if 'store_name' in store_columns else "s.name"
            store_code_sql = "s.store_code" if 'store_code' in store_columns else "NULL"

            query = text(f"""
                SELECT
                    c.*,
                    {store_name_sql} AS store_name,
                    {store_code_sql} AS store_code,
                    l.location_name,
                    l.address AS location_address,
                    COALESCE(txn.txn_count, 0) AS transaction_count,
                    COALESCE(txn.total_paid, 0) AS total_paid,
                    {calculation_method_sql} AS calculation_method,
                    {pph42_rate_sql} AS pph42_rate,
                    {pph42_timing_sql} AS pph42_payment_timing,
                    {pph42_date_sql} AS pph42_payment_date
                FROM rental_contracts c
                LEFT JOIN rental_stores s ON c.store_id = s.id
                LEFT JOIN rental_locations l ON c.location_id = l.id
                LEFT JOIN (
                    SELECT
                        rental_contract_id,
                        COUNT(*) AS txn_count,
                        COALESCE(SUM(ABS(amount)), 0) AS total_paid
                    FROM transactions
                    WHERE rental_contract_id IS NOT NULL
                    GROUP BY rental_contract_id
                ) txn ON txn.rental_contract_id = c.id
                WHERE (:company_id IS NULL OR c.company_id = :company_id)
                  AND (:status IS NULL OR c.status = :status)
                ORDER BY c.start_date DESC, c.created_at DESC
            """)

            result = conn.execute(query, {'company_id': company_id, 'status': status})
            contracts = [_serialize_row(row) for row in result]
            has_method_col = 'calculation_method' in contract_columns
            has_rate_col = 'pph42_rate' in contract_columns
            has_timing_col = 'pph42_payment_timing' in contract_columns
            has_date_col = 'pph42_payment_date' in contract_columns

            for contract in contracts:
                clean_notes, cfg = _split_notes_and_cfg(contract.get('notes'))
                contract['notes'] = clean_notes

                if cfg:
                    if (not has_method_col) or not contract.get('calculation_method'):
                        contract['calculation_method'] = str(cfg.get('calculation_method') or 'BRUTO').upper()
                    if (not has_rate_col) or contract.get('pph42_rate') is None:
                        contract['pph42_rate'] = float(cfg.get('pph42_rate') or 10)
                    if (not has_timing_col) or not contract.get('pph42_payment_timing'):
                        contract['pph42_payment_timing'] = cfg.get('pph42_payment_timing') or 'same_period'
                    if (not has_date_col) or not contract.get('pph42_payment_date'):
                        contract['pph42_payment_date'] = cfg.get('pph42_payment_date')
        return jsonify({'contracts': contracts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-contracts/expiring', methods=['GET'])
def get_expiring_contracts():
    company_id = request.args.get('company_id')
    days = int(request.args.get('days') or 30)
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.connect() as conn:
            store_columns = _table_columns(conn, 'rental_stores')
            store_name_sql = "s.store_name" if 'store_name' in store_columns else "s.name"
            if conn.dialect.name == 'sqlite':
                query = text(f"""
                    SELECT c.*, {store_name_sql} AS store_name, l.location_name
                    FROM rental_contracts c
                    LEFT JOIN rental_stores s ON c.store_id = s.id
                    LEFT JOIN rental_locations l ON c.location_id = l.id
                    WHERE (:company_id IS NULL OR c.company_id = :company_id)
                      AND c.status = 'active'
                      AND date(c.end_date) <= date('now', :window)
                    ORDER BY c.end_date ASC
                """)
                params = {'company_id': company_id, 'window': f'+{days} day'}
            else:
                query = text(f"""
                    SELECT c.*, {store_name_sql} AS store_name, l.location_name
                    FROM rental_contracts c
                    LEFT JOIN rental_stores s ON c.store_id = s.id
                    LEFT JOIN rental_locations l ON c.location_id = l.id
                    WHERE (:company_id IS NULL OR c.company_id = :company_id)
                      AND c.status = 'active'
                      AND c.end_date <= DATE_ADD(CURDATE(), INTERVAL :days DAY)
                    ORDER BY c.end_date ASC
                """)
                params = {'company_id': company_id, 'days': days}

            result = conn.execute(query, params)
            contracts = [_serialize_row(row) for row in result]
        return jsonify({'contracts': contracts, 'days': days})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-contracts', methods=['POST'])
def create_contract():
    data = request.json or {}
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    required = ['company_id', 'store_id', 'location_id', 'start_date', 'end_date']
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400

    contract_id = str(uuid.uuid4())
    now = datetime.datetime.now()
    linked_ids = _normalize_ids(data.get('linked_transaction_ids', []))

    try:
        with engine.begin() as conn:
            contract_columns = _table_columns(conn, 'rental_contracts')
            allowed_txn_ids = _filter_rent_transaction_ids(conn, linked_ids, data.get('company_id'))
            rejected_txn_ids = [txn_id for txn_id in linked_ids if txn_id not in set(allowed_txn_ids)]

            insert_payload = {
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
                'notes': data.get('notes'),
                'calculation_method': data.get('calculation_method'),
                'pph42_rate': data.get('pph42_rate'),
                'pph42_payment_timing': data.get('pph42_payment_timing'),
                'pph42_payment_date': data.get('pph42_payment_date'),
                'created_at': now,
                'updated_at': now
            }

            cfg_payload = {
                'calculation_method': data.get('calculation_method'),
                'pph42_rate': data.get('pph42_rate'),
                'pph42_payment_timing': data.get('pph42_payment_timing'),
                'pph42_payment_date': data.get('pph42_payment_date')
            }
            if 'notes' in contract_columns and (
                'calculation_method' not in contract_columns
                or 'pph42_rate' not in contract_columns
                or 'pph42_payment_timing' not in contract_columns
                or 'pph42_payment_date' not in contract_columns
            ):
                insert_payload['notes'] = _merge_notes_with_cfg(insert_payload.get('notes'), cfg_payload)

            insert_columns = [column for column in insert_payload.keys() if column in contract_columns]
            if not insert_columns:
                return jsonify({'error': 'rental_contracts table has no compatible columns for insert'}), 500
            columns_sql = ', '.join(insert_columns)
            values_sql = ', '.join(f":{column}" for column in insert_columns)

            conn.execute(text(f"""
                INSERT INTO rental_contracts ({columns_sql})
                VALUES ({values_sql})
            """), insert_payload)

            if allowed_txn_ids:
                update_query = text("""
                    UPDATE transactions
                    SET rental_contract_id = :contract_id
                    WHERE id IN :txn_ids
                """).bindparams(bindparam('txn_ids', expanding=True))
                conn.execute(update_query, {
                    'contract_id': contract_id,
                    'txn_ids': allowed_txn_ids
                })

        accounting_payload = {
            'calculation_method': data.get('calculation_method'),
            'pph42_rate': data.get('pph42_rate'),
            'pph42_payment_timing': data.get('pph42_payment_timing'),
            'pph42_payment_date': data.get('pph42_payment_date')
        }
        prepaid_info = create_or_update_prepaid_from_contract(contract_id, data['company_id'], accounting_payload)

        return jsonify({
            'id': contract_id,
            'message': 'Contract created successfully',
            'linked_transactions_count': len(allowed_txn_ids),
            'rejected_transaction_ids': rejected_txn_ids,
            'prepaid_auto_created': bool(prepaid_info.get('created')),
            'prepaid_auto_updated': bool(prepaid_info.get('updated')),
            'prepaid_expense_id': prepaid_info.get('prepaid_id'),
            'prepaid_error': prepaid_info.get('error'),
            'total_amount': prepaid_info.get('amount_bruto') or prepaid_info.get('total_amount') or data.get('total_amount'),
            'amount_net': prepaid_info.get('amount_net'),
            'amount_tax': prepaid_info.get('amount_tax'),
            'tax_rate': prepaid_info.get('tax_rate'),
            'calculation_method': prepaid_info.get('calculation_method'),
            'pph42_payment_timing': prepaid_info.get('pph42_payment_timing'),
            'journal_preview': prepaid_info.get('journals', [])
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-contracts/<contract_id>', methods=['PUT'])
def update_contract(contract_id):
    data = request.json or {}
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    linked_ids = _normalize_ids(data.get('linked_transaction_ids', []))
    now = datetime.datetime.now()

    try:
        with engine.begin() as conn:
            contract_columns = _table_columns(conn, 'rental_contracts')
            current = conn.execute(text("""
                SELECT id, company_id
                FROM rental_contracts
                WHERE id = :id
                LIMIT 1
            """), {'id': contract_id}).fetchone()
            if not current:
                return jsonify({'error': 'Contract not found'}), 404

            company_id = data.get('company_id') or current.company_id
            allowed_txn_ids = _filter_rent_transaction_ids(conn, linked_ids, company_id)

            update_payload = {
                'id': contract_id,
                'company_id': company_id,
                'store_id': data.get('store_id'),
                'location_id': data.get('location_id'),
                'contract_number': data.get('contract_number'),
                'landlord_name': data.get('landlord_name'),
                'start_date': data.get('start_date'),
                'end_date': data.get('end_date'),
                'total_amount': data.get('total_amount'),
                'status': data.get('status'),
                'notes': data.get('notes'),
                'calculation_method': data.get('calculation_method'),
                'pph42_rate': data.get('pph42_rate'),
                'pph42_payment_timing': data.get('pph42_payment_timing'),
                'pph42_payment_date': data.get('pph42_payment_date'),
                'updated_at': now
            }

            cfg_payload = {
                'calculation_method': data.get('calculation_method'),
                'pph42_rate': data.get('pph42_rate'),
                'pph42_payment_timing': data.get('pph42_payment_timing'),
                'pph42_payment_date': data.get('pph42_payment_date')
            }
            if 'notes' in contract_columns and (
                'calculation_method' not in contract_columns
                or 'pph42_rate' not in contract_columns
                or 'pph42_payment_timing' not in contract_columns
                or 'pph42_payment_date' not in contract_columns
            ):
                update_payload['notes'] = _merge_notes_with_cfg(update_payload.get('notes'), cfg_payload)

            updatable_columns = [column for column in update_payload.keys() if column in contract_columns and column != 'id']
            if updatable_columns:
                set_clause = ', '.join(f"{column} = :{column}" for column in updatable_columns)
                conn.execute(text(f"""
                    UPDATE rental_contracts
                    SET {set_clause}
                    WHERE id = :id
                """), update_payload)

            conn.execute(text("""
                UPDATE transactions
                SET rental_contract_id = NULL
                WHERE rental_contract_id = :contract_id
            """), {'contract_id': contract_id})

            if allowed_txn_ids:
                relink_query = text("""
                    UPDATE transactions
                    SET rental_contract_id = :contract_id
                    WHERE id IN :txn_ids
                """).bindparams(bindparam('txn_ids', expanding=True))
                conn.execute(relink_query, {
                    'contract_id': contract_id,
                    'txn_ids': allowed_txn_ids
                })

        accounting_payload = {
            'calculation_method': data.get('calculation_method'),
            'pph42_rate': data.get('pph42_rate'),
            'pph42_payment_timing': data.get('pph42_payment_timing'),
            'pph42_payment_date': data.get('pph42_payment_date')
        }
        prepaid_info = create_or_update_prepaid_from_contract(contract_id, company_id, accounting_payload)

        return jsonify({
            'message': 'Contract updated successfully',
            'linked_transactions_count': len(allowed_txn_ids),
            'prepaid_auto_updated': bool(prepaid_info.get('updated') or prepaid_info.get('created')),
            'prepaid_expense_id': prepaid_info.get('prepaid_id'),
            'prepaid_error': prepaid_info.get('error'),
            'journal_preview': prepaid_info.get('journals', [])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-contracts/<contract_id>', methods=['DELETE'])
def delete_contract(contract_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.begin() as conn:
            contract = conn.execute(text("""
                SELECT id
                FROM rental_contracts
                WHERE id = :id
                LIMIT 1
            """), {'id': contract_id}).fetchone()
            if not contract:
                return jsonify({'error': 'Contract not found'}), 404

            conn.execute(text("""
                UPDATE transactions
                SET rental_contract_id = NULL
                WHERE rental_contract_id = :contract_id
            """), {'contract_id': contract_id})

            conn.execute(text("DELETE FROM rental_contracts WHERE id = :id"), {'id': contract_id})

        return jsonify({'message': 'Contract deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-contracts/<contract_id>/transactions', methods=['GET'])
def get_contract_transactions(contract_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    t.*,
                    m.personal_use,
                    m.internal_report,
                    m.tax_report
                FROM transactions t
                LEFT JOIN marks m ON t.mark_id = m.id
                WHERE t.rental_contract_id = :contract_id
                ORDER BY t.txn_date DESC, t.created_at DESC
            """), {'contract_id': contract_id})
            transactions = [_serialize_row(row) for row in result]
        return jsonify({'transactions': transactions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-contracts/<contract_id>/link-transaction', methods=['POST'])
def link_transaction(contract_id):
    txn_id = (request.json or {}).get('transaction_id')
    if not txn_id:
        return jsonify({'error': 'transaction_id is required'}), 400

    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.begin() as conn:
            contract = conn.execute(text("""
                SELECT company_id
                FROM rental_contracts
                WHERE id = :id
                LIMIT 1
            """), {'id': contract_id}).fetchone()
            if not contract:
                return jsonify({'error': 'Contract not found'}), 404

            allowed_ids = _filter_rent_transaction_ids(conn, [txn_id], contract.company_id)
            if not allowed_ids:
                return jsonify({'error': 'Transaction is not eligible (must be marked as sewa tempat)'}), 400

            conn.execute(text("""
                UPDATE transactions
                SET rental_contract_id = :contract_id
                WHERE id = :txn_id
            """), {
                'contract_id': contract_id,
                'txn_id': txn_id
            })

        prepaid_info = create_or_update_prepaid_from_contract(contract_id, contract.company_id)
        return jsonify({
            'message': 'Transaction linked successfully',
            'prepaid_updated': bool(prepaid_info.get('updated') or prepaid_info.get('created'))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-contracts/<contract_id>/unlink-transaction/<transaction_id>', methods=['DELETE'])
def unlink_transaction(contract_id, transaction_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.begin() as conn:
            contract = conn.execute(text("""
                SELECT company_id
                FROM rental_contracts
                WHERE id = :id
                LIMIT 1
            """), {'id': contract_id}).fetchone()
            if not contract:
                return jsonify({'error': 'Contract not found'}), 404

            conn.execute(text("""
                UPDATE transactions
                SET rental_contract_id = NULL
                WHERE id = :transaction_id
                  AND rental_contract_id = :contract_id
            """), {
                'transaction_id': transaction_id,
                'contract_id': contract_id
            })

        prepaid_info = create_or_update_prepaid_from_contract(contract_id, contract.company_id)
        return jsonify({
            'message': 'Transaction unlinked successfully',
            'prepaid_updated': bool(prepaid_info.get('updated') or prepaid_info.get('created'))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-contracts/linkable-transactions', methods=['GET'])
def get_linkable_transactions():
    company_id = request.args.get('company_id')
    current_contract_id = request.args.get('current_contract_id')
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT
                    t.*,
                    m.personal_use,
                    m.internal_report,
                    m.tax_report
                FROM transactions t
                LEFT JOIN marks m ON t.mark_id = m.id
                WHERE (
                      :company_id IS NULL
                      OR t.company_id = :company_id
                      OR (t.rental_contract_id = :current_contract_id)
                  )
                  AND (t.rental_contract_id IS NULL OR t.rental_contract_id = :current_contract_id)
                  AND (
                      t.rental_contract_id = :current_contract_id
                      OR
                      LOWER(COALESCE(m.personal_use, '')) LIKE '%%sewa tempat%%'
                      OR LOWER(COALESCE(m.internal_report, '')) LIKE '%%sewa tempat%%'
                      OR LOWER(COALESCE(m.tax_report, '')) LIKE '%%sewa tempat%%'
                      OR LOWER(COALESCE(m.personal_use, '')) LIKE '%%sewa%%'
                      OR LOWER(COALESCE(t.description, '')) LIKE '%%sewa%%'
                      OR LOWER(COALESCE(t.description, '')) LIKE '%%rent%%'
                      OR EXISTS (
                          SELECT 1
                          FROM mark_coa_mapping mcm
                          INNER JOIN chart_of_accounts coa ON coa.id = mcm.coa_id
                          WHERE mcm.mark_id = t.mark_id
                            AND coa.code IN ('5315', '5105')
                      )
                  )
                ORDER BY t.txn_date DESC, t.created_at DESC
            """)
            result = conn.execute(query, {
                'company_id': company_id,
                'current_contract_id': current_contract_id
            })
            transactions = [_serialize_row(row) for row in result]

        return jsonify({'transactions': transactions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rental_bp.route('/api/rental-contracts/<contract_id>/generate-journals', methods=['POST'])
def generate_journals(contract_id):
    payload = request.json or {}
    company_id = payload.get('company_id') or request.args.get('company_id')

    preview = generate_contract_journal_preview(contract_id, company_id, payload)
    if preview.get('error'):
        return jsonify({'error': preview['error']}), 400

    return jsonify({
        'journals': preview.get('journals', []),
        'amortization_schedule': preview.get('amortization_schedule', []),
        'monthly_amount': preview.get('monthly_amortization', 0),
        'amount_bruto': preview.get('amount_bruto', 0),
        'amount_net': preview.get('amount_net', 0),
        'amount_tax': preview.get('amount_tax', 0),
        'tax_rate': preview.get('tax_rate', 0),
        'calculation_method': preview.get('calculation_method', 'BRUTO'),
        'pph42_payment_timing': preview.get('pph42_payment_timing', 'same_period')
    })
