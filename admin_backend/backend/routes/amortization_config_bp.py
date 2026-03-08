import uuid
from flask import Blueprint, request, jsonify
from backend.errors import BadRequestError, NotFoundError
from backend.routes.accounting_utils import require_db_engine, serialize_result_rows
from backend.routes.amortization_config_helpers import (
    DEFAULT_AMORTIZATION_SETTINGS,
    build_settings_to_save,
    merge_asset_groups,
    merge_settings_payload,
    parse_amortization_settings,
    serialize_mapping_row,
)
from backend.routes.amortization_config_queries import (
    amortization_asset_groups_query,
    amortization_coa_codes_query,
    amortization_eligible_marks_query,
    amortization_settings_query,
    delete_mark_amortization_mapping_query,
    insert_amortization_asset_group_query,
    insert_amortization_settings_query,
    insert_mark_amortization_mapping_query,
    mark_amortization_config_query,
    mark_amortization_mappings_query,
    update_amortization_asset_group_query,
    update_amortization_settings_query,
    update_mark_amortization_mapping_query,
)

amortization_config_bp = Blueprint('amortization_config_bp', __name__)

@amortization_config_bp.route('/api/amortization/asset-groups', methods=['GET'])
def get_amortization_asset_groups():
    """Retrieve amortization asset groups"""
    engine = require_db_engine()
    company_id = request.args.get('company_id')
    asset_type = request.args.get('asset_type')

    with engine.connect() as conn:
        query_params = {}
        conditions = []

        if company_id:
            conditions.append("(company_id = :company_id OR company_id IS NULL)")
            query_params['company_id'] = company_id
        else:
            conditions.append("company_id IS NULL")

        if asset_type:
            conditions.append("asset_type = :asset_type")
            query_params['asset_type'] = asset_type

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        result = conn.execute(
            amortization_asset_groups_query(where_clause, include_company_order=bool(company_id)),
            query_params,
        )
        groups = merge_asset_groups(result, company_id)
        return jsonify({'groups': groups})

@amortization_config_bp.route('/api/amortization/asset-groups', methods=['POST'])
def create_amortization_asset_group():
    """Create a new amortization asset group"""
    data = request.json or {}
    if not data.get('group_name') or data.get('group_number') is None or not data.get('asset_type'):
        raise BadRequestError('group_name, group_number, and asset_type are required')

    engine = require_db_engine()
    group_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            insert_amortization_asset_group_query(),
            {
                'id': group_id,
                'company_id': data.get('company_id'),
                'group_name': data.get('group_name'),
                'group_number': data.get('group_number'),
                'asset_type': data.get('asset_type'),
                'tarif_rate': data.get('tarif_rate'),
                'tarif_half_rate': data.get('tarif_half_rate'),
                'useful_life_years': data.get('useful_life_years')
            }
        )

    return jsonify({**data, 'id': group_id}), 201

@amortization_config_bp.route('/api/amortization/asset-groups/<group_id>', methods=['PUT'])
def update_amortization_asset_group(group_id):
    """Update an amortization asset group"""
    data = request.json or {}
    engine = require_db_engine()
    with engine.begin() as conn:
        result = conn.execute(update_amortization_asset_group_query(), {
            'id': group_id,
            'group_name': data.get('group_name'),
            'group_number': data.get('group_number'),
            'asset_type': data.get('asset_type'),
            'tarif_rate': data.get('tarif_rate'),
            'tarif_half_rate': data.get('tarif_half_rate'),
            'useful_life_years': data.get('useful_life_years')
        })

    if result.rowcount == 0:
        raise NotFoundError('Amortization asset group not found')
    return jsonify({'success': True})

@amortization_config_bp.route('/api/amortization-coa-codes', methods=['GET'])
def get_amortization_coa_codes():
    """Retrieve COA codes that can be used for amortization"""
    engine = require_db_engine()
    with engine.connect() as conn:
        result = conn.execute(amortization_coa_codes_query())
        coa_rows = serialize_result_rows(result)
        coa_codes = []
        coa_details = []
        for d in coa_rows:
            coa_codes.append(d['code'])
            coa_details.append(d)

        return jsonify({
            'coa_codes': coa_codes,
            'coa_details': coa_details
        })

@amortization_config_bp.route('/api/amortization-settings', methods=['GET'])
@amortization_config_bp.route('/api/amortization/settings', methods=['GET'])
@amortization_config_bp.route('/api/amortization/mark-settings', methods=['GET'])
def get_amortization_settings():
    """Retrieve amortization settings for a company"""
    engine = require_db_engine()
    company_id = request.args.get('company_id')

    with engine.connect() as conn:
        result = conn.execute(amortization_settings_query(), {'company_id': company_id}).fetchall()
        settings = parse_amortization_settings(result)
        return jsonify({
            'settings': settings,
            'available_marks': []
        })

@amortization_config_bp.route('/api/amortization-settings', methods=['POST'])
@amortization_config_bp.route('/api/amortization/settings', methods=['POST'])
@amortization_config_bp.route('/api/amortization/mark-settings', methods=['POST'])
def save_amortization_settings():
    """Save amortization settings for a company"""
    data = request.json or {}
    engine = require_db_engine()
    company_id = (data.get('company_id') or '').strip() or None

    with engine.begin() as conn:
        rows = conn.execute(amortization_settings_query(), {'company_id': company_id}).fetchall()
        merged_settings = merge_settings_payload(rows, data)
        settings_to_save = build_settings_to_save(merged_settings)

        for name, val, typ in settings_to_save:
            update_result = conn.execute(
                update_amortization_settings_query(),
                {
                    'company_id': company_id,
                    'name': name,
                    'val': val,
                    'typ': typ
                }
            )

            if update_result.rowcount == 0:
                conn.execute(
                    insert_amortization_settings_query(),
                    {
                        'id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'name': name,
                        'val': val,
                        'typ': typ
                    }
                )
    return jsonify({'success': True})

@amortization_config_bp.route('/api/mark-amortization-mappings', methods=['GET'])
def get_mark_amortization_mappings():
    """Retrieve all mark amortization mappings"""
    engine = require_db_engine()
    with engine.connect() as conn:
        result = conn.execute(mark_amortization_mappings_query())
        mappings = [
            serialize_mapping_row(row)
            for row in serialize_result_rows(result)
        ]

        return jsonify({'mappings': mappings})

@amortization_config_bp.route('/api/mark-amortization-mappings', methods=['POST'])
def create_mark_amortization_mapping():
    """Create a new mark amortization mapping"""
    data = request.json or {}
    if not data.get('mark_id') or not data.get('asset_type'):
        raise BadRequestError('mark_id and asset_type are required')

    engine = require_db_engine()
    mapping_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            insert_mark_amortization_mapping_query(),
            {
                'id': mapping_id,
                'mark_id': data.get('mark_id'),
                'asset_type': data.get('asset_type'),
                'useful_life_years': data.get('useful_life_years', 5),
                'amortization_rate': data.get('amortization_rate', 20.0),
                'asset_group_id': data.get('asset_group_id'),
                'is_deductible_50_percent': data.get('is_deductible_50_percent', False)
            }
        )

    return jsonify({**data, 'id': mapping_id}), 201

@amortization_config_bp.route('/api/mark-amortization-mappings/<mapping_id>', methods=['PUT'])
def update_mark_amortization_mapping(mapping_id):
    """Update a mark amortization mapping"""
    data = request.json or {}
    engine = require_db_engine()
    with engine.begin() as conn:
        result = conn.execute(update_mark_amortization_mapping_query(), {
            'id': mapping_id,
            'mark_id': data.get('mark_id'),
            'asset_type': data.get('asset_type'),
            'useful_life_years': data.get('useful_life_years'),
            'amortization_rate': data.get('amortization_rate'),
            'asset_group_id': data.get('asset_group_id'),
            'is_deductible_50_percent': data.get('is_deductible_50_percent')
        })

    if result.rowcount == 0:
        raise NotFoundError('Mark amortization mapping not found')
    return jsonify({'success': True})

@amortization_config_bp.route('/api/mark-amortization-mappings/<mapping_id>', methods=['DELETE'])
def delete_mark_amortization_mapping(mapping_id):
    """Delete a mark amortization mapping"""
    engine = require_db_engine()
    with engine.begin() as conn:
        result = conn.execute(delete_mark_amortization_mapping_query(), {'id': mapping_id})

    if result.rowcount == 0:
        raise NotFoundError('Mark amortization mapping not found')
    return jsonify({'success': True})

@amortization_config_bp.route('/api/marks/<mark_id>/amortization', methods=['GET'])
def get_mark_amortization_config(mark_id):
    """Get amortization configuration for a specific mark"""
    engine = require_db_engine()
    with engine.connect() as conn:
        result = conn.execute(mark_amortization_config_query(), {'mark_id': mark_id})
        row = result.fetchone()

        if row:
            return jsonify(serialize_mapping_row(row._mapping))
        return jsonify(None)

@amortization_config_bp.route('/api/marks/amortization-eligible', methods=['GET'])
def get_amortization_eligible_marks():
    """Get marks that are eligible for amortization (have asset-related COA mappings)"""
    engine = require_db_engine()
    with engine.connect() as conn:
        result = conn.execute(amortization_eligible_marks_query())
        marks = [
            {
                'id': d['id'],
                'personal_use': d['personal_use'],
                'asset_type': d['asset_type']
            }
            for d in serialize_result_rows(result)
        ]

        return jsonify({
            'marks': marks
        }), 201
