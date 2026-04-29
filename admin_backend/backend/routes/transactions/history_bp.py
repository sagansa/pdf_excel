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


def _normalize_manual_line_side(value):
    return 'CREDIT' if str(value or '').strip().upper() == 'CREDIT' else 'DEBIT'


def _manual_journal_mark_label(mark_data):
    for key in ('internal_report', 'personal_use', 'tax_report'):
        value = str((mark_data or {}).get(key) or '').strip()
        if value:
            return value
    return ''


def _fetch_marks_lookup(conn, mark_ids):
    normalized_ids = sorted({str(mark_id).strip() for mark_id in (mark_ids or []) if str(mark_id or '').strip()})
    if not normalized_ids:
        return {}

    rows = conn.execute(
        text("""
            SELECT
                m.id,
                m.internal_report,
                m.personal_use,
                m.tax_report,
                COALESCE(
                    m.natural_direction,
                    (
                        SELECT CASE
                            WHEN SUM(CASE WHEN UPPER(TRIM(COALESCE(t.db_cr, ''))) IN ('DB', 'DEBIT', 'D', 'DE') THEN 1 ELSE 0 END) >=
                                 SUM(CASE WHEN UPPER(TRIM(COALESCE(t.db_cr, ''))) IN ('CR', 'CREDIT', 'K', 'KREDIT') THEN 1 ELSE 0 END)
                            THEN 'DB'
                            ELSE 'CR'
                        END
                        FROM transactions t
                        WHERE t.mark_id = m.id
                    )
                ) AS natural_direction
            FROM marks m
            WHERE id IN :ids
        """).bindparams(bindparam('ids', expanding=True)),
        {'ids': normalized_ids}
    ).fetchall()

    lookup = {}
    for row in rows:
        data = serialize_row_values(row._mapping)
        lookup[str(data.get('id'))] = {
            **data,
            'label': _manual_journal_mark_label(data)
        }
    return lookup


def _prepare_manual_journal_lines(lines, header_description, journal_amount):
    normalized_lines = lines or []
    if not normalized_lines:
        raise BadRequestError('Generated journal lines are required')

    total_debit = 0.0
    total_credit = 0.0
    prepared_lines = []
    for index, line in enumerate(normalized_lines, start=1):
        side = _normalize_manual_line_side(line.get('side'))
        try:
            amount = float(line.get('amount') or 0)
        except (TypeError, ValueError):
            raise BadRequestError(f'Line {index}: amount must be numeric')
        if amount <= 0:
            raise BadRequestError(f'Line {index}: amount must be greater than 0')

        coa_id = str(line.get('coa_id') or '').strip()
        coa_id_coretax = str(line.get('coa_id_coretax') or '').strip()
        if not coa_id and not coa_id_coretax:
            raise BadRequestError(f'Line {index}: at least one COA mapping is required')

        description = str(line.get('description') or '').strip()
        if not description:
            description = str(header_description or '').strip() or 'Manual Journal'

        label = str(line.get('label') or '').strip()
        line_total = amount
        if side == 'DEBIT':
            total_debit += line_total
        else:
            total_credit += line_total

        prepared_lines.append({
            'side': side,
            'amount': line_total,
            'description': description,
            'label': label,
            'coa_id': coa_id or None,
            'coa_id_coretax': coa_id_coretax or None,
        })

    if abs(total_debit - total_credit) > 0.01:
        raise BadRequestError(f'Journal is not balanced. Debits: {total_debit}, Credits: {total_credit}')
    if abs(total_debit - float(journal_amount or 0)) > 0.01:
        raise BadRequestError('Journal total must match the generated debit and credit totals')

    return prepared_lines


def _normalize_manual_db_cr(value):
    normalized = str(value or '').strip().upper()
    if normalized in ('CR', 'CREDIT', 'K', 'KREDIT'):
        return 'CR'
    return 'DB'


def _prepare_manual_journal_entry(conn, payload):
    txn_date = payload.get('txn_date')
    description = str(payload.get('description') or '').strip()
    mark_id = str(payload.get('mark_id') or '').strip()
    linked_transaction_ids = []
    linked_seen = set()
    for linked_id in (payload.get('linked_transaction_ids') or []):
        normalized_id = str(linked_id or '').strip()
        if not normalized_id or normalized_id in linked_seen:
            continue
        linked_seen.add(normalized_id)
        linked_transaction_ids.append(normalized_id)

    if not txn_date:
        raise BadRequestError('Transaction date is required')
    if not description:
        raise BadRequestError('Journal memo is required')
    if not mark_id:
        raise BadRequestError('Mark is required')

    amount_raw = payload.get('amount')
    try:
        amount = float(amount_raw or 0)
    except (TypeError, ValueError):
        raise BadRequestError('Amount must be numeric')

    if amount <= 0:
        raise BadRequestError('Amount must be greater than 0')

    mark_lookup = _fetch_marks_lookup(conn, [mark_id])
    if mark_id not in mark_lookup:
        raise BadRequestError('Selected mark was not found')

    mark = mark_lookup[mark_id]
    db_cr = _normalize_manual_db_cr(mark.get('natural_direction'))
    prepared_lines = _prepare_manual_journal_lines(
        payload.get('lines'),
        description,
        amount,
    )

    return {
        'txn_date': txn_date,
        'description': description,
        'company_id': payload.get('company_id') or None,
        'mark_id': mark_id,
        'amount': amount,
        'db_cr': db_cr,
        'lines': prepared_lines,
        'linked_transaction_ids': linked_transaction_ids,
    }


def _insert_manual_journal_lines(conn, parent_id, prepared_entry, txn_columns, now):
    for index, line in enumerate(prepared_entry['lines'], start=1):
        line_id = str(uuid.uuid4())
        line_side = line['side']
        line_db_cr = 'DB' if line_side == 'DEBIT' else 'CR'

        child_data = {
            'id': line_id,
            'parent_id': parent_id,
            'txn_date': prepared_entry['txn_date'],
            'description': line['description'] or prepared_entry['description'],
            'amount': line['amount'],
            'db_cr': line_db_cr,
            'bank_code': 'MANUAL',
            'source_file': 'MANUAL',
            'mark_id': prepared_entry['mark_id'],
            'coa_id': line.get('coa_id'),
            'coa_id_coretax': line.get('coa_id_coretax'),
            'company_id': prepared_entry['company_id'],
            'created_at': now,
            'updated_at': now,
        }
        child_insert_cols = [column for column in child_data.keys() if column in txn_columns]
        child_cols_sql = ', '.join(child_insert_cols)
        child_vals_sql = ', '.join(f":{column}" for column in child_insert_cols)
        conn.execute(text(f"INSERT INTO transactions ({child_cols_sql}) VALUES ({child_vals_sql})"), child_data)

def _delete_orphan_marks(conn, mark_ids):
    normalized_ids = sorted({str(mark_id).strip() for mark_id in (mark_ids or []) if str(mark_id or '').strip()})
    if not normalized_ids:
        return

    used_rows = conn.execute(
        text("SELECT DISTINCT mark_id FROM transactions WHERE mark_id IN :mids")
        .bindparams(bindparam('mids', expanding=True)),
        {'mids': normalized_ids}
    ).fetchall()
    used_mark_ids = {
        str(row.mark_id).strip()
        for row in used_rows
        if getattr(row, 'mark_id', None)
    }
    marks_to_delete = [mark_id for mark_id in normalized_ids if mark_id not in used_mark_ids]
    if not marks_to_delete:
        return

    conn.execute(
        text("DELETE FROM mark_coa_mapping WHERE mark_id IN :mids")
        .bindparams(bindparam('mids', expanding=True)),
        {'mids': marks_to_delete}
    )
    conn.execute(
        text("DELETE FROM marks WHERE id IN :mids")
        .bindparams(bindparam('mids', expanding=True)),
        {'mids': marks_to_delete}
    )


@history_bp.route('/api/transactions/manual', methods=['POST'])
def create_manual_transaction():
    engine = require_db_engine()

    data = request.json or {}
    now = datetime.now()
    txn_id = str(uuid.uuid4())
    
    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        prepared_entry = _prepare_manual_journal_entry(conn, data)

        transaction_data = {
            'id': txn_id,
            'txn_date': prepared_entry['txn_date'],
            'description': prepared_entry['description'],
            'amount': prepared_entry['amount'],
            'db_cr': prepared_entry['db_cr'],
            'bank_code': 'MANUAL',
            'source_file': 'MANUAL',
            'company_id': prepared_entry['company_id'],
            'mark_id': prepared_entry['mark_id'],
            'created_at': now,
            'updated_at': now,
        }
        insert_cols = [c for c in transaction_data.keys() if c in txn_columns]
        cols_sql = ', '.join(insert_cols)
        vals_sql = ', '.join(f":{c}" for c in insert_cols)
        conn.execute(text(f"INSERT INTO transactions ({cols_sql}) VALUES ({vals_sql})"), transaction_data)
        _insert_manual_journal_lines(conn, txn_id, prepared_entry, txn_columns, now)

        if prepared_entry['linked_transaction_ids']:
            for linked_id in prepared_entry['linked_transaction_ids']:
                conn.execute(text("""
                    INSERT IGNORE INTO manual_journal_links (id, manual_txn_id, linked_txn_id, created_at)
                    VALUES (:id, :manual_txn_id, :linked_txn_id, :now)
                """), {
                    'id': str(uuid.uuid4()),
                    'manual_txn_id': txn_id,
                    'linked_txn_id': linked_id,
                    'now': now
                })

    return jsonify({'message': 'Manual journal entry created successfully', 'id': txn_id}), 201


@history_bp.route('/api/transactions/manual/<parent_id>', methods=['GET'])
def get_manual_journal(parent_id):
    """Get full data of a manual journal entry by its parent_id."""
    engine = require_db_engine()
    
    with engine.connect() as conn:
        p_row = conn.execute(text("""
            SELECT id, txn_date, description, amount, company_id, mark_id, db_cr
            FROM transactions
            WHERE id = :id AND bank_code = 'MANUAL' AND (parent_id IS NULL OR parent_id = '')
        """), {'id': parent_id}).fetchone()
        
        if not p_row:
            raise NotFoundError('Manual journal parent not found')
            
        parent = serialize_row_values(p_row._mapping)

        c_rows = conn.execute(text("""
            SELECT
                t.id,
                t.description,
                t.amount,
                t.db_cr,
                t.mark_id,
                t.coa_id AS direct_coa_id,
                t.coa_id_coretax AS direct_coa_id_coretax,
                mcm.coa_id AS legacy_coa_id,
                mcm.report_type
            FROM transactions t
            LEFT JOIN mark_coa_mapping mcm
                ON mcm.mark_id = t.mark_id
               AND t.coa_id IS NULL
               AND t.coa_id_coretax IS NULL
               AND UPPER(COALESCE(mcm.mapping_type, '')) = CASE
                    WHEN UPPER(TRIM(COALESCE(t.db_cr, ''))) IN ('CR', 'CREDIT', 'K', 'KREDIT') THEN 'CREDIT'
                    WHEN UPPER(TRIM(COALESCE(t.db_cr, ''))) IN ('DB', 'DEBIT', 'D', 'DE') THEN 'DEBIT'
                    ELSE UPPER(COALESCE(mcm.mapping_type, ''))
               END
            WHERE t.parent_id = :pid
            ORDER BY t.created_at ASC
        """), {'pid': parent_id}).fetchall()
        
        child_rows = []
        child_ids = []
        lines_map = {}
        for row in c_rows:
            d = serialize_row_values(row._mapping)
            tx_id = str(d.get('id') or '')
            if not tx_id:
                continue
            if tx_id not in lines_map:
                child_ids.append(tx_id)
                child_rows.append(d)
                lines_map[tx_id] = {
                    'id': tx_id,
                    'description': d.get('description'),
                    'amount': float(d.get('amount') or 0),
                    'side': 'DEBIT' if _normalize_db_cr(d.get('db_cr')) == 'DB' else 'CREDIT',
                    'coa_id': d.get('direct_coa_id') or None,
                    'coa_id_coretax': d.get('direct_coa_id_coretax') or None,
                }

            report_type = str(d.get('report_type') or 'real').strip().lower()
            legacy_coa_id = d.get('legacy_coa_id')
            if legacy_coa_id:
                if report_type == 'coretax':
                    lines_map[tx_id]['coa_id_coretax'] = lines_map[tx_id]['coa_id_coretax'] or legacy_coa_id
                else:
                    lines_map[tx_id]['coa_id'] = lines_map[tx_id]['coa_id'] or legacy_coa_id

        lines = list(lines_map.values())

        if not parent.get('mark_id') and child_rows:
            unique_mark_ids = {
                str(row.get('mark_id') or '').strip()
                for row in child_rows
                if row.get('mark_id')
            }
            if len(unique_mark_ids) == 1:
                parent['mark_id'] = unique_mark_ids.pop()
                first_child = child_rows[0]
                parent['amount'] = float(first_child.get('amount') or 0)
                parent['db_cr'] = _normalize_db_cr(first_child.get('db_cr'))
            else:
                parent['legacy_multi_line'] = True

        l_rows = conn.execute(text("""
            SELECT t.id, t.txn_date, t.description, t.amount, t.db_cr, t.bank_code
            FROM manual_journal_links mjl
            JOIN transactions t ON mjl.linked_txn_id = t.id
            WHERE mjl.manual_txn_id = :manual_txn_id
            ORDER BY t.txn_date DESC, t.created_at DESC
        """), {'manual_txn_id': parent_id}).fetchall()
        
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
    now = datetime.now()
    
    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        prepared_entry = _prepare_manual_journal_entry(conn, data)

        # 1. Verify and Update Parent
        p_row = conn.execute(text("SELECT id, mark_id FROM transactions WHERE id = :id AND bank_code = 'MANUAL'"), {'id': parent_id}).fetchone()
        if not p_row:
            raise NotFoundError('Manual journal not found')

        # 2. Get old children and their marks to cleanup
        old_rows = conn.execute(text("SELECT id, mark_id FROM transactions WHERE parent_id = :pid"), {'pid': parent_id}).fetchall()
        old_child_ids = [r.id for r in old_rows]
        old_mark_ids = [r.mark_id for r in old_rows if r.mark_id]
        # Cleanup
        conn.execute(text("DELETE FROM transactions WHERE parent_id = :pid"), {'pid': parent_id})
        
        if old_child_ids:
            conn.execute(text("DELETE FROM manual_journal_links WHERE manual_txn_id = :pid OR manual_txn_id IN :child_ids").bindparams(bindparam('child_ids', expanding=True)), 
                         {'pid': parent_id, 'child_ids': old_child_ids})
        else:
            conn.execute(text("DELETE FROM manual_journal_links WHERE manual_txn_id = :pid"), {'pid': parent_id})

        update_fields = {
            'id': parent_id,
            'txn_date': prepared_entry['txn_date'],
            'description': prepared_entry['description'],
            'amount': prepared_entry['amount'],
            'company_id': prepared_entry['company_id'],
            'mark_id': prepared_entry['mark_id'],
            'db_cr': prepared_entry['db_cr'],
            'updated_at': now,
        }
        set_fields = [
            "txn_date = :txn_date",
            "description = :description",
            "amount = :amount",
            "company_id = :company_id",
            "mark_id = :mark_id",
            "db_cr = :db_cr",
        ]
        if 'updated_at' in txn_columns:
            set_fields.append("updated_at = :updated_at")

        conn.execute(text(f"""
            UPDATE transactions 
            SET {', '.join(set_fields)}
            WHERE id = :id
        """), update_fields)
        _insert_manual_journal_lines(conn, parent_id, prepared_entry, txn_columns, now)

        if prepared_entry['linked_transaction_ids']:
            for linked_id in prepared_entry['linked_transaction_ids']:
                conn.execute(text("""
                    INSERT IGNORE INTO manual_journal_links (id, manual_txn_id, linked_txn_id, created_at)
                    VALUES (:id, :manual_txn_id, :linked_txn_id, :now)
                """), {
                    'id': str(uuid.uuid4()),
                    'manual_txn_id': parent_id,
                    'linked_txn_id': linked_id,
                    'now': now
                })

        _delete_orphan_marks(conn, old_mark_ids)

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
    Excludes: MANUAL source transactions and split parents that already have children.
    """
    engine = require_db_engine()

    company_id = request.args.get('company_id')
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    exclude_manual_txn_id = request.args.get('exclude_manual_txn_id')  # exclude already-linked ones

    where_clauses = [
        "(t.source_file IS NULL OR t.source_file != 'MANUAL')",
        "NOT EXISTS (SELECT 1 FROM transactions t_child WHERE t_child.parent_id = t.id)",
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
                   t.bank_code, t.parent_id,
                   pt.description as parent_description,
                   m.internal_report as mark_name,
                   c.name as company_name
            FROM transactions t
            LEFT JOIN transactions pt ON t.parent_id = pt.id
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
            d['is_split_child'] = bool(d.get('parent_id'))
            results.append(d)

        return jsonify({'transactions': results})


@history_bp.route('/api/transactions', methods=['GET'])
def get_transactions():
    engine = require_db_engine()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT t.*, m.internal_report, m.personal_use, m.tax_report,
                   c.name as company_name, c.short_name as company_short_name,
                   mjl.manual_txn_id as linked_manual_id,
                   mt.mark_id as manual_mark_id,
                   mm.internal_report as manual_mark_name
            FROM transactions t
            LEFT JOIN marks m ON t.mark_id = m.id
            LEFT JOIN companies c ON t.company_id = c.id
            LEFT JOIN manual_journal_links mjl ON t.id = mjl.linked_txn_id
            LEFT JOIN transactions mt ON mjl.manual_txn_id = mt.id
            LEFT JOIN marks mm ON mt.mark_id = mm.id
            ORDER BY t.txn_date DESC, t.created_at DESC
        """))
        transactions = serialize_result_rows(result)
        for d in transactions:
            d['db_cr'] = _normalize_db_cr(d.get('db_cr'))
            d['is_linked_to_manual'] = bool(d.get('linked_manual_id'))
            
            if not str(d.get('description') or '').strip():
                fallback_desc = d.get('internal_report') or d.get('personal_use') or d.get('tax_report')
                if fallback_desc:
                    d['description'] = fallback_desc
        return jsonify({'transactions': transactions})


@history_bp.route('/api/transactions/upload-summary', methods=['GET'])
def get_upload_summary():
    engine = require_db_engine()

    with engine.connect() as conn:
        transaction_columns = get_table_columns(conn, 'transactions')
        definition_columns = get_table_columns(conn, 'bank_account_definitions')
        has_bank_account_number = 'bank_account_number' in transaction_columns
        bank_account_number_expr = (
            "MAX(NULLIF(TRIM(t.bank_account_number), ''))"
            if has_bank_account_number else
            "NULL"
        )
        account_variant_count_expr = (
            "COUNT(DISTINCT COALESCE(NULLIF(TRIM(t.bank_account_number), ''), '__EMPTY__'))"
            if has_bank_account_number else
            "0"
        )
        result = conn.execute(text("""
            SELECT t.source_file,
                   COUNT(*) as transaction_count,
                   MIN(t.txn_date) as start_date,
                   MAX(t.txn_date) as end_date,
                   t.bank_code,
                   {bank_account_number_expr} as bank_account_number,
                   {account_variant_count_expr} as account_variant_count,
                   COUNT(DISTINCT t.company_id) as company_count,
                   SUM(CASE WHEN t.db_cr = 'DB' THEN t.amount ELSE 0 END) as total_debit,
                   SUM(CASE WHEN t.db_cr = 'CR' THEN t.amount ELSE 0 END) as total_credit,
                   MAX(t.created_at) as last_upload
            FROM transactions t
            GROUP BY t.source_file, t.bank_code
            ORDER BY last_upload DESC
        """.format(
            bank_account_number_expr=bank_account_number_expr,
            account_variant_count_expr=account_variant_count_expr,
        )))
        summary = serialize_result_rows(result)

        definition_map = {}
        if definition_columns:
            definition_rows = conn.execute(text("""
                SELECT bank_code, account_number, display_name
                FROM bank_account_definitions
            """)).fetchall()
            definition_map = {
                (str(row.bank_code or ''), str(row.account_number or '')): str(row.display_name or '')
                for row in definition_rows
            }

    for item in summary:
        bank_code = str(item.get('bank_code') or '')
        account_number = str(item.get('bank_account_number') or '')
        variant_count = int(item.get('account_variant_count') or 0)
        item['account_variant_count'] = variant_count
        item['is_account_mixed'] = variant_count > 1
        if item['is_account_mixed']:
            item['bank_account_display_name'] = 'Mixed Accounts'
        elif account_number:
            item['bank_account_display_name'] = definition_map.get((bank_code, account_number)) or account_number
        else:
            item['bank_account_display_name'] = None
    return jsonify({'summary': summary})


MONTH_NAMES_ID = [
    '', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
]


def _normalize_bank_account_number(value):
    raw = str(value or '').strip()
    return raw[:100] if raw else ''


def _humanize_bank_code(bank_code):
    return str(bank_code or '').replace('_CC', ' CC')


def _mask_bank_account_number(account_number):
    raw = _normalize_bank_account_number(account_number)
    if not raw:
        return ''
    compact = ''.join(ch for ch in raw if ch.isalnum())
    if len(compact) <= 4:
        return compact or raw
    return f"Acct {compact[-4:]}"


def _build_checklist_column(bank_code, account_number='', display_name=''):
    normalized_bank = str(bank_code or '').strip()
    normalized_account = _normalize_bank_account_number(account_number)
    normalized_name = str(display_name or '').strip()
    key = f"{normalized_bank}::{normalized_account}" if normalized_account else normalized_bank
    label = _humanize_bank_code(normalized_bank)
    if normalized_account:
        label = f"{label} · {normalized_name or _mask_bank_account_number(normalized_account)}"
    return {
        'key': key,
        'label': label,
        'bank_code': normalized_bank,
        'account_number': normalized_account or None,
        'display_name': normalized_name or None,
    }


def _definition_is_active_for_year(active_from, active_until, year):
    year = int(year)
    year_start = f"{year}-01-01"
    year_end = f"{year}-12-31"
    normalized_from = _normalize_iso_date(active_from)
    normalized_until = _normalize_iso_date(active_until)
    if normalized_from and normalized_from > year_end:
        return False
    if normalized_until and normalized_until < year_start:
        return False
    return True


@history_bp.route('/api/bank-account-definitions', methods=['GET'])
def get_bank_account_definitions():
    engine = require_db_engine()
    bank_code_filter = str(request.args.get('bank_code') or '').strip().upper()

    with engine.connect() as conn:
        definition_columns = get_table_columns(conn, 'bank_account_definitions')
        if not definition_columns:
            return jsonify({'definitions': []})
        has_active_period = 'active_from' in definition_columns and 'active_until' in definition_columns
        active_from_select = 'active_from' if has_active_period else 'NULL AS active_from'
        active_until_select = 'active_until' if has_active_period else 'NULL AS active_until'

        query = f"""
            SELECT id, bank_code, account_number, display_name, {active_from_select}, {active_until_select}, created_at, updated_at
            FROM bank_account_definitions
        """
        params = {}
        if bank_code_filter:
            query += " WHERE bank_code = :bank_code"
            params['bank_code'] = bank_code_filter
        query += " ORDER BY bank_code ASC, display_name ASC, account_number ASC"
        rows = conn.execute(text(query), params).fetchall()

    definitions = [
        {
            'id': str(row.id),
            'bank_code': str(row.bank_code or ''),
            'account_number': str(row.account_number or ''),
            'display_name': str(row.display_name or ''),
            'active_from': str(row.active_from)[:10] if row.active_from else None,
            'active_until': str(row.active_until)[:10] if row.active_until else None,
            'created_at': str(row.created_at)[:19] if row.created_at else None,
            'updated_at': str(row.updated_at)[:19] if row.updated_at else None,
        }
        for row in rows
    ]
    return jsonify({'definitions': definitions})


@history_bp.route('/api/bank-account-definitions/candidates', methods=['GET'])
def get_bank_account_definition_candidates():
    engine = require_db_engine()
    bank_code_filter = str(request.args.get('bank_code') or '').strip().upper()

    with engine.connect() as conn:
        transaction_columns = get_table_columns(conn, 'transactions')
        definition_columns = get_table_columns(conn, 'bank_account_definitions')

        if 'bank_account_number' not in transaction_columns:
            return jsonify({'candidates': []})
        if not definition_columns:
            mapped_join = ""
            mapped_filter = ""
        else:
            mapped_join = """
                LEFT JOIN bank_account_definitions bad
                  ON bad.bank_code = t.bank_code
                 AND bad.account_number = t.bank_account_number
            """
            mapped_filter = " AND bad.id IS NULL"

        params = {}
        bank_filter_sql = ""
        if bank_code_filter:
            bank_filter_sql = " AND t.bank_code = :bank_code"
            params['bank_code'] = bank_code_filter

        rows = conn.execute(text(f"""
            SELECT
                t.bank_code,
                t.bank_account_number,
                COUNT(*) AS transaction_count,
                COUNT(DISTINCT t.source_file) AS source_file_count,
                MIN(t.txn_date) AS first_txn_date,
                MAX(t.txn_date) AS last_txn_date,
                MAX(t.created_at) AS last_upload,
                GROUP_CONCAT(DISTINCT t.source_file ORDER BY t.source_file SEPARATOR '||') AS source_files
            FROM transactions t
            {mapped_join}
            WHERE (t.bank_code IS NOT NULL AND t.bank_code <> '' AND t.bank_code <> 'MANUAL')
              AND NULLIF(TRIM(t.bank_account_number), '') IS NOT NULL
              {bank_filter_sql}
              {mapped_filter}
            GROUP BY t.bank_code, t.bank_account_number
            ORDER BY t.bank_code ASC, last_upload DESC, t.bank_account_number ASC
        """), params).fetchall()

    candidates = [
        {
            'bank_code': str(row.bank_code or ''),
            'account_number': str(row.bank_account_number or ''),
            'transaction_count': int(row.transaction_count or 0),
            'source_file_count': int(row.source_file_count or 0),
            'first_txn_date': str(row.first_txn_date)[:10] if row.first_txn_date else None,
            'last_txn_date': str(row.last_txn_date)[:10] if row.last_txn_date else None,
            'last_upload': str(row.last_upload)[:19] if row.last_upload else None,
            'source_files': [value for value in str(row.source_files or '').split('||') if value],
        }
        for row in rows
    ]
    return jsonify({'candidates': candidates})


@history_bp.route('/api/bank-account-definitions', methods=['POST'])
def save_bank_account_definition():
    engine = require_db_engine()
    payload = request.get_json(silent=True) or {}

    bank_code = str(payload.get('bank_code') or '').strip().upper()
    account_number = _normalize_bank_account_number(payload.get('account_number'))
    display_name = str(payload.get('display_name') or '').strip()
    active_from = _normalize_iso_date(payload.get('active_from'))
    active_until = _normalize_iso_date(payload.get('active_until'))

    if not bank_code:
        raise BadRequestError('bank_code is required')
    if not account_number:
        raise BadRequestError('account_number is required')
    if not display_name:
        raise BadRequestError('display_name is required')
    if active_from and active_until and active_until < active_from:
        raise BadRequestError('active_until must be greater than or equal to active_from')

    now = datetime.now()
    with engine.begin() as conn:
        definition_columns = get_table_columns(conn, 'bank_account_definitions')
        if not definition_columns:
            raise BadRequestError('bank_account_definitions table is not available. Run migration 064 first.')
        has_active_period = 'active_from' in definition_columns and 'active_until' in definition_columns

        existing = conn.execute(text("""
            SELECT id
            FROM bank_account_definitions
            WHERE bank_code = :bank_code
              AND account_number = :account_number
            LIMIT 1
        """), {
            'bank_code': bank_code,
            'account_number': account_number,
        }).fetchone()

        if existing:
            definition_id = str(existing.id)
            update_assignments = [
                'display_name = :display_name',
                'updated_at = :updated_at',
            ]
            params = {
                'id': definition_id,
                'display_name': display_name,
                'updated_at': now,
            }
            if has_active_period:
                update_assignments.insert(1, 'active_from = :active_from')
                update_assignments.insert(2, 'active_until = :active_until')
                params['active_from'] = active_from
                params['active_until'] = active_until

            conn.execute(text(f"""
                UPDATE bank_account_definitions
                SET {', '.join(update_assignments)}
                WHERE id = :id
            """), params)
        else:
            definition_id = str(uuid.uuid4())
            insert_columns = ['id', 'bank_code', 'account_number', 'display_name']
            insert_values = [':id', ':bank_code', ':account_number', ':display_name']
            params = {
                'id': definition_id,
                'bank_code': bank_code,
                'account_number': account_number,
                'display_name': display_name,
                'created_at': now,
                'updated_at': now,
            }
            if has_active_period:
                insert_columns.extend(['active_from', 'active_until'])
                insert_values.extend([':active_from', ':active_until'])
                params['active_from'] = active_from
                params['active_until'] = active_until
            insert_columns.extend(['created_at', 'updated_at'])
            insert_values.extend([':created_at', ':updated_at'])

            conn.execute(text(f"""
                INSERT INTO bank_account_definitions (
                    {', '.join(insert_columns)}
                ) VALUES (
                    {', '.join(insert_values)}
                )
            """), params)

    return jsonify({
        'success': True,
        'definition': {
            'id': definition_id,
            'bank_code': bank_code,
            'account_number': account_number,
            'display_name': display_name,
            'active_from': active_from,
            'active_until': active_until,
        }
    })


@history_bp.route('/api/transactions/assign-bank-account', methods=['POST'])
def assign_bank_account_to_uploaded_file():
    engine = require_db_engine()
    payload = request.get_json(silent=True) or {}

    source_file = str(payload.get('source_file') or '').strip()
    bank_code = str(payload.get('bank_code') or '').strip().upper()
    account_number = _normalize_bank_account_number(payload.get('account_number'))

    if not source_file:
        raise BadRequestError('source_file is required')
    if not bank_code:
        raise BadRequestError('bank_code is required')

    with engine.begin() as conn:
        transaction_columns = get_table_columns(conn, 'transactions')
        if 'bank_account_number' not in transaction_columns:
            raise BadRequestError('transactions.bank_account_number is not available. Run migration 064 first.')

        definition_columns = get_table_columns(conn, 'bank_account_definitions')
        if account_number and definition_columns:
            definition = conn.execute(text("""
                SELECT id
                FROM bank_account_definitions
                WHERE bank_code = :bank_code
                  AND account_number = :account_number
                LIMIT 1
            """), {
                'bank_code': bank_code,
                'account_number': account_number,
            }).fetchone()
            if not definition:
                raise BadRequestError('Selected bank account definition was not found for this bank')

        result = conn.execute(text("""
            UPDATE transactions
            SET bank_account_number = :bank_account_number,
                updated_at = :updated_at
            WHERE source_file = :source_file
              AND bank_code = :bank_code
        """), {
            'bank_account_number': account_number or None,
            'updated_at': datetime.now(),
            'source_file': source_file,
            'bank_code': bank_code,
        })

        if result.rowcount == 0:
            raise NotFoundError('No uploaded transactions found for the selected source file and bank')

    return jsonify({
        'success': True,
        'updated_count': int(result.rowcount or 0),
        'source_file': source_file,
        'bank_code': bank_code,
        'account_number': account_number or None,
    })


@history_bp.route('/api/bank-account-definitions/<definition_id>', methods=['DELETE'])
def delete_bank_account_definition(definition_id):
    engine = require_db_engine()

    with engine.begin() as conn:
        if not get_table_columns(conn, 'bank_account_definitions'):
            raise NotFoundError('Bank account definition table is not available')

        result = conn.execute(text("""
            DELETE FROM bank_account_definitions
            WHERE id = :id
        """), {'id': definition_id})
        if result.rowcount == 0:
            raise NotFoundError('Bank account definition not found')

    return jsonify({'success': True})


@history_bp.route('/api/transactions/upload-checklist', methods=['GET'])
def get_upload_checklist():
    """Return a per-month × per-bank-account upload checklist for a given year.

    Query params:
        year (int): The fiscal year to inspect (default: current year).

    Response shape:
    {
        "year": 2025,
        "banks": ["BCA", "DBS", ...],
        "months": [
            {
                "month": 1,
                "label": "Januari",
                "banks": {
                    "BCA": {
                        "uploaded": true,
                        "source_files": ["bca_jan_2025.pdf"],
                        "transaction_count": 52,
                        "total_debit": 12345000.0,
                        "total_credit": 9876000.0,
                        "last_upload": "2025-02-01"
                    },
                    "DBS": {"uploaded": false}
                }
            },
            ...
        ]
    }
    """
    engine = require_db_engine()
    current_year = datetime.now().year
    try:
        year = int(request.args.get('year', current_year))
    except (TypeError, ValueError):
        year = current_year

    with engine.connect() as conn:
        transaction_columns = get_table_columns(conn, 'transactions')
        definition_columns = get_table_columns(conn, 'bank_account_definitions')
        has_bank_account_number = 'bank_account_number' in transaction_columns
        has_definition_table = bool(definition_columns)
        has_definition_active_period = 'active_from' in definition_columns and 'active_until' in definition_columns

        bank_account_number_expr = (
            "NULLIF(TRIM(t.bank_account_number), '')"
            if has_bank_account_number else
            "NULL"
        )
        definition_name_expr = (
            "NULLIF(TRIM(bad.display_name), '')"
            if has_definition_table and has_bank_account_number else
            "NULL"
        )
        definition_join_sql = (
            """
            LEFT JOIN bank_account_definitions bad
              ON bad.bank_code = t.bank_code
             AND bad.account_number = t.bank_account_number
            """
            if has_definition_table and has_bank_account_number else
            ""
        )

        rows = conn.execute(text(f"""
            SELECT
                MONTH(t.txn_date)                                        AS txn_month,
                t.bank_code,
                {bank_account_number_expr}                               AS bank_account_number,
                {definition_name_expr}                                   AS account_definition_name,
                GROUP_CONCAT(DISTINCT t.source_file ORDER BY t.source_file SEPARATOR '||') AS source_files,
                COUNT(*)                                                  AS transaction_count,
                SUM(CASE WHEN t.db_cr = 'DB' THEN t.amount ELSE 0 END)  AS total_debit,
                SUM(CASE WHEN t.db_cr = 'CR' THEN t.amount ELSE 0 END)  AS total_credit,
                MAX(t.created_at)                                         AS last_upload
            FROM transactions t
            {definition_join_sql}
            WHERE YEAR(t.txn_date) = :year
              AND (t.bank_code IS NULL OR t.bank_code != 'MANUAL')
              AND (t.parent_id IS NULL OR t.parent_id = '')
            GROUP BY MONTH(t.txn_date), t.bank_code, bank_account_number, account_definition_name
            ORDER BY txn_month ASC, t.bank_code ASC, account_definition_name ASC, bank_account_number ASC
        """), {'year': year}).fetchall()

        definitions = []
        if has_definition_table:
            if has_definition_active_period:
                definitions = conn.execute(text("""
                    SELECT bank_code, account_number, display_name, active_from, active_until
                    FROM bank_account_definitions
                    WHERE (active_from IS NULL OR active_from <= :year_end)
                      AND (active_until IS NULL OR active_until >= :year_start)
                    ORDER BY bank_code ASC, display_name ASC, account_number ASC
                """), {
                    'year_start': f'{year}-01-01',
                    'year_end': f'{year}-12-31',
                }).fetchall()
            else:
                definitions = conn.execute(text("""
                    SELECT bank_code, account_number, display_name, NULL AS active_from, NULL AS active_until
                    FROM bank_account_definitions
                    ORDER BY bank_code ASC, display_name ASC, account_number ASC
                """)).fetchall()

    columns_map = {}
    for definition in definitions:
        bank_code = str(definition.bank_code or '').strip()
        account_number = _normalize_bank_account_number(definition.account_number)
        display_name = str(definition.display_name or '').strip()
        if not _definition_is_active_for_year(definition.active_from, definition.active_until, year):
            continue
        if not bank_code or not account_number:
            continue
        column = _build_checklist_column(bank_code, account_number, display_name)
        columns_map[column['key']] = column

    cell_map = {}
    for row in rows:
        month = int(row.txn_month or 0)
        bank = str(row.bank_code or '')
        account_number = _normalize_bank_account_number(getattr(row, 'bank_account_number', ''))
        display_name = str(getattr(row, 'account_definition_name', '') or '').strip()
        if not month or not bank:
            continue

        column = _build_checklist_column(bank, account_number, display_name)
        columns_map.setdefault(column['key'], column)

        raw_files = str(row.source_files or '')
        source_files = [f for f in raw_files.split('||') if f and f != 'MANUAL']
        last_upload_raw = row.last_upload
        last_upload_str = str(last_upload_raw)[:10] if last_upload_raw else None
        cell_map[(month, column['key'])] = {
            'uploaded': True,
            'source_files': source_files,
            'transaction_count': int(row.transaction_count or 0),
            'total_debit': float(row.total_debit or 0),
            'total_credit': float(row.total_credit or 0),
            'last_upload': last_upload_str,
        }

    banks_with_account_columns = {
        column['bank_code']
        for column in columns_map.values()
        if column.get('account_number')
    }
    for column in columns_map.values():
        if not column.get('account_number') and column.get('bank_code') in banks_with_account_columns:
            column['label'] = f"{_humanize_bank_code(column.get('bank_code'))} · Unmapped"

    columns = sorted(
        columns_map.values(),
        key=lambda column: (
            str(column.get('bank_code') or '').lower(),
            0 if column.get('account_number') else 1,
            str(column.get('display_name') or '').lower(),
            str(column.get('account_number') or ''),
            str(column.get('key') or ''),
        )
    )

    months_data = []
    for m in range(1, 13):
        bank_cells = {}
        for column in columns:
            cell = cell_map.get((m, column['key']))
            bank_cells[column['key']] = cell if cell else {'uploaded': False}
        months_data.append({
            'month': m,
            'label': MONTH_NAMES_ID[m],
            'banks': bank_cells,
        })

    return jsonify({
        'year': year,
        'banks': [column['key'] for column in columns],
        'columns': columns,
        'months': months_data,
    })


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
            
        where_sql = ' AND '.join(where_clauses)
        
        # Get parent/top-level IDs and marks before deletion
        ids_result = conn.execute(text(f"SELECT id, mark_id FROM transactions WHERE {where_sql}"), params).fetchall()
        if not ids_result:
            return jsonify({'message': 'Deleted 0 transactions'})
            
        txn_ids = [r.id for r in ids_result]
        mark_ids = [r.mark_id for r in ids_result if r.mark_id]
        
        # Fetch children (splits) that belong to these parents, since they don't have source_file set
        child_ids_result = conn.execute(
            text("SELECT id, mark_id FROM transactions WHERE parent_id IN :pids").bindparams(bindparam('pids', expanding=True)),
            {'pids': txn_ids}
        ).fetchall()
        
        child_ids = [r.id for r in child_ids_result]
        child_mark_ids = [r.mark_id for r in child_ids_result if r.mark_id]
        
        all_txn_ids = list(set(txn_ids + child_ids))
        all_mark_ids = list(set(mark_ids + child_mark_ids))
        
        # 1. Clean up manual journal links first
        if all_txn_ids:
            conn.execute(
                text("DELETE FROM manual_journal_links WHERE manual_txn_id IN :ids OR linked_txn_id IN :ids OR child_txn_id IN :ids")
                .bindparams(bindparam('ids', expanding=True)),
                {'ids': all_txn_ids}
            )

        # 2. Delete child transactions first to satisfy `fk_transactions_parent_id` constraint
        if child_ids:
            conn.execute(
                text("DELETE FROM transactions WHERE id IN :child_ids")
                .bindparams(bindparam('child_ids', expanding=True)),
                {'child_ids': child_ids}
            )
        
        # 3. Delete parent (or all remaining) transactions
        result = conn.execute(text(f"DELETE FROM transactions WHERE {where_sql}"), params)
        
        # 4. Clean up orphaned marks securely
        if all_mark_ids:
            used_marks = conn.execute(
                text("SELECT DISTINCT mark_id FROM transactions WHERE mark_id IN :mids")
                .bindparams(bindparam('mids', expanding=True)),
                {'mids': all_mark_ids}
            ).fetchall()
            used_mark_ids = {r.mark_id for r in used_marks if r.mark_id}
            
            marks_to_delete = list(set(all_mark_ids) - used_mark_ids)
            if marks_to_delete:
                conn.execute(
                    text("DELETE FROM mark_coa_mapping WHERE mark_id IN :mids")
                    .bindparams(bindparam('mids', expanding=True)),
                    {'mids': marks_to_delete}
                )
                conn.execute(
                    text("DELETE FROM marks WHERE id IN :mids")
                    .bindparams(bindparam('mids', expanding=True)),
                    {'mids': marks_to_delete}
                )

        return jsonify({'message': f'Deleted {len(all_txn_ids)} transactions'})


@history_bp.route('/api/transactions/<txn_id>/assign-mark', methods=['POST'])
def assign_mark_transaction(txn_id):
    engine = require_db_engine()

    data = request.json or {}
    mark_id = data.get('mark_id')
    now = datetime.now()
    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        linked_to_manual = conn.execute(text("""
            SELECT 1
            FROM manual_journal_links
            WHERE linked_txn_id = :txn_id
            LIMIT 1
        """), {'txn_id': txn_id}).fetchone()
        if linked_to_manual:
            raise BadRequestError(
                'Transaksi ini sudah menjadi referensi manual journal. Ubah dari manual journal agar tidak terjadi double accounting.'
            )

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

        linked_rows = conn.execute(text("""
            SELECT DISTINCT linked_txn_id
            FROM manual_journal_links
            WHERE linked_txn_id IN :ids
        """).bindparams(bindparam('ids', expanding=True)), {'ids': updatable_ids}).fetchall()
        linked_ids = [str(row.linked_txn_id) for row in linked_rows if getattr(row, 'linked_txn_id', None)]
        if linked_ids:
            linked_set = set(linked_ids)
            blocked_ids.extend(linked_ids)
            updatable_ids = [current_id for current_id in updatable_ids if str(current_id) not in linked_set]

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
        # 1. Collect child transactions / marks if this is a parent (manual journal or split)
        child_rows = conn.execute(
            text("SELECT id, mark_id FROM transactions WHERE parent_id = :id"),
            {'id': txn_id}
        ).fetchall()
        child_ids = [r.id for r in child_rows]
        child_mark_ids = [r.mark_id for r in child_rows if r.mark_id]

        # Delete children
        conn.execute(
            text("DELETE FROM transactions WHERE parent_id = :id"),
            {'id': txn_id}
        )

        # 2. Handle own mark/mapping if exists
        # 3. Handle manual_journal_links (both as parent or linked item)
        manual_link_ids = [txn_id] + child_ids
        conn.execute(
            text("DELETE FROM manual_journal_links WHERE manual_txn_id IN :ids OR linked_txn_id IN :ids")
            .bindparams(bindparam('ids', expanding=True)),
            {'ids': manual_link_ids}
        )

        # 4. Handle HPP batch links
        conn.execute(
            text("DELETE FROM hpp_batch_transactions WHERE transaction_id = :id"),
            {'id': txn_id}
        )

        # 5. Finally delete the transaction itself
        result = conn.execute(text("DELETE FROM transactions WHERE id = :id"), {'id': txn_id})
        if int(result.rowcount or 0) == 0:
            raise NotFoundError('Transaction not found')

        _delete_orphan_marks(conn, child_mark_ids)

    return jsonify({'message': 'Transaction and all related records deleted successfully'})


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
