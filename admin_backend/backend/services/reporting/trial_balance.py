"""Trial balance: saldo awal + mutasi periode = saldo akhir per akun COA.

Mutasi periode memakai query GL yang sama dengan laporan lain (mark → COA
mapping, report_type real/coretax) supaya angkanya konsisten dengan GL dan
income statement. Saldo awal disimpan per company × tahun di tabel
opening_balances (migrasi 075) dan divalidasi debit = kredit saat disimpan.

Catatan jujur: transaksi bank statement ter-map ke satu COA (mark), jadi
mutasi periode tidak dengan sendirinya D=C — kolom `is_balanced` /
`unbalanced_amount` justru alat untuk melihat selisih yang perlu jurnal
penyeimbang.
"""

import logging
from datetime import datetime

from sqlalchemy import text

from backend.routes.reporting.general_ledger_helpers import (
    coretax_filter_clause,
    mark_coa_join_clause,
)
from backend.routes.reporting.general_ledger_queries import (
    build_general_ledger_summary_query,
)

logger = logging.getLogger(__name__)

BALANCE_TOLERANCE = 0.01


def build_trial_balance(engine, company_id=None, year=None, report_type='real'):
    """Susun trial balance satu tahun: opening + mutasi = closing per COA."""
    year = int(year or datetime.now().year)
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'

    company_filter = ''
    params = {'start_date': start_date, 'end_date': end_date}
    if company_id:
        company_filter = 'AND t.company_id = :company_id'
        params['company_id'] = company_id

    with engine.connect() as conn:
        movements = conn.execute(
            build_general_ledger_summary_query(
                conn=conn,
                mark_coa_join=mark_coa_join_clause(
                    conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='LEFT',
                ),
                company_filter=company_filter,
                coretax_filter=coretax_filter_clause(conn, report_type, 'm'),
                report_type=report_type,
            ),
            params,
        ).fetchall()

        opening_filter = 'AND ob.company_id IS :company_id' if company_id else ''
        opening_params = {'year': year}
        if company_id:
            opening_params['company_id'] = company_id
        openings = conn.execute(text(f"""
            SELECT ob.coa_id, coa.code, coa.name, coa.category,
                   SUM(ob.opening_debit) AS opening_debit,
                   SUM(ob.opening_credit) AS opening_credit
            FROM opening_balances ob
            JOIN chart_of_accounts coa ON coa.id = ob.coa_id
            WHERE ob.period_year = :year {opening_filter}
            GROUP BY ob.coa_id, coa.code, coa.name, coa.category
        """), opening_params).fetchall()

        # GL summary dikelompokkan per code — petakan balik ke id COA supaya
        # tiap baris TB selalu membawa coa_id.
        coa_id_by_code = {
            row.code: row.id for row in conn.execute(text(
                'SELECT id, code FROM chart_of_accounts'
            )).fetchall()
        }

    rows_by_code = {}

    for opening in openings:
        rows_by_code[opening.code] = {
            'coa_id': opening.coa_id,
            'coa_code': opening.code,
            'coa_name': opening.name,
            'coa_category': opening.category,
            'opening_debit': float(opening.opening_debit or 0),
            'opening_credit': float(opening.opening_credit or 0),
            'period_debit': 0.0,
            'period_credit': 0.0,
        }

    for movement in movements:
        row = rows_by_code.get(movement.coa_code)
        if row is None:
            row = {
                'coa_id': coa_id_by_code.get(movement.coa_code),
                'coa_code': movement.coa_code,
                'coa_name': movement.coa_name,
                'coa_category': movement.coa_category,
                'opening_debit': 0.0,
                'opening_credit': 0.0,
                'period_debit': 0.0,
                'period_credit': 0.0,
            }
            rows_by_code[movement.coa_code] = row
        row['period_debit'] = float(movement.total_debit or 0)
        row['period_credit'] = float(movement.total_credit or 0)

    rows = sorted(rows_by_code.values(), key=lambda row: row['coa_code'])
    totals = {
        'opening_debit': 0.0, 'opening_credit': 0.0,
        'period_debit': 0.0, 'period_credit': 0.0,
        'closing_debit': 0.0, 'closing_credit': 0.0,
    }
    for row in rows:
        opening_net = row['opening_debit'] - row['opening_credit']
        closing_net = opening_net + row['period_debit'] - row['period_credit']
        row['closing_debit'] = closing_net if closing_net > BALANCE_TOLERANCE else 0.0
        row['closing_credit'] = -closing_net if closing_net < -BALANCE_TOLERANCE else 0.0
        for key in totals:
            totals[key] += row[key]

    return {
        'year': year,
        'company_id': company_id,
        'report_type': report_type,
        'rows': rows,
        'totals': totals,
        'is_balanced': abs(totals['closing_debit'] - totals['closing_credit']) <= BALANCE_TOLERANCE,
        'unbalanced_amount': round(
            totals['closing_debit'] - totals['closing_credit'], 2,
        ),
    }


def save_opening_balances(engine, company_id, year, entries):
    """Ganti seluruh set saldo awal (company × tahun). Validasi D=C & COA ada.

    entries: list of {coa_id, opening_debit, opening_credit}.
    Raise ValueError dengan pesan jelas bila tidak valid.
    """
    year = int(year)
    total_debit = sum(float(entry.get('opening_debit') or 0) for entry in entries)
    total_credit = sum(float(entry.get('opening_credit') or 0) for entry in entries)
    if abs(total_debit - total_credit) > BALANCE_TOLERANCE:
        raise ValueError(
            f'Saldo awal tidak seimbang: debit {total_debit:,.2f} vs '
            f'kredit {total_credit:,.2f} (selisih {total_debit - total_credit:,.2f}).'
        )

    non_zero = [
        entry for entry in entries
        if abs(float(entry.get('opening_debit') or 0)) > BALANCE_TOLERANCE
        or abs(float(entry.get('opening_credit') or 0)) > BALANCE_TOLERANCE
    ]

    coa_ids = {entry.get('coa_id') for entry in non_zero}
    if coa_ids:
        with engine.connect() as conn:
            placeholders = ', '.join(f':coa_{i}' for i in range(len(coa_ids)))
            found = {
                row[0] for row in conn.execute(text(
                    f'SELECT id FROM chart_of_accounts WHERE id IN ({placeholders})'
                ), {f'coa_{i}': value for i, value in enumerate(sorted(coa_ids))}).fetchall()
            }
        missing = coa_ids - found
        if missing:
            raise ValueError(f'COA tidak ditemukan: {", ".join(sorted(missing))}')

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with engine.begin() as conn:
        delete_filter = 'AND company_id IS :company_id' if company_id else 'AND company_id IS NULL'
        conn.execute(text(
            f'DELETE FROM opening_balances WHERE period_year = :year {delete_filter}'
        ), {'year': year, 'company_id': company_id})
        for entry in non_zero:
            conn.execute(text(
                'INSERT INTO opening_balances '
                '(company_id, coa_id, period_year, opening_debit, opening_credit, updated_at) '
                'VALUES (:company_id, :coa_id, :year, :debit, :credit, :updated_at)'
            ), {
                'company_id': company_id,
                'coa_id': entry.get('coa_id'),
                'year': year,
                'debit': float(entry.get('opening_debit') or 0),
                'credit': float(entry.get('opening_credit') or 0),
                'updated_at': now,
            })
