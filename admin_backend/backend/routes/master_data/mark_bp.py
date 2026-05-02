import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.db.schema import get_table_columns
from backend.errors import BadRequestError, ConflictError, NotFoundError
from backend.routes.accounting_utils import require_db_engine, serialize_result_rows
from backend.routes.route_utils import _parse_bool

mark_bp = Blueprint('mark_bp', __name__)


def _normalize_mapping_report_type(value, allow_all=False):
    normalized = str(value or '').strip().lower()
    if normalized == 'coretax':
        return 'coretax'
    if allow_all and normalized == 'all':
        return 'all'
    return 'real'


@mark_bp.route('/api/marks', methods=['GET'])
def get_marks():
    engine = require_db_engine()
    include_system = _parse_bool(request.args.get('include_system'))

    with engine.connect() as conn:
        mark_columns = get_table_columns(conn, 'marks')
        where_sql = ""
        params = {}
        if 'is_system_generated' in mark_columns and not include_system:
            where_sql = "WHERE COALESCE(is_system_generated, 0) = 0"
        result = conn.execute(text(f"SELECT * FROM marks {where_sql} ORDER BY personal_use ASC"), params)
        marks = serialize_result_rows(result)
        marks_dict = {}
        for d in marks:
            if 'is_asset' not in d:
                d['is_asset'] = False
            if 'is_service' not in d:
                d['is_service'] = False
            if 'is_salary_component' not in d:
                d['is_salary_component'] = False
            if 'is_rental' not in d:
                d['is_rental'] = False
            if 'is_coretax' not in d:
                d['is_coretax'] = False
            if 'is_system_generated' not in d:
                d['is_system_generated'] = False
            d['is_asset'] = _parse_bool(d.get('is_asset'))
            d['is_service'] = _parse_bool(d.get('is_service'))
            d['is_salary_component'] = _parse_bool(d.get('is_salary_component'))
            d['is_rental'] = _parse_bool(d.get('is_rental'))
            d['is_coretax'] = _parse_bool(d.get('is_coretax'))
            d['is_system_generated'] = _parse_bool(d.get('is_system_generated'))
            d['fiscal_category'] = d.get('fiscal_category')
            d['mappings_real'] = []
            d['mappings_coretax'] = []
            d['mappings'] = d['mappings_real']
            marks_dict[d['id']] = d

        mapping_columns = get_table_columns(conn, 'mark_coa_mapping')
        report_type_select_sql = "'real' AS report_type"
        if 'report_type' in mapping_columns:
            if conn.dialect.name == 'sqlite':
                report_type_expr = "LOWER(COALESCE(NULLIF(TRIM(CAST(mcm.report_type AS TEXT)), ''), 'real'))"
            else:
                report_type_expr = "LOWER(COALESCE(NULLIF(TRIM(CAST(mcm.report_type AS CHAR)), ''), 'real'))"
            report_type_select_sql = f"{report_type_expr} AS report_type"

        mapping_result = conn.execute(text(f"""
            SELECT mcm.mark_id, mcm.coa_id, mcm.mapping_type, coa.code, coa.name, {report_type_select_sql}
            FROM mark_coa_mapping mcm
            JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        """))

        for m in serialize_result_rows(mapping_result):
            mark_id = m['mark_id']
            if mark_id in marks_dict:
                report_type = str(m.get('report_type') or 'real').strip().lower()
                target_key = 'mappings_coretax' if report_type == 'coretax' else 'mappings_real'
                marks_dict[mark_id][target_key].append({
                    'id': m['coa_id'],
                    'coa_id': m['coa_id'],
                    'code': m['code'],
                    'name': m['name'],
                    'type': m['mapping_type'],
                    'report_type': report_type
                })

        return jsonify({'marks': marks})


@mark_bp.route('/api/marks', methods=['POST'])
def create_mark():
    engine = require_db_engine()

    data = request.json or {}
    now = datetime.now()
    mark_id = str(uuid.uuid4())
    with engine.begin() as conn:
        mark_columns = get_table_columns(conn, 'marks')
        if 'is_service' not in mark_columns:
            raise BadRequestError('Kolom is_service belum tersedia. Jalankan migrasi terbaru.')
        if 'is_coretax' not in mark_columns:
            raise BadRequestError('Kolom is_coretax belum tersedia. Jalankan migrasi terbaru.')
        new_row = {
            'id': mark_id,
            'internal_report': data.get('internal_report', ''),
            'personal_use': data.get('personal_use', ''),
            'tax_report': data.get('tax_report', ''),
            'is_asset': _parse_bool(data.get('is_asset', False)),
            'is_service': _parse_bool(data.get('is_service', False)),
            'is_salary_component': _parse_bool(data.get('is_salary_component', False)),
            'is_rental': _parse_bool(data.get('is_rental', False)),
            'is_coretax': _parse_bool(data.get('is_coretax', False)),
            'fiscal_category': data.get('fiscal_category') or None,
            'created_at': now,
            'updated_at': now
        }
        insert_columns = [column for column in new_row.keys() if column in mark_columns]
        columns_sql = ', '.join(insert_columns)
        values_sql = ', '.join(f":{column}" for column in insert_columns)
        conn.execute(text(f"""
            INSERT INTO marks ({columns_sql})
            VALUES ({values_sql})
        """), new_row)
    return jsonify({'message': 'Mark created successfully', 'id': mark_id}), 201


@mark_bp.route('/api/marks/<mark_id>', methods=['PUT', 'DELETE'])
def update_or_delete_mark(mark_id):
    engine = require_db_engine()

    if request.method == 'DELETE':
        with engine.begin() as conn:
            conn.execute(text("UPDATE transactions SET mark_id = NULL WHERE mark_id = :id"), {'id': mark_id})
            result = conn.execute(text("DELETE FROM marks WHERE id = :id"), {'id': mark_id})
            if result.rowcount == 0:
                raise NotFoundError('Mark not found')
        return jsonify({'message': 'Mark deleted successfully'})

    data = request.json or {}
    with engine.begin() as conn:
        mark_columns = get_table_columns(conn, 'marks')
        if 'is_service' in data and 'is_service' not in mark_columns:
            raise BadRequestError('Kolom is_service belum tersedia. Jalankan migrasi terbaru.')
        if 'is_salary_component' in data and 'is_salary_component' not in mark_columns:
            raise BadRequestError('Kolom is_salary_component belum tersedia. Jalankan migrasi terbaru.')
        if 'is_rental' in data and 'is_rental' not in mark_columns:
            raise BadRequestError('Kolom is_rental belum tersedia. Jalankan migrasi terbaru.')
        if 'is_coretax' in data and 'is_coretax' not in mark_columns:
            raise BadRequestError('Kolom is_coretax belum tersedia. Jalankan migrasi terbaru.')

        field_map = {
            'internal_report': 'internal_report',
            'personal_use': 'personal_use',
            'tax_report': 'tax_report',
            'is_asset': 'is_asset',
            'is_service': 'is_service',
            'is_salary_component': 'is_salary_component',
            'is_rental': 'is_rental',
            'is_coretax': 'is_coretax',
            'fiscal_category': 'fiscal_category'
        }

        params = {'id': mark_id, 'updated_at': datetime.now()}
        set_fields = []
        for payload_key, column_name in field_map.items():
            if payload_key in data and column_name in mark_columns:
                if payload_key in {'is_asset', 'is_service', 'is_salary_component', 'is_rental', 'is_coretax'}:
                    params[payload_key] = _parse_bool(data.get(payload_key))
                else:
                    val = data.get(payload_key)
                    if payload_key == 'fiscal_category' and not val:
                        val = None
                    params[payload_key] = val
                set_fields.append(f"{column_name} = :{payload_key}")

        if 'updated_at' in mark_columns:
            set_fields.append("updated_at = :updated_at")

        if not set_fields:
            raise BadRequestError('No valid fields to update')

        conn.execute(text(f"""
            UPDATE marks
            SET {', '.join(set_fields)}
            WHERE id = :id
        """), params)
    return jsonify({'message': 'Mark updated successfully'})


@mark_bp.route('/api/marks/<mark_id>/coa-mappings', methods=['GET'])
def get_mark_coa_mappings(mark_id):
    engine = require_db_engine()

    requested_report_type = _normalize_mapping_report_type(
        request.args.get('report_type'),
        allow_all=True
    )
    with engine.connect() as conn:
        mapping_columns = get_table_columns(conn, 'mark_coa_mapping')
        report_type_select_sql = "'real' AS report_type"
        report_type_filter_sql = ""
        params = {'mark_id': mark_id}

        if 'report_type' in mapping_columns:
            if conn.dialect.name == 'sqlite':
                report_type_expr = "LOWER(COALESCE(NULLIF(TRIM(CAST(mcm.report_type AS TEXT)), ''), 'real'))"
            else:
                report_type_expr = "LOWER(COALESCE(NULLIF(TRIM(CAST(mcm.report_type AS CHAR)), ''), 'real'))"
            report_type_select_sql = f"{report_type_expr} AS report_type"
            if requested_report_type != 'all':
                report_type_filter_sql = f"AND {report_type_expr} = :report_type"
                params['report_type'] = requested_report_type

        result = conn.execute(text(f"""
            SELECT mcm.*, {report_type_select_sql}, coa.code, coa.name, coa.category
            FROM mark_coa_mapping mcm
            INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            WHERE mcm.mark_id = :mark_id
            {report_type_filter_sql}
            ORDER BY coa.code
        """), params)

        mappings = serialize_result_rows(result)
        return jsonify({'mappings': mappings})


@mark_bp.route('/api/marks/<mark_id>/coa-mappings', methods=['POST'])
def create_mark_coa_mapping(mark_id):
    engine = require_db_engine()

    data = request.json or {}
    coa_id = data.get('coa_id')
    mapping_type = data.get('mapping_type', 'DEBIT')
    report_type = _normalize_mapping_report_type(data.get('report_type'))

    if not coa_id:
        raise BadRequestError('COA ID is required')
    if mapping_type not in ['DEBIT', 'CREDIT']:
        raise BadRequestError('Invalid mapping type')

    mapping_id = str(uuid.uuid4())
    now = datetime.now()
    try:
        with engine.begin() as conn:
            mapping_columns = get_table_columns(conn, 'mark_coa_mapping')
            mapping_payload = {
                'id': mapping_id,
                'mark_id': mark_id,
                'coa_id': coa_id,
                'mapping_type': mapping_type,
                'notes': data.get('notes'),
                'created_at': now,
                'updated_at': now,
                'report_type': report_type
            }
            insert_columns = [column for column in mapping_payload.keys() if column in mapping_columns]
            columns_sql = ', '.join(insert_columns)
            values_sql = ', '.join(f":{column}" for column in insert_columns)
            conn.execute(text(f"""
                INSERT INTO mark_coa_mapping ({columns_sql})
                VALUES ({values_sql})
            """), mapping_payload)
        return jsonify({
            'message': 'Mapping created successfully',
            'id': mapping_id,
            'report_type': report_type
        }), 201
    except IntegrityError as error:
        if 'Duplicate entry' in str(error) or 'UNIQUE constraint failed' in str(error):
            raise ConflictError('This mapping already exists')
        raise


@mark_bp.route('/api/mark-coa-mappings/<mapping_id>', methods=['DELETE'])
def delete_mark_coa_mapping(mapping_id):
    engine = require_db_engine()

    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM mark_coa_mapping WHERE id = :id"), {'id': mapping_id})
        if result.rowcount == 0:
            raise NotFoundError('Mapping not found')
    return jsonify({'message': 'Mapping deleted successfully'})
