import datetime
import uuid

from flask import Blueprint, jsonify, request
from sqlalchemy import bindparam, text

from backend.db.schema import get_table_columns
from backend.errors import BadRequestError, NotFoundError
from backend.routes.accounting_utils import require_db_engine, serialize_result_rows
from backend.routes.rental_helpers import (
    merge_notes_with_cfg,
    normalize_ids,
    split_notes_and_cfg,
)
from backend.routes.rental_queries import (
    build_contract_transactions_query,
    build_contracts_query,
    build_expiring_contracts_query_default,
    build_expiring_contracts_query_sqlite,
    build_filter_rent_transaction_ids_query,
    build_linkable_transactions_query,
)
from backend.services.rental_service import (
    create_or_update_prepaid_from_contract,
    generate_contract_journal_preview,
)

rental_contract_bp = Blueprint('rental_contract_bp', __name__)


def _filter_rent_transaction_ids(conn, transaction_ids, company_id):
    if not transaction_ids:
        return []

    result = conn.execute(build_filter_rent_transaction_ids_query(), {
        'txn_ids': transaction_ids,
        'company_id': company_id
    })
    return [str(row.id) for row in result]


@rental_contract_bp.route('/api/rental-contracts', methods=['GET'])
def get_contracts():
    company_id = request.args.get('company_id')
    status = request.args.get('status')
    engine = require_db_engine()

    with engine.connect() as conn:
        contract_columns = get_table_columns(conn, 'rental_contracts')
        store_columns = get_table_columns(conn, 'rental_stores')

        calculation_method_sql = "COALESCE(c.calculation_method, 'BRUTO')" if 'calculation_method' in contract_columns else "'BRUTO'"
        pph42_rate_sql = "COALESCE(c.pph42_rate, 10)" if 'pph42_rate' in contract_columns else "10"
        pph42_timing_sql = "COALESCE(c.pph42_payment_timing, 'same_period')" if 'pph42_payment_timing' in contract_columns else "'same_period'"
        pph42_date_sql = "c.pph42_payment_date" if 'pph42_payment_date' in contract_columns else "NULL"
        pph42_ref_sql = "c.pph42_payment_ref" if 'pph42_payment_ref' in contract_columns else "NULL"
        store_name_sql = "s.store_name" if 'store_name' in store_columns else "s.name"
        store_code_sql = "s.store_code" if 'store_code' in store_columns else "NULL"

        result = conn.execute(
            build_contracts_query(
                calculation_method_sql,
                pph42_rate_sql,
                pph42_timing_sql,
                pph42_date_sql,
                pph42_ref_sql,
                store_name_sql,
                store_code_sql,
            ),
            {'company_id': company_id, 'status': status}
        )
        contracts = serialize_result_rows(result, datetime_format='%Y-%m-%dT%H:%M:%S')
        has_method_col = 'calculation_method' in contract_columns
        has_rate_col = 'pph42_rate' in contract_columns
        has_timing_col = 'pph42_payment_timing' in contract_columns
        has_date_col = 'pph42_payment_date' in contract_columns

        for contract in contracts:
            clean_notes, cfg = split_notes_and_cfg(contract.get('notes'))
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


@rental_contract_bp.route('/api/rental-contracts/expiring', methods=['GET'])
def get_expiring_contracts():
    company_id = request.args.get('company_id')
    days = int(request.args.get('days') or 30)
    engine = require_db_engine()
    with engine.connect() as conn:
        store_columns = get_table_columns(conn, 'rental_stores')
        store_name_sql = "s.store_name" if 'store_name' in store_columns else "s.name"
        if conn.dialect.name == 'sqlite':
            query = build_expiring_contracts_query_sqlite(store_name_sql)
            params = {'company_id': company_id, 'window': f'+{days} day'}
        else:
            query = build_expiring_contracts_query_default(store_name_sql)
            params = {'company_id': company_id, 'days': days}

        result = conn.execute(query, params)
        contracts = serialize_result_rows(result, datetime_format='%Y-%m-%dT%H:%M:%S')
    return jsonify({'contracts': contracts, 'days': days})


@rental_contract_bp.route('/api/rental-contracts', methods=['POST'])
def create_contract():
    data = request.json or {}
    engine = require_db_engine()

    required = ['company_id', 'store_id', 'location_id', 'start_date', 'end_date']
    missing = [field for field in required if not data.get(field)]
    if missing:
        raise BadRequestError(f"Missing required fields: {', '.join(missing)}")

    contract_id = str(uuid.uuid4())
    now = datetime.datetime.now()
    linked_ids = normalize_ids(data.get('linked_transaction_ids', []))

    with engine.begin() as conn:
        contract_columns = get_table_columns(conn, 'rental_contracts')
        allowed_txn_ids = _filter_rent_transaction_ids(conn, linked_ids, data.get('company_id'))
        rejected_txn_ids = [txn_id for txn_id in linked_ids if txn_id not in set(allowed_txn_ids)]

        insert_payload = {
            'id': contract_id,
            'company_id': data['company_id'],
            'store_id': data['store_id'],
            'location_id': data.get('location_id'),
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
            'pph42_payment_ref': data.get('pph42_payment_ref'),
            'created_at': now,
            'updated_at': now
        }

        cfg_payload = {
            'calculation_method': data.get('calculation_method'),
            'pph42_rate': data.get('pph42_rate'),
            'pph42_payment_timing': data.get('pph42_payment_timing'),
            'pph42_payment_date': data.get('pph42_payment_date'),
            'pph42_payment_ref': data.get('pph42_payment_ref')
        }
        if 'notes' in contract_columns and (
            'calculation_method' not in contract_columns
            or 'pph42_rate' not in contract_columns
            or 'pph42_payment_timing' not in contract_columns
            or 'pph42_payment_date' not in contract_columns
        ):
            insert_payload['notes'] = merge_notes_with_cfg(insert_payload.get('notes'), cfg_payload)

        insert_columns = [column for column in insert_payload.keys() if column in contract_columns]
        if not insert_columns:
            raise BadRequestError('rental_contracts table has no compatible columns for insert')
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


@rental_contract_bp.route('/api/rental-contracts/<contract_id>', methods=['PUT'])
def update_contract(contract_id):
    data = request.json or {}
    engine = require_db_engine()
    linked_ids = normalize_ids(data.get('linked_transaction_ids', []))
    now = datetime.datetime.now()

    with engine.begin() as conn:
        contract_columns = get_table_columns(conn, 'rental_contracts')
        current = conn.execute(text("""
            SELECT id, company_id
            FROM rental_contracts
            WHERE id = :id
            LIMIT 1
        """), {'id': contract_id}).fetchone()
        if not current:
            raise NotFoundError('Contract not found')

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
            'pph42_payment_ref': data.get('pph42_payment_ref'),
            'updated_at': now
        }

        cfg_payload = {
            'calculation_method': data.get('calculation_method'),
            'pph42_rate': data.get('pph42_rate'),
            'pph42_payment_timing': data.get('pph42_payment_timing'),
            'pph42_payment_date': data.get('pph42_payment_date'),
            'pph42_payment_ref': data.get('pph42_payment_ref')
        }
        if 'notes' in contract_columns and (
            'calculation_method' not in contract_columns
            or 'pph42_rate' not in contract_columns
            or 'pph42_payment_timing' not in contract_columns
            or 'pph42_payment_date' not in contract_columns
        ):
            update_payload['notes'] = merge_notes_with_cfg(update_payload.get('notes'), cfg_payload)

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


@rental_contract_bp.route('/api/rental-contracts/<contract_id>', methods=['DELETE'])
def delete_contract(contract_id):
    engine = require_db_engine()
    with engine.begin() as conn:
        contract = conn.execute(text("""
            SELECT id
            FROM rental_contracts
            WHERE id = :id
            LIMIT 1
        """), {'id': contract_id}).fetchone()
        if not contract:
            raise NotFoundError('Contract not found')

        conn.execute(text("""
            UPDATE transactions
            SET rental_contract_id = NULL
            WHERE rental_contract_id = :contract_id
        """), {'contract_id': contract_id})

        conn.execute(text("DELETE FROM rental_contracts WHERE id = :id"), {'id': contract_id})
    return jsonify({'message': 'Contract deleted successfully'})


@rental_contract_bp.route('/api/rental-contracts/<contract_id>/transactions', methods=['GET'])
def get_contract_transactions(contract_id):
    engine = require_db_engine()
    with engine.connect() as conn:
        result = conn.execute(build_contract_transactions_query(), {'contract_id': contract_id})
        transactions = serialize_result_rows(result, datetime_format='%Y-%m-%dT%H:%M:%S')
    return jsonify({'transactions': transactions})


@rental_contract_bp.route('/api/rental-contracts/<contract_id>/link-transaction', methods=['POST'])
def link_transaction(contract_id):
    txn_id = (request.json or {}).get('transaction_id')
    if not txn_id:
        raise BadRequestError('transaction_id is required')

    engine = require_db_engine()
    with engine.begin() as conn:
        contract = conn.execute(text("""
            SELECT company_id
            FROM rental_contracts
            WHERE id = :id
            LIMIT 1
        """), {'id': contract_id}).fetchone()
        if not contract:
            raise NotFoundError('Contract not found')

        allowed_ids = _filter_rent_transaction_ids(conn, [txn_id], contract.company_id)
        if not allowed_ids:
            raise BadRequestError('Transaction is not eligible (must be marked as sewa tempat)')

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


@rental_contract_bp.route('/api/rental-contracts/<contract_id>/unlink-transaction/<transaction_id>', methods=['DELETE'])
def unlink_transaction(contract_id, transaction_id):
    engine = require_db_engine()
    with engine.begin() as conn:
        contract = conn.execute(text("""
            SELECT company_id
            FROM rental_contracts
            WHERE id = :id
            LIMIT 1
        """), {'id': contract_id}).fetchone()
        if not contract:
            raise NotFoundError('Contract not found')

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


@rental_contract_bp.route('/api/rental-contracts/linkable-transactions', methods=['GET'])
def get_linkable_transactions():
    company_id = request.args.get('company_id')
    current_contract_id = request.args.get('current_contract_id')
    engine = require_db_engine()
    with engine.connect() as conn:
        result = conn.execute(build_linkable_transactions_query(), {
            'company_id': company_id,
            'current_contract_id': current_contract_id
        })
        transactions = serialize_result_rows(result, datetime_format='%Y-%m-%dT%H:%M:%S')

    return jsonify({'transactions': transactions})


@rental_contract_bp.route('/api/rental-contracts/<contract_id>/generate-journals', methods=['POST'])
def generate_journals(contract_id):
    payload = request.json or {}
    company_id = payload.get('company_id') or request.args.get('company_id')

    preview = generate_contract_journal_preview(contract_id, company_id, payload)
    if preview.get('error'):
        raise BadRequestError(preview['error'])

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
