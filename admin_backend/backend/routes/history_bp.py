import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import bindparam, text

from backend.errors import BadRequestError, NotFoundError
from backend.db.schema import get_table_columns
from backend.routes.accounting_utils import require_db_engine, serialize_result_rows, serialize_row_values
from backend.routes.route_utils import (
    _normalize_db_cr,
    _normalize_iso_date,
    _parse_bool,
)

history_bp = Blueprint('history_bp', __name__)


@history_bp.route('/api/transactions/manual', methods=['POST'])
def create_manual_transaction():
    engine = require_db_engine()

    data = request.json or {}
    txn_date = data.get('txn_date')
    header_description = data.get('description', 'Manual Journal')
    company_id = data.get('company_id')
    lines = data.get('lines', [])

    if not txn_date or not lines:
        raise BadRequestError('Missing required fields (date, lines)')

    total_debit = 0.0
    total_credit = 0.0
    for line in lines:
        try:
            amt = float(line.get('amount', 0))
        except (ValueError, TypeError):
            raise BadRequestError(f"Invalid amount in line for COA {line.get('coa_id')}")

        side = str(line.get('side', 'DEBIT')).upper()
        if side == 'DEBIT':
            total_debit += amt
        else:
            total_credit += amt

    if abs(total_debit - total_credit) > 0.01:
        raise BadRequestError(
            f'Journal is not balanced. Debits ({total_debit:,.2f}) != Credits ({total_credit:,.2f})'
        )

    now = datetime.now()
    parent_txn_id = str(uuid.uuid4())

    with engine.begin() as conn:
        mark_columns = get_table_columns(conn, 'marks')
        txn_columns = get_table_columns(conn, 'transactions')

        conn.execute(text("""
            INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, source_file, company_id, created_at, updated_at)
            VALUES (:id, :txn_date, :description, :amount, 'DB', 'MANUAL', 'MANUAL', :company_id, :now, :now)
        """), {
            'id': parent_txn_id,
            'txn_date': txn_date,
            'description': header_description,
            'amount': total_debit,
            'company_id': company_id if company_id else None,
            'now': now
        })

        for line in lines:
            line_id = str(uuid.uuid4())
            line_amount = float(line.get('amount', 0))
            line_side = str(line.get('side', 'DEBIT')).upper()
            line_coa_id = line.get('coa_id')
            line_desc = line.get('description') or header_description

            mark_id = str(uuid.uuid4())
            mark_name = f"JV: {line_desc}"

            mark_data = {
                'id': mark_id,
                'internal_report': mark_name,
                'personal_use': mark_name,
                'created_at': now,
                'updated_at': now
            }
            if 'is_asset' in mark_columns:
                mark_data['is_asset'] = False
            if 'is_service' in mark_columns:
                mark_data['is_service'] = False
            if 'is_salary_component' in mark_columns:
                mark_data['is_salary_component'] = False
            if 'is_rental' in mark_columns:
                mark_data['is_rental'] = False
            if 'is_coretax' in mark_columns:
                mark_data['is_coretax'] = False

            insert_cols = [c for c in mark_data.keys() if c in mark_columns]
            cols_sql = ', '.join(insert_cols)
            vals_sql = ', '.join(f":{c}" for c in insert_cols)
            conn.execute(text(f"INSERT INTO marks ({cols_sql}) VALUES ({vals_sql})"), mark_data)

            mapping_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO mark_coa_mapping (id, mark_id, coa_id, mapping_type, created_at, updated_at)
                VALUES (:id, :mark_id, :coa_id, :side, :now, :now)
            """), {
                'id': mapping_id,
                'mark_id': mark_id,
                'coa_id': line_coa_id,
                'side': line_side,
                'now': now
            })

            line_db_cr = 'DB' if line_side == 'DEBIT' else 'CR'
            child_data = {
                'id': line_id,
                'parent_id': parent_txn_id,
                'txn_date': txn_date,
                'description': line_desc,
                'amount': line_amount,
                'db_cr': line_db_cr,
                'bank_code': 'MANUAL',
                'source_file': 'MANUAL',
                'mark_id': mark_id,
                'company_id': company_id if company_id else None,
                'now': now
            }

            child_insert_cols = [c for c in child_data.keys() if c in txn_columns]
            c_cols_sql = ', '.join(child_insert_cols)
            c_vals_sql = ', '.join(f":{c}" for c in child_insert_cols)
            conn.execute(text(f"INSERT INTO transactions ({c_cols_sql}) VALUES ({c_vals_sql})"), child_data)

    return jsonify({'message': 'Manual multi-line journal entry created successfully', 'id': parent_txn_id}), 201


@history_bp.route('/api/transactions', methods=['GET'])
def get_transactions():
    engine = require_db_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT t.*, m.internal_report, m.personal_use, m.tax_report,
                   c.name as company_name, c.short_name as company_short_name
            FROM transactions t
            LEFT JOIN marks m ON t.mark_id = m.id
            LEFT JOIN companies c ON t.company_id = c.id
            ORDER BY t.txn_date DESC, t.created_at DESC
        """))
        transactions = serialize_result_rows(result)
        for d in transactions:
            d['db_cr'] = _normalize_db_cr(d.get('db_cr'))
        return jsonify({'transactions': transactions})


@history_bp.route('/api/transactions/upload-summary', methods=['GET'])
def get_upload_summary():
    engine = require_db_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT t.source_file,
                   COUNT(*) as transaction_count,
                   MIN(t.txn_date) as start_date,
                   MAX(t.txn_date) as end_date,
                   t.bank_code,
                   COUNT(DISTINCT t.company_id) as company_count,
                   SUM(CASE WHEN t.db_cr = 'DB' THEN t.amount ELSE 0 END) as total_debit,
                   SUM(CASE WHEN t.db_cr = 'CR' THEN t.amount ELSE 0 END) as total_credit,
                   MAX(t.created_at) as last_upload
            FROM transactions t
            GROUP BY t.source_file, t.bank_code
            ORDER BY last_upload DESC
        """))
        summary = serialize_result_rows(result)
        return jsonify({'summary': summary})


@history_bp.route('/api/transactions/delete-by-source', methods=['POST'])
def delete_by_source():
    engine = require_db_engine()

    data = request.json or {}
    source_file = data.get('source_file')
    bank_code = data.get('bank_code')
    company_id = data.get('company_id')

    if not source_file:
        raise BadRequestError('source_file is required')

    with engine.begin() as conn:
        where_clauses = ["source_file = :source_file"]
        params = {'source_file': source_file}

        if bank_code:
            where_clauses.append("bank_code = :bank_code")
            params['bank_code'] = bank_code
        if company_id:
            where_clauses.append("company_id = :company_id")
            params['company_id'] = company_id

        result = conn.execute(
            text(f"DELETE FROM transactions WHERE {' AND '.join(where_clauses)}"),
            params
        )
        return jsonify({'message': f'Deleted {result.rowcount} transactions'})


@history_bp.route('/api/transactions/<txn_id>/assign-mark', methods=['POST'])
def assign_mark_transaction(txn_id):
    engine = require_db_engine()

    data = request.json or {}
    mark_id = data.get('mark_id')
    now = datetime.now()
    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        if mark_id and 'parent_id' in txn_columns:
            has_children = conn.execute(text("""
                SELECT 1
                FROM transactions
                WHERE parent_id = :txn_id
                LIMIT 1
            """), {'txn_id': txn_id}).fetchone()
            if has_children:
                raise BadRequestError(
                    'Transaksi ini sudah memiliki multi mark (split). Ubah mark pada split, bukan parent.'
                )

        result = conn.execute(
            text("UPDATE transactions SET mark_id = :mark_id, updated_at = :updated_at WHERE id = :id"),
            {'id': txn_id, 'mark_id': mark_id, 'updated_at': now}
        )
        if int(result.rowcount or 0) == 0:
            raise NotFoundError('Transaction not found')
        return jsonify({'message': 'Transaction marked successfully'})


@history_bp.route('/api/transactions/<txn_id>/amortization-group', methods=['PUT', 'PATCH', 'POST'])
def update_transaction_amortization_group(txn_id):
    engine = require_db_engine()

    payload = request.json or {}
    asset_group_id_raw = payload.get('asset_group_id')
    asset_group_id = str(asset_group_id_raw).strip() if asset_group_id_raw not in (None, '') else None
    is_amortizable = _parse_bool(payload.get('is_amortizable', True))
    use_half_rate = _parse_bool(payload.get('use_half_rate', False))
    amortization_start_date = _normalize_iso_date(payload.get('amortization_start_date'))
    amortization_notes = payload.get('amortization_notes')
    if amortization_notes is not None:
        amortization_notes = str(amortization_notes).strip()
    if amortization_notes == '':
        amortization_notes = None

    useful_life_raw = payload.get('amortization_useful_life')
    amortization_useful_life = None
    if useful_life_raw not in (None, ''):
        try:
            amortization_useful_life = int(useful_life_raw)
            if amortization_useful_life <= 0:
                raise BadRequestError('amortization_useful_life must be greater than 0')
        except (TypeError, ValueError):
            raise BadRequestError('amortization_useful_life must be numeric')

    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        required_columns = {'amortization_asset_group_id', 'is_amortizable', 'use_half_rate', 'amortization_start_date'}
        if not required_columns.issubset(txn_columns):
            raise BadRequestError(
                'Kolom amortization di transactions belum lengkap. Jalankan migrasi amortization terbaru.'
            )

        set_fields = [
            "amortization_asset_group_id = :asset_group_id",
            "is_amortizable = :is_amortizable",
            "use_half_rate = :use_half_rate",
            "amortization_start_date = :amortization_start_date"
        ]
        params = {
            'txn_id': txn_id,
            'asset_group_id': asset_group_id,
            'is_amortizable': is_amortizable,
            'use_half_rate': use_half_rate,
            'amortization_start_date': amortization_start_date
        }

        if 'amortization_useful_life' in txn_columns:
            set_fields.append("amortization_useful_life = :amortization_useful_life")
            params['amortization_useful_life'] = amortization_useful_life
        if 'amortization_notes' in txn_columns:
            set_fields.append("amortization_notes = :amortization_notes")
            params['amortization_notes'] = amortization_notes
        if 'updated_at' in txn_columns:
            set_fields.append("updated_at = :updated_at")
            params['updated_at'] = datetime.now()

        result = conn.execute(text(f"""
            UPDATE transactions
            SET {', '.join(set_fields)}
            WHERE id = :txn_id
        """), params)
        if int(result.rowcount or 0) == 0:
            raise NotFoundError('Transaction not found')

    return jsonify({
        'message': 'Transaction amortization group updated successfully',
        'transaction_id': txn_id,
        'asset_group_id': asset_group_id,
        'is_amortizable': is_amortizable,
        'use_half_rate': use_half_rate,
        'amortization_start_date': amortization_start_date,
        'amortization_useful_life': amortization_useful_life,
        'amortization_notes': amortization_notes
    })


@history_bp.route('/api/transactions/<txn_id>/assign-company', methods=['POST'])
def assign_company_transaction(txn_id):
    engine = require_db_engine()

    data = request.json or {}
    company_id = data.get('company_id')
    now = datetime.now()
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE transactions SET company_id = :company_id, updated_at = :updated_at WHERE id = :id"),
            {'id': txn_id, 'company_id': company_id, 'updated_at': now}
        )
        if int(result.rowcount or 0) == 0:
            raise NotFoundError('Transaction not found')
    return jsonify({'message': 'Company assigned successfully'})


@history_bp.route('/api/transactions/bulk-mark', methods=['POST'])
def bulk_mark_transactions():
    engine = require_db_engine()

    data = request.json or {}
    txn_ids = data.get('transaction_ids', [])
    mark_id = data.get('mark_id') or None

    if not txn_ids:
        raise BadRequestError('No transaction IDs provided')

    now = datetime.now()
    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        blocked_ids = []
        updatable_ids = list(txn_ids)

        if mark_id and 'parent_id' in txn_columns:
            blocked_rows = conn.execute(text("""
                SELECT t.id
                FROM transactions t
                WHERE t.id IN :ids
                  AND EXISTS (
                    SELECT 1
                    FROM transactions c
                    WHERE c.parent_id = t.id
                  )
            """).bindparams(bindparam('ids', expanding=True)), {'ids': updatable_ids}).fetchall()
            blocked_ids = [str(row.id) for row in blocked_rows]
            blocked_set = set(blocked_ids)
            updatable_ids = [current_id for current_id in updatable_ids if str(current_id) not in blocked_set]

        if updatable_ids:
            conn.execute(text("""
                UPDATE transactions
                SET mark_id = :mark_id, updated_at = :updated_at
                WHERE id IN :ids
            """).bindparams(bindparam('ids', expanding=True)), {
                'ids': updatable_ids,
                'mark_id': mark_id,
                'updated_at': now
            })

        return jsonify({
            'message': f'{len(updatable_ids)} transactions updated successfully',
            'updated_count': len(updatable_ids),
            'skipped_split_parent_ids': blocked_ids
        })


@history_bp.route('/api/transactions/bulk-assign-company', methods=['POST'])
def bulk_assign_company_transactions():
    engine = require_db_engine()

    data = request.json or {}
    txn_ids = data.get('transaction_ids', [])
    company_id = data.get('company_id') or None

    if not txn_ids:
        raise BadRequestError('No transaction IDs provided')

    now = datetime.now()
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE transactions
                SET company_id = :company_id, updated_at = :updated_at
                WHERE id IN :ids
            """).bindparams(bindparam('ids', expanding=True)),
            {'ids': txn_ids, 'company_id': company_id, 'updated_at': now}
        )
    return jsonify({'message': f'{len(txn_ids)} transactions updated successfully'})


@history_bp.route('/api/transactions/<txn_id>', methods=['DELETE'])
def delete_transaction(txn_id):
    engine = require_db_engine()

    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM transactions WHERE id = :id"), {'id': txn_id})
        if int(result.rowcount or 0) == 0:
            raise NotFoundError('Transaction not found')
    return jsonify({'message': 'Transaction deleted successfully'})


@history_bp.route('/api/transactions/bulk-delete', methods=['POST'])
def bulk_delete_transactions():
    engine = require_db_engine()

    data = request.json or {}
    txn_ids = data.get('transaction_ids', [])
    if not txn_ids:
        raise BadRequestError('No transaction IDs provided')
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM transactions WHERE id IN :ids").bindparams(bindparam('ids', expanding=True)),
            {'ids': txn_ids}
        )
    return jsonify({'message': f'{len(txn_ids)} transactions deleted successfully'})


@history_bp.route('/api/transactions/<transaction_id>/notes', methods=['PUT'])
def update_transaction_notes(transaction_id):
    engine = require_db_engine()

    data = request.json or {}
    notes = data.get('notes')
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE transactions SET notes = :notes, updated_at = :now WHERE id = :id"),
            {'id': transaction_id, 'notes': notes, 'now': datetime.now()}
        )
        if int(result.rowcount or 0) == 0:
            raise NotFoundError('Transaction not found')
    return jsonify({'message': 'Notes updated successfully'})


@history_bp.route('/api/transactions/<txn_id>/splits', methods=['GET'])
def get_transaction_splits(txn_id):
    engine = require_db_engine()

    with engine.connect() as conn:
        main_result = conn.execute(text("""
            SELECT id, description, amount, db_cr, txn_date, mark_id, company_id, notes
            FROM transactions
            WHERE id = :txn_id
        """), {'txn_id': txn_id}).fetchone()

        if not main_result:
            raise NotFoundError('Transaction not found')

        splits_result = conn.execute(text("""
            SELECT id, description, amount, db_cr, txn_date, mark_id, notes
            FROM transactions
            WHERE parent_id = :txn_id
            ORDER BY txn_date
        """), {'txn_id': txn_id}).fetchall()

        main_transaction = serialize_row_values(main_result._mapping)
        split_transactions = serialize_result_rows(splits_result)

        return jsonify({
            'main_transaction': main_transaction,
            'splits': split_transactions,
            'total_split_amount': sum(split.get('amount', 0) for split in split_transactions)
        })


@history_bp.route('/api/transactions/<txn_id>/splits', methods=['POST'])
def save_transaction_splits(txn_id):
    engine = require_db_engine()

    data = request.json or {}
    splits = data.get('splits', [])

    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        if 'parent_id' not in txn_columns:
            raise BadRequestError('Split feature unavailable: transactions.parent_id column is missing')

        parent_result = conn.execute(text("""
            SELECT company_id, txn_date, mark_id, db_cr
            FROM transactions
            WHERE id = :txn_id
            LIMIT 1
        """), {'txn_id': txn_id}).fetchone()
        if not parent_result:
            raise NotFoundError('Transaction not found')

        parent_data = dict(parent_result._mapping)
        conn.execute(text("DELETE FROM transactions WHERE parent_id = :txn_id"), {'txn_id': txn_id})

        if splits and 'mark_id' in txn_columns:
            if 'updated_at' in txn_columns:
                conn.execute(text("""
                    UPDATE transactions
                    SET mark_id = NULL, updated_at = :updated_at
                    WHERE id = :txn_id
                """), {'txn_id': txn_id, 'updated_at': datetime.now()})
            else:
                conn.execute(text("""
                    UPDATE transactions
                    SET mark_id = NULL
                    WHERE id = :txn_id
                """), {'txn_id': txn_id})

        insert_sql = text("""
            INSERT INTO transactions (
                id, parent_id, description, amount, db_cr, txn_date,
                mark_id, notes, company_id, created_at, updated_at
            ) VALUES (
                :id, :parent_id, :description, :amount, :db_cr, :txn_date,
                :mark_id, :notes, :company_id, :created_at, :updated_at
            )
        """)

        now = datetime.now()
        for split in splits:
            conn.execute(insert_sql, {
                'id': str(uuid.uuid4()),
                'parent_id': txn_id,
                'description': split.get('description', ''),
                'amount': split.get('amount', 0),
                'db_cr': _normalize_db_cr(split.get('db_cr') or parent_data.get('db_cr') or 'DB'),
                'txn_date': parent_data.get('txn_date'),
                'mark_id': split.get('mark_id'),
                'notes': split.get('notes', ''),
                'company_id': parent_data.get('company_id'),
                'created_at': now,
                'updated_at': now
            })

        return jsonify({'message': 'Splits saved successfully', 'splits_count': len(splits)})
