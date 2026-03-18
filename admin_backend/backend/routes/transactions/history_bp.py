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
    linked_transaction_ids = data.get('linked_transaction_ids', [])



    if not lines or not txn_date:
        raise BadRequestError('Transaction date and lines are required')
    
    # Validation for balance and required fields per line
    total_debit = 0.0
    total_credit = 0.0
    for line in lines:
        amt = float(line.get('amount') or 0)
        side = str(line.get('side', 'DEBIT')).upper()
        if side == 'DEBIT':
            total_debit += amt
        else:
            total_credit += amt
            
    if abs(total_debit - total_credit) > 0.01:
        raise BadRequestError(f'Journal is not balanced. Debits: {total_debit}, Credits: {total_credit}')

    now = datetime.now()
    parent_txn_id = str(uuid.uuid4())
    
    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        mark_columns = get_table_columns(conn, 'marks')
        mapping_columns = get_table_columns(conn, 'mark_coa_mapping')

        # 1. Create Parent Transaction
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
            line_desc = line.get('description') or header_description
            
            # Dual COA IDs from line
            real_coa_id = line.get('coa_id')
            coretax_coa_id = line.get('coa_id_coretax')

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
            
            # For manual journal lines, we mark them as both if they have both mappings
            # But coretax flag in marks is usually a global setting for that mark if it's automated.
            # Here we can just set it to False or based on presence of coretax_coa_id
            if 'is_coretax' in mark_columns:
                mark_data['is_coretax'] = bool(coretax_coa_id)

            insert_cols = [c for c in mark_data.keys() if c in mark_columns]
            cols_sql = ', '.join(insert_cols)
            vals_sql = ', '.join(f":{c}" for c in insert_cols)
            conn.execute(text(f"INSERT INTO marks ({cols_sql}) VALUES ({vals_sql})"), mark_data)

            # Insert REAL Mapping
            if real_coa_id:
                mapping_id = str(uuid.uuid4())
                mapping_data = {
                    'id': mapping_id,
                    'mark_id': mark_id,
                    'coa_id': real_coa_id,
                    'mapping_type': line_side,
                    'created_at': now,
                    'updated_at': now,
                    'report_type': 'real'
                }
                mapping_insert_cols = [c for c in mapping_data.keys() if c in mapping_columns]
                mapping_cols_sql = ', '.join(mapping_insert_cols)
                mapping_vals_sql = ', '.join(f":{c}" for c in mapping_insert_cols)
                conn.execute(text(f"INSERT INTO mark_coa_mapping ({mapping_cols_sql}) VALUES ({mapping_vals_sql})"), mapping_data)

            # Insert CORETAX Mapping
            if coretax_coa_id:
                mapping_id = str(uuid.uuid4())
                mapping_data = {
                    'id': mapping_id,
                    'mark_id': mark_id,
                    'coa_id': coretax_coa_id,
                    'mapping_type': line_side,
                    'created_at': now,
                    'updated_at': now,
                    'report_type': 'coretax'
                }
                mapping_insert_cols = [c for c in mapping_data.keys() if c in mapping_columns]
                mapping_cols_sql = ', '.join(mapping_insert_cols)
                mapping_vals_sql = ', '.join(f":{c}" for c in mapping_insert_cols)
                conn.execute(text(f"INSERT INTO mark_coa_mapping ({mapping_cols_sql}) VALUES ({mapping_vals_sql})"), mapping_data)

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
                'created_at': now,
                'updated_at': now
            }

            child_insert_cols = [c for c in child_data.keys() if c in txn_columns]
            c_cols_sql = ', '.join(child_insert_cols)
            c_vals_sql = ', '.join(f":{c}" for c in child_insert_cols)
            conn.execute(text(f"INSERT INTO transactions ({c_cols_sql}) VALUES ({c_vals_sql})"), child_data)

        # Save links to existing transactions if provided
        if linked_transaction_ids:
            for linked_id in linked_transaction_ids:
                conn.execute(text("""
                    INSERT IGNORE INTO manual_journal_links (id, manual_txn_id, linked_txn_id, created_at)
                    VALUES (:id, :manual_txn_id, :linked_txn_id, :now)
                """), {
                    'id': str(uuid.uuid4()),
                    'manual_txn_id': parent_txn_id,
                    'linked_txn_id': linked_id,
                    'now': now
                })

    return jsonify({'message': 'Manual multi-line journal entry created successfully', 'id': parent_txn_id}), 201


@history_bp.route('/api/transactions/manual/<parent_id>', methods=['GET'])
def get_manual_journal(parent_id):
    """Get full data of a manual journal entry by its parent_id."""
    engine = require_db_engine()
    
    with engine.connect() as conn:
        # 1. Fetch Parent
        p_row = conn.execute(text("""
            SELECT id, txn_date, description, amount, company_id
            FROM transactions
            WHERE id = :id AND bank_code = 'MANUAL' AND (parent_id IS NULL OR parent_id = '')
        """), {'id': parent_id}).fetchone()
        
        if not p_row:
            raise NotFoundError('Manual journal parent not found')
            
        parent = serialize_row_values(p_row._mapping)
        
        # 2. Fetch Children and their mappings
        c_rows = conn.execute(text("""
            SELECT t.id, t.description, t.amount, t.db_cr, t.mark_id,
                   mcm.coa_id, mcm.report_type
            FROM transactions t
            LEFT JOIN marks m ON t.mark_id = m.id
            LEFT JOIN mark_coa_mapping mcm ON mcm.mark_id = m.id
            WHERE t.parent_id = :pid
            ORDER BY t.created_at ASC
        """), {'pid': parent_id}).fetchall()
        
        lines_map = {}
        for row in c_rows:
            d = serialize_row_values(row._mapping)
            tx_id = d['id']
            if tx_id not in lines_map:
                lines_map[tx_id] = {
                    'id': tx_id,
                    'description': d['description'],
                    'amount': float(d['amount']),
                    'side': 'DEBIT' if d['db_cr'] == 'DB' else 'CREDIT',
                    'coa_id': None,
                    'coa_id_coretax': None
                }
            
            # Map COA based on report_type
            if d['report_type'] == 'coretax':
                lines_map[tx_id]['coa_id_coretax'] = d['coa_id']
            else:
                lines_map[tx_id]['coa_id'] = d['coa_id']
        
        lines = list(lines_map.values())
        
        # 3. Fetch Linked Transactions
        l_rows = conn.execute(text("""
            SELECT t.id, t.txn_date, t.description, t.amount, t.db_cr, t.bank_code
            FROM manual_journal_links mjl
            JOIN transactions t ON mjl.linked_txn_id = t.id
            WHERE mjl.manual_txn_id = :pid
        """), {'pid': parent_id}).fetchall()
        
        linked = []
        for row in l_rows:
            d = serialize_row_values(row._mapping)
            d['db_cr'] = _normalize_db_cr(d.get('db_cr'))
            linked.append(d)
            
        return jsonify({
            'header': parent,
            'lines': lines,
            'linked_transactions': linked
        })


@history_bp.route('/api/transactions/manual/<parent_id>', methods=['PUT'])
def update_manual_journal(parent_id):
    """Update an existing manual journal entry."""
    engine = require_db_engine()
    data = request.json or {}
    lines = data.get('lines', [])
    header_description = data.get('description', '')
    txn_date = data.get('txn_date')
    company_id = data.get('company_id')
    linked_transaction_ids = data.get('linked_transaction_ids', [])


    if not lines or not txn_date:
        raise BadRequestError('Transaction date and lines are required')
    
    # Validation for balance
    total_debit = 0.0
    total_credit = 0.0
    for line in lines:
        amt = float(line.get('amount') or 0)
        side = str(line.get('side', 'DEBIT')).upper()
        if side == 'DEBIT':
            total_debit += amt
        else:
            total_credit += amt
            
    if abs(total_debit - total_credit) > 0.01:
        raise BadRequestError(f'Journal is not balanced. Debits: {total_debit}, Credits: {total_credit}')

    now = datetime.now()
    
    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        mark_columns = get_table_columns(conn, 'marks')
        mapping_columns = get_table_columns(conn, 'mark_coa_mapping')

        # 1. Verify and Update Parent
        p_row = conn.execute(text("SELECT id FROM transactions WHERE id = :id AND bank_code = 'MANUAL'"), {'id': parent_id}).fetchone()
        if not p_row:
            raise NotFoundError('Manual journal not found')

        conn.execute(text("""
            UPDATE transactions 
            SET txn_date = :txn_date, description = :description, amount = :amount, 
                company_id = :company_id, updated_at = :now
            WHERE id = :id
        """), {
            'id': parent_id,
            'txn_date': txn_date,
            'description': header_description,
            'amount': total_debit,
            'company_id': company_id if company_id else None,
            'now': now
        })

        # 2. Get old children and their marks to cleanup
        old_children = conn.execute(text("SELECT mark_id FROM transactions WHERE parent_id = :pid"), {'pid': parent_id}).fetchall()
        old_mark_ids = [r.mark_id for r in old_children if r.mark_id]

        # Cleanup
        if old_mark_ids:
            conn.execute(text("DELETE FROM mark_coa_mapping WHERE mark_id IN :ids"), {'ids': old_mark_ids})
            conn.execute(text("DELETE FROM marks WHERE id IN :ids"), {'ids': old_mark_ids})
        conn.execute(text("DELETE FROM transactions WHERE parent_id = :pid"), {'pid': parent_id})
        conn.execute(text("DELETE FROM manual_journal_links WHERE manual_txn_id = :pid"), {'pid': parent_id})

        # 3. Re-insert children
        for line in lines:
            line_id = str(uuid.uuid4())
            line_amount = float(line.get('amount', 0))
            line_side = str(line.get('side', 'DEBIT')).upper()
            line_desc = line.get('description') or header_description
            
            # Dual COA IDs from line
            real_coa_id = line.get('coa_id')
            coretax_coa_id = line.get('coa_id_coretax')

            mark_id = str(uuid.uuid4())
            mark_name = f"JV: {line_desc}"

            mark_data = {
                'id': mark_id,
                'internal_report': mark_name,
                'personal_use': mark_name,
                'created_at': now,
                'updated_at': now
            }
            if 'is_coretax' in mark_columns:
                mark_data['is_coretax'] = bool(coretax_coa_id)

            insert_cols = [c for c in mark_data.keys() if c in mark_columns]
            cols_sql = ', '.join(insert_cols)
            vals_sql = ', '.join(f":{c}" for c in insert_cols)
            conn.execute(text(f"INSERT INTO marks ({cols_sql}) VALUES ({vals_sql})"), mark_data)

            # Insert REAL Mapping
            if real_coa_id:
                mapping_id = str(uuid.uuid4())
                mapping_data = {
                    'id': mapping_id,
                    'mark_id': mark_id,
                    'coa_id': real_coa_id,
                    'mapping_type': line_side,
                    'created_at': now,
                    'updated_at': now,
                    'report_type': 'real'
                }
                mapping_insert_cols = [c for c in mapping_data.keys() if c in mapping_columns]
                mapping_cols_sql = ', '.join(mapping_insert_cols)
                mapping_vals_sql = ', '.join(f":{c}" for c in mapping_insert_cols)
                conn.execute(text(f"INSERT INTO mark_coa_mapping ({mapping_cols_sql}) VALUES ({mapping_vals_sql})"), mapping_data)

            # Insert CORETAX Mapping
            if coretax_coa_id:
                mapping_id = str(uuid.uuid4())
                mapping_data = {
                    'id': mapping_id,
                    'mark_id': mark_id,
                    'coa_id': coretax_coa_id,
                    'mapping_type': line_side,
                    'created_at': now,
                    'updated_at': now,
                    'report_type': 'coretax'
                }
                mapping_insert_cols = [c for c in mapping_data.keys() if c in mapping_columns]
                mapping_cols_sql = ', '.join(mapping_insert_cols)
                mapping_vals_sql = ', '.join(f":{c}" for c in mapping_insert_cols)
                conn.execute(text(f"INSERT INTO mark_coa_mapping ({mapping_cols_sql}) VALUES ({mapping_vals_sql})"), mapping_data)

            line_db_cr = 'DB' if line_side == 'DEBIT' else 'CR'
            child_data = {
                'id': line_id,
                'parent_id': parent_id,
                'txn_date': txn_date,
                'description': line_desc,
                'amount': line_amount,
                'db_cr': line_db_cr,
                'bank_code': 'MANUAL',
                'source_file': 'MANUAL',
                'mark_id': mark_id,
                'company_id': company_id if company_id else None,
                'created_at': now,
                'updated_at': now
            }

            child_insert_cols = [c for c in child_data.keys() if c in txn_columns]
            c_cols_sql = ', '.join(child_insert_cols)
            c_vals_sql = ', '.join(f":{c}" for c in child_insert_cols)
            conn.execute(text(f"INSERT INTO transactions ({c_cols_sql}) VALUES ({c_vals_sql})"), child_data)

        # 4. Refresh Links
        if linked_transaction_ids:
            for linked_id in linked_transaction_ids:
                conn.execute(text("""
                    INSERT IGNORE INTO manual_journal_links (id, manual_txn_id, linked_txn_id, created_at)
                    VALUES (:id, :manual_txn_id, :linked_txn_id, :now)
                """), {
                    'id': str(uuid.uuid4()),
                    'manual_txn_id': parent_id,
                    'linked_txn_id': linked_id,
                    'now': now
                })

    return jsonify({'message': 'Manual journal updated successfully'})


@history_bp.route('/api/transactions/manual/<txn_id>/links', methods=['GET'])
def get_manual_journal_links(txn_id):
    """Get all transactions linked to a manual journal entry."""
    engine = require_db_engine()

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT t.id, t.txn_date, t.description, t.amount, t.db_cr,
                   t.bank_code, c.name as company_name
            FROM manual_journal_links mjl
            JOIN transactions t ON mjl.linked_txn_id = t.id
            LEFT JOIN companies c ON t.company_id = c.id
            WHERE mjl.manual_txn_id = :txn_id
            ORDER BY t.txn_date DESC
        """), {'txn_id': txn_id}).fetchall()

        links = []
        for row in rows:
            d = serialize_row_values(row._mapping)
            d['db_cr'] = _normalize_db_cr(d.get('db_cr'))
            links.append(d)

        return jsonify({'links': links})


@history_bp.route('/api/transactions/linkable', methods=['GET'])
def get_linkable_transactions():
    """Search transactions that can be linked to a manual journal.
    Excludes: child transactions (have a parent_id), MANUAL source transactions.
    """
    engine = require_db_engine()

    company_id = request.args.get('company_id')
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    exclude_manual_txn_id = request.args.get('exclude_manual_txn_id')  # exclude already-linked ones

    where_clauses = [
        "(t.source_file IS NULL OR t.source_file != 'MANUAL')",
        "(t.parent_id IS NULL OR t.parent_id = '')",
    ]
    params = {}

    if company_id:
        where_clauses.append("t.company_id = :company_id")
        params['company_id'] = company_id

    if search:
        where_clauses.append("t.description LIKE :search")
        params['search'] = f'%{search}%'

    if start_date:
        where_clauses.append("t.txn_date >= :start_date")
        params['start_date'] = start_date

    if end_date:
        where_clauses.append("t.txn_date <= :end_date")
        params['end_date'] = end_date

    # Exclude transactions already linked to a specific manual journal
    if exclude_manual_txn_id:
        where_clauses.append("""
            t.id NOT IN (
                SELECT linked_txn_id FROM manual_journal_links
                WHERE manual_txn_id = :exclude_manual_txn_id
            )
        """)
        params['exclude_manual_txn_id'] = exclude_manual_txn_id

    where_sql = ' AND '.join(where_clauses)

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT t.id, t.txn_date, t.description, t.amount, t.db_cr,
                   t.bank_code, m.internal_report as mark_name,
                   c.name as company_name
            FROM transactions t
            LEFT JOIN marks m ON t.mark_id = m.id
            LEFT JOIN companies c ON t.company_id = c.id
            WHERE {where_sql}
            ORDER BY t.txn_date DESC, t.created_at DESC
            LIMIT 50
        """), params).fetchall()

        results = []
        for row in rows:
            d = serialize_row_values(row._mapping)
            d['db_cr'] = _normalize_db_cr(d.get('db_cr'))
            results.append(d)

        return jsonify({'transactions': results})


@history_bp.route('/api/transactions', methods=['GET'])
def get_transactions():
    engine = require_db_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT t.*, m.internal_report, m.personal_use, m.tax_report,
                   c.name as company_name, c.short_name as company_short_name,
                   mjl.manual_txn_id as linked_manual_id
            FROM transactions t
            LEFT JOIN marks m ON t.mark_id = m.id
            LEFT JOIN companies c ON t.company_id = c.id
            LEFT JOIN manual_journal_links mjl ON t.id = mjl.linked_txn_id
            ORDER BY t.txn_date DESC, t.created_at DESC
        """))
        transactions = serialize_result_rows(result)
        for d in transactions:
            d['db_cr'] = _normalize_db_cr(d.get('db_cr'))
            if not str(d.get('description') or '').strip():
                fallback_desc = d.get('internal_report') or d.get('personal_use') or d.get('tax_report')
                if fallback_desc:
                    d['description'] = fallback_desc
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
        txn_columns = get_table_columns(conn, 'transactions')
        update_fields = ["company_id = :company_id"]
        params = {'company_id': company_id, 'updated_at': now, 'txn_id': txn_id}
        if 'updated_at' in txn_columns:
            update_fields.append("updated_at = :updated_at")

        if 'parent_id' in txn_columns:
            row = conn.execute(
                text("SELECT id, parent_id FROM transactions WHERE id = :txn_id LIMIT 1"),
                {'txn_id': txn_id}
            ).fetchone()
            if not row:
                raise NotFoundError('Transaction not found')

            parent_id = str(row.parent_id) if row.parent_id else None
            if parent_id:
                params['parent_id'] = parent_id
                conn.execute(text(f"""
                    UPDATE transactions
                    SET {', '.join(update_fields)}
                    WHERE id = :txn_id OR id = :parent_id OR parent_id = :parent_id
                """), params)
            else:
                conn.execute(text(f"""
                    UPDATE transactions
                    SET {', '.join(update_fields)}
                    WHERE id = :txn_id OR parent_id = :txn_id
                """), params)
        else:
            result = conn.execute(
                text(f"UPDATE transactions SET {', '.join(update_fields)} WHERE id = :txn_id"),
                params
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
        txn_columns = get_table_columns(conn, 'transactions')
        update_fields = ["company_id = :company_id"]
        params = {'company_id': company_id, 'updated_at': now}
        if 'updated_at' in txn_columns:
            update_fields.append("updated_at = :updated_at")

        update_ids = set(txn_ids)
        if 'parent_id' in txn_columns and txn_ids:
            rows = conn.execute(
                text("SELECT id, parent_id FROM transactions WHERE id IN :ids")
                .bindparams(bindparam('ids', expanding=True)),
                {'ids': list(update_ids)}
            ).fetchall()
            parent_ids = set()
            for row in rows:
                parent_ids.add(str(row.parent_id) if row.parent_id else str(row.id))

            if parent_ids:
                children = conn.execute(
                    text("SELECT id FROM transactions WHERE parent_id IN :parent_ids")
                    .bindparams(bindparam('parent_ids', expanding=True)),
                    {'parent_ids': list(parent_ids)}
                ).fetchall()
                update_ids.update(parent_ids)
                update_ids.update(str(row.id) for row in children)

        if update_ids:
            params['ids'] = list(update_ids)
            conn.execute(
                text(f"""
                    UPDATE transactions
                    SET {', '.join(update_fields)}
                    WHERE id IN :ids
                """).bindparams(bindparam('ids', expanding=True)),
                params
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

        mark_name_lookup = {}
        mark_ids = list({str(split.get('mark_id')) for split in splits if split.get('mark_id')})
        if mark_ids:
            mark_rows = conn.execute(
                text("""
                    SELECT id, internal_report, personal_use, tax_report
                    FROM marks
                    WHERE id IN :ids
                """).bindparams(bindparam('ids', expanding=True)),
                {'ids': mark_ids}
            ).fetchall()
            for row in mark_rows:
                mark_name_lookup[str(row.id)] = row.internal_report or row.personal_use or row.tax_report or ''

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
            raw_desc = split.get('description')
            description = str(raw_desc).strip() if raw_desc is not None else ''
            if not description:
                mark_label = mark_name_lookup.get(str(split.get('mark_id') or ''))
                description = mark_label or parent_data.get('description') or ''
            conn.execute(insert_sql, {
                'id': str(uuid.uuid4()),
                'parent_id': txn_id,
                'description': description,
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
