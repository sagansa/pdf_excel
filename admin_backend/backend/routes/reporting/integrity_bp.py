"""Route integritas akuntansi (Fase 2): cek kontinuitas saldo & trial balance.

- GET  /api/reports/balance-check      → analisis per akun bank (on-the-fly)
- GET  /api/reports/trial-balance      → opening + mutasi = closing per COA
- GET  /api/reports/opening-balances   → set saldo awal (company × tahun)
- PUT  /api/reports/opening-balances   → simpan (validasi D=C & COA ada)
"""

import logging

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from backend.errors import BadRequestError
from backend.routes.accounting_utils import require_db_engine
from backend.services.reporting.balance_continuity import check_balance_continuity
from backend.services.reporting.trial_balance import (
    build_trial_balance,
    save_opening_balances,
)

logger = logging.getLogger(__name__)

integrity_bp = Blueprint('integrity_bp', __name__)


@integrity_bp.route('/api/reports/balance-check', methods=['GET'])
def get_balance_check():
    engine = require_db_engine()
    result = check_balance_continuity(engine)
    accounts = result['accounts']
    return jsonify({
        'success': True,
        'data': {
            'accounts': accounts,
            'accounts_total': len(accounts),
            'accounts_with_breaks': sum(1 for a in accounts if a['breaks']),
            'total_breaks': sum(len(a['breaks']) for a in accounts),
        },
    })


@integrity_bp.route('/api/reports/trial-balance', methods=['GET'])
def get_trial_balance():
    engine = require_db_engine()
    company_id = (request.args.get('company_id') or '').strip() or None
    year_raw = (request.args.get('year') or '').strip()
    report_type = (request.args.get('report_type') or 'real').strip()

    try:
        year = int(year_raw) if year_raw else None
    except ValueError:
        raise BadRequestError(f'Invalid year "{year_raw}".')

    result = build_trial_balance(engine, company_id=company_id, year=year, report_type=report_type)
    return jsonify({'success': True, 'data': result})


@integrity_bp.route('/api/reports/opening-balances', methods=['GET'])
def get_opening_balances():
    engine = require_db_engine()
    company_id = (request.args.get('company_id') or '').strip() or None
    year_raw = (request.args.get('year') or '').strip()

    try:
        year = int(year_raw) if year_raw else None
    except ValueError:
        raise BadRequestError(f'Invalid year "{year_raw}".')

    company_filter = 'AND ob.company_id IS :company_id' if company_id else ''
    year_filter = 'AND ob.period_year = :year' if year else ''
    params = {'company_id': company_id, 'year': year}

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT ob.coa_id, coa.code AS coa_code, coa.name AS coa_name,
                   coa.category AS coa_category, ob.period_year,
                   ob.opening_debit, ob.opening_credit, ob.updated_at
            FROM opening_balances ob
            JOIN chart_of_accounts coa ON coa.id = ob.coa_id
            WHERE 1=1 {company_filter} {year_filter}
            ORDER BY coa.code
        """), params).fetchall()

    entries = [
        {
            'coa_id': row.coa_id,
            'coa_code': row.coa_code,
            'coa_name': row.coa_name,
            'coa_category': row.coa_category,
            'period_year': row.period_year,
            'opening_debit': float(row.opening_debit or 0),
            'opening_credit': float(row.opening_credit or 0),
            'updated_at': str(row.updated_at) if row.updated_at else None,
        }
        for row in rows
    ]
    return jsonify({'success': True, 'data': entries})


@integrity_bp.route('/api/reports/opening-balances', methods=['PUT'])
def put_opening_balances():
    engine = require_db_engine()
    payload = request.get_json(silent=True) or {}
    company_id = (payload.get('company_id') or '').strip() or None
    year = payload.get('year')
    entries = payload.get('entries')

    if not year:
        raise BadRequestError('year wajib diisi.')
    if not isinstance(entries, list):
        raise BadRequestError('entries harus berupa list.')

    try:
        save_opening_balances(engine, company_id=company_id, year=year, entries=entries)
    except ValueError as exc:
        raise BadRequestError(str(exc))

    return jsonify({'success': True, 'data': {'saved': len(entries), 'year': int(year)}})
