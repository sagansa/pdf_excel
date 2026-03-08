import uuid
from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.errors import BadRequestError, ConflictError, NotFoundError
from backend.routes.accounting_utils import require_db_engine
from backend.routes.amortization_helpers import (
    build_manual_item_payload,
    build_registered_asset_payload,
    load_amortization_defaults,
)
from backend.routes.amortization_queries import (
    amortization_assets_query,
    amortization_items_query,
    amortization_settings_query,
    coa_id_by_code_query,
    existing_manual_journal_query,
    first_company_query,
    insert_amortization_item_query,
    insert_mark_coa_mapping_query,
    insert_mark_query,
    insert_transaction_query,
    manual_amortization_items_query,
    update_amortization_item_query,
    delete_amortization_item_query,
)

amortization_item_bp = Blueprint('amortization_item_bp', __name__)

@amortization_item_bp.route('/api/reports/amortization-items', methods=['GET'])
@amortization_item_bp.route('/api/amortization-items', methods=['GET'])
def get_amortization_items():
    """Retrieve amortization items for a company and year"""
    engine = require_db_engine()
    year = request.args.get('year') or datetime.now().year
    company_id = request.args.get('company_id')

    if not company_id:
        # Fallback for testing: get first company
        with engine.connect() as conn:
            first_comp = conn.execute(first_company_query()).fetchone()
            if first_comp:
                company_id = first_comp[0]
            else:
                raise BadRequestError('company_id is required')

    with engine.connect() as conn:
        settings_rows = conn.execute(amortization_settings_query(), {'company_id': company_id}).fetchall()
        defaults = load_amortization_defaults(settings_rows)
        default_rate = defaults['default_rate']
        default_life = defaults['default_life']
        allow_partial_year = defaults['allow_partial_year']

        items_result = conn.execute(amortization_items_query(), {'company_id': company_id, 'year': year})
        items = []
        manual_total_amort = 0
        automatic_total_amort = 0
        total_amount = 0

        for row in items_result:
            item_payload, annual_amortization = build_manual_item_payload(row._mapping, int(year), allow_partial_year)
            if not item_payload:
                continue
            items.append(item_payload)
            total_amount += float(item_payload.get('amount', 0))
            manual_total_amort += annual_amortization

        assets_result = conn.execute(amortization_assets_query(), {'company_id': company_id})

        for row in assets_result:
            asset_payload, current_year_amort, base_amount = build_registered_asset_payload(
                row._mapping, int(year), default_rate, default_life, allow_partial_year
            )
            items.append(asset_payload)
            total_amount += base_amount
            automatic_total_amort += current_year_amort

        return jsonify({
            'items': items,
            'totalAmount': total_amount,
            'manual_total': manual_total_amort,
            'calculated_total': automatic_total_amort,
            'grand_total': manual_total_amort + automatic_total_amort,
            'settings': {}
        })


@amortization_item_bp.route('/api/amortization-items/generate-journal', methods=['POST'])
def generate_manual_amortization_journal():
    """Generate journal entries for manual amortization items using mark-based approach"""
    data = request.json or {}
    company_id = data.get('company_id')
    year = data.get('year')

    if not company_id or not year:
        raise BadRequestError('company_id and year are required')

    engine = require_db_engine()
    with engine.begin() as conn:
        manual_rows = conn.execute(manual_amortization_items_query(), {
            'company_id': company_id,
            'year': year
        }).fetchall()

        existing_result = conn.execute(existing_manual_journal_query(), {
            'company_id': company_id,
            'year': year
        }).fetchone()

        if existing_result and existing_result.count > 0:
            raise ConflictError(
                'Journal entries already exist for manual amortization items',
                payload={'existing_count': existing_result.count},
            )

        accumulated_coa_codes = {
            'Tangible': '1530',
            'Intangible': '1601',
            'Building': '1524',
            'LandRights': '1534'
        }

        coa_ids = {}
        expense_row = conn.execute(coa_id_by_code_query(), {'code': '5314'}).fetchone()
        if not expense_row:
            raise NotFoundError('COA 5314 for amortization expense not found')
        expense_coa_id = expense_row[0]

        for asset_type, coa_code in accumulated_coa_codes.items():
            coa_result = conn.execute(coa_id_by_code_query(), {'code': coa_code}).fetchone()
            if coa_result:
                coa_ids[asset_type] = coa_result[0]

        journal_count = 0
        for row in manual_rows:
            d = row._mapping
            amount = float(d['amount'])
            asset_type = d.get('asset_type', 'Tangible')

            debit_mark_id = str(uuid.uuid4())
            debit_mark_name = f"Manual Amortization-Debit-{d['id'][:8]}"

            conn.execute(insert_mark_query(), {
                'id': debit_mark_id,
                'name': debit_mark_name
            })

            credit_mark_id = str(uuid.uuid4())
            credit_mark_name = f"Manual Amortization-Credit-{d['id'][:8]}"

            conn.execute(insert_mark_query(), {
                'id': credit_mark_id,
                'name': credit_mark_name
            })

            conn.execute(insert_mark_coa_mapping_query(), {
                'id': str(uuid.uuid4()),
                'mark_id': debit_mark_id,
                'coa_id': expense_coa_id,
                'mapping_type': 'DEBIT',
            })

            if asset_type in coa_ids:
                conn.execute(insert_mark_coa_mapping_query(), {
                    'id': str(uuid.uuid4()),
                    'mark_id': credit_mark_id,
                    'coa_id': coa_ids[asset_type],
                    'mapping_type': 'CREDIT',
                })

            txn_date = d.get('amortization_date', f'{year}-12-31')
            description = f"Manual Amortization - {d['description']}"

            debit_txn_id = str(uuid.uuid4())
            conn.execute(insert_transaction_query(), {
                'id': debit_txn_id,
                'date': txn_date,
                'desc': description,
                'amount': amount,
                'db_cr': 'DB',
                'mark_id': debit_mark_id,
                'company_id': company_id,
                'source': 'manual_amortization_journal'
            })

            if asset_type in coa_ids:
                credit_txn_id = str(uuid.uuid4())
                conn.execute(insert_transaction_query(), {
                    'id': credit_txn_id,
                    'date': txn_date,
                    'desc': description,
                    'amount': amount,
                    'db_cr': 'CR',
                    'mark_id': credit_mark_id,
                    'company_id': company_id,
                    'source': 'manual_amortization_journal'
                })

            journal_count += 1

        return jsonify({
            'message': f'Successfully generated {journal_count} journal entries',
            'journal_count': journal_count,
            'items_processed': len(manual_rows)
        }), 201


@amortization_item_bp.route('/api/amortization-items', methods=['POST'])
def create_amortization_item():
    """Create a new amortization item"""
    data = request.json or {}
    if not data.get('company_id') or not data.get('year') or not data.get('description'):
        raise BadRequestError('company_id, year, and description are required')

    engine = require_db_engine()
    with engine.begin() as conn:
        item_id = str(uuid.uuid4())
        conn.execute(insert_amortization_item_query(), {
            'id': item_id,
            'company_id': data.get('company_id'),
            'year': data.get('year'),
            'mark_id': data.get('mark_id'),
            'description': data.get('description'),
            'amount': data.get('amount'),
            'amortization_date': data.get('amortization_date'),
            'asset_group_id': data.get('asset_group_id'),
            'use_half_rate': data.get('use_half_rate', False),
            'notes': data.get('notes'),
            'is_manual': data.get('is_manual', True)
        })

    return jsonify({**data, 'id': item_id}), 201

@amortization_item_bp.route('/api/amortization-items/<item_id>', methods=['PUT'])
def update_amortization_item(item_id):
    """Update an amortization item"""
    data = request.json or {}
    engine = require_db_engine()
    with engine.begin() as conn:
        result = conn.execute(update_amortization_item_query(), {
            'id': item_id,
            'mark_id': data.get('mark_id'),
            'description': data.get('description'),
            'amount': data.get('amount'),
            'amortization_date': data.get('amortization_date'),
            'asset_group_id': data.get('asset_group_id'),
            'use_half_rate': data.get('use_half_rate'),
            'notes': data.get('notes')
        })

    if result.rowcount == 0:
        raise NotFoundError('Amortization item not found')
    return jsonify({'id': item_id, **data})

@amortization_item_bp.route('/api/amortization-items/<item_id>', methods=['DELETE'])
def delete_amortization_item(item_id):
    """Delete an amortization item"""
    engine = require_db_engine()
    with engine.begin() as conn:
        result = conn.execute(delete_amortization_item_query(), {'id': item_id})

    if result.rowcount == 0:
        raise NotFoundError('Amortization item not found')
    return jsonify({'success': True})
