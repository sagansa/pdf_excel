import os
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from backend.db.schema import get_table_columns
from backend.db.session import get_sagansa_engine
from backend.errors import BadRequestError
from backend.routes.accounting_utils import (
    build_inventory_balance_with_carry,
    require_db_engine,
    to_float,
)
from backend.routes.inventory.inventory_queries import (
    insert_carry_forward_inventory_balance_query,
    insert_inventory_balance_query,
    inventory_balance_id_query,
    update_inventory_balance_query,
)
from backend.routes.inventory.remaining_storage_bp import _fetch_all_remote_remaining_storages
from backend.routes.inventory.remaining_storage_helpers import (
    derive_api_root_from_remaining_storage_url,
    extract_detail_stock_card_rows,
    extract_remaining_storage_rows,
    is_remaining_storage_value,
    normalize_remaining_storage_row,
    to_iso_date,
)
from backend.routes.inventory.remaining_storage_queries import build_monitoring_definition_query
from backend.routes.route_utils import _fetch_remote_json, _safe_int

inventory_bp = Blueprint('inventory_bp', __name__)

DEFAULT_REMAINING_STORAGE_API_URL = os.environ.get(
    'SAGANSA_REMAINING_STORAGE_API_URL',
    'https://superadmin.sagansa.id/api/remaining-storages'
)
DEFAULT_REMAINING_STORAGE_API_TOKEN = os.environ.get(
    'SAGANSA_REMAINING_STORAGE_TOKEN',
    ''
)
DEFAULT_STOCK_MONITORING_API_URL = os.environ.get(
    'SAGANSA_STOCK_MONITORING_API_URL',
    'https://superadmin.sagansa.id/api/stock-monitorings'
)
DEFAULT_STOCK_MONITORING_API_TOKEN = os.environ.get(
    'SAGANSA_STOCK_MONITORING_TOKEN',
    DEFAULT_REMAINING_STORAGE_API_TOKEN
)


def _require_remaining_storage_token(token):
    if not token:
        raise BadRequestError('Remaining storage API token is required')


def _require_sagansa_engine():
    engine, error_msg = get_sagansa_engine()
    if engine is None:
        raise BadRequestError(error_msg or 'Sagansa DB connection failed')
    return engine


def _normalize_product_key(value):
    raw = str(value or '').strip().lower()
    if not raw:
        return ''
    return ' '.join(raw.replace('_', ' ').replace('-', ' ').split())


def _fetch_stock_monitoring_index():
    token = str(DEFAULT_STOCK_MONITORING_API_TOKEN or '').strip()
    api_url = str(DEFAULT_STOCK_MONITORING_API_URL or '').strip()
    if not token or not api_url:
        return {}

    try:
        payload = _fetch_remote_json(
            api_url=api_url,
            token=token,
            query_params={'per_page': 200},
            resource_name='StockMonitoring API'
        )
    except Exception:
        return {}

    paginated = payload.get('data') if isinstance(payload, dict) else None
    rows = []
    if isinstance(paginated, dict):
        rows = paginated.get('data') or []
    elif isinstance(payload, list):
        rows = payload

    monitoring_index = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        monitoring_id = str(row.get('id') or '').strip()
        if not monitoring_id:
            continue
        monitoring_index[monitoring_id] = {
            'id': monitoring_id,
            'name': row.get('name') or monitoring_id,
        }
    return monitoring_index


def _fetch_remaining_storage_snapshot(api_url, token, snapshot_date):
    query_base = {
        'date': snapshot_date,
        'per_page': 200,
    }

    meta_payload = _fetch_remote_json(
        api_url=api_url,
        token=token,
        query_params={**query_base, 'page': 1},
        resource_name='RemainingStorage API'
    )
    first_rows, meta = extract_remaining_storage_rows(meta_payload)
    last_page = max(1, _safe_int(meta.get('last_page'), 1))

    normalized_rows = []

    def append_rows(raw_rows):
        for item in raw_rows:
            normalized = normalize_remaining_storage_row(item)
            if not is_remaining_storage_value(normalized.get('for')):
                continue
            normalized_rows.append(normalized)

    append_rows(first_rows)

    for current_page in range(2, last_page + 1):
        page_payload = _fetch_remote_json(
            api_url=api_url,
            token=token,
            query_params={**query_base, 'page': current_page},
            resource_name='RemainingStorage API'
        )
        page_rows, _ = extract_remaining_storage_rows(page_payload)
        append_rows(page_rows)

    if normalized_rows:
        return normalized_rows

    api_root = derive_api_root_from_remaining_storage_url(api_url)
    if not api_root:
        return normalized_rows

    yearly_payload = _fetch_remote_json(
        api_url=f'{api_root}/detail-stock-cards/yearly',
        token=token,
        resource_name='DetailStockCard yearly API'
    )
    yearly_rows = extract_detail_stock_card_rows(yearly_payload)
    yearly_details = []
    for item in yearly_rows:
        if not isinstance(item, dict):
            continue
        if not is_remaining_storage_value(item.get('for')):
            continue
        if to_iso_date(item.get('date')) != snapshot_date:
            continue
        yearly_details.append({
            'id': item.get('id'),
            'product_id': item.get('product_id'),
            'product_name': item.get('product_name') or item.get('name'),
            'unit_name': item.get('unit_name') or item.get('unit'),
            'quantity': to_float(item.get('quantity'), 0.0),
        })

    if yearly_details:
        normalized_rows.append({
            'id': f'yearly-{snapshot_date}',
            'for': 'remaining storage',
            'date': snapshot_date,
            'store_id': None,
            'store_name': None,
            'user_id': None,
            'user_name': None,
            'description': 'Year-end detail-stock-card fallback',
            'detail_count': len(yearly_details),
            'total_quantity': sum(detail['quantity'] for detail in yearly_details),
            'details': yearly_details,
        })

    return normalized_rows


def _fetch_remaining_storage_snapshot_as_of(api_url, token, snapshot_date):
    exact_rows = _fetch_remaining_storage_snapshot(api_url, token, snapshot_date)
    if exact_rows:
        return exact_rows, snapshot_date, 'exact'

    try:
        meta_payload = _fetch_remote_json(
            api_url=api_url,
            token=token,
            query_params={'page': 1, 'per_page': 1},
            resource_name='RemainingStorage API'
        )
    except RuntimeError:
        return [], snapshot_date, 'unavailable'

    _, meta = extract_remaining_storage_rows(meta_payload)
    last_page = max(1, _safe_int(meta.get('last_page'), 1))
    candidate_rows = []

    for current_page in range(1, last_page + 1):
        try:
            page_payload = _fetch_remote_json(
                api_url=api_url,
                token=token,
                query_params={'page': current_page, 'per_page': 200},
                resource_name='RemainingStorage API'
            )
        except RuntimeError:
            continue

        page_rows, _ = extract_remaining_storage_rows(page_payload)
        for item in page_rows:
            normalized = normalize_remaining_storage_row(item)
            if not is_remaining_storage_value(normalized.get('for')):
                continue
            row_date = to_iso_date(normalized.get('date'))
            if not row_date or row_date > snapshot_date:
                continue
            candidate_rows.append(normalized)

    if not candidate_rows:
        return [], snapshot_date, 'empty'

    as_of_date = max(to_iso_date(row.get('date')) for row in candidate_rows if to_iso_date(row.get('date')))
    filtered_rows = [
        row for row in candidate_rows
        if to_iso_date(row.get('date')) == as_of_date
    ]
    return filtered_rows, as_of_date or snapshot_date, 'as_of'


def _build_quantity_map(rows):
    product_map = {}
    for row in rows:
        for detail in row.get('details') or []:
            product_id = detail.get('product_id')
            product_name = detail.get('product_name')
            name_key = _normalize_product_key(product_name)
            if product_id in (None, '') and not name_key:
                continue

            key = str(product_id) if product_id not in (None, '') else f"name:{name_key}"
            quantity = to_float(detail.get('quantity'), 0.0)
            current = product_map.get(key)
            if current is None:
                product_map[key] = {
                    'product_id': str(product_id) if product_id not in (None, '') else None,
                    'product_name': product_name or key,
                    'normalized_name': name_key,
                    'unit_name': detail.get('unit_name') or detail.get('unit_id') or '',
                    'quantity': quantity,
                }
            else:
                current['quantity'] += quantity
                if not current.get('product_name') and product_name:
                    current['product_name'] = product_name
                if not current.get('unit_name') and (detail.get('unit_name') or detail.get('unit_id')):
                    current['unit_name'] = detail.get('unit_name') or detail.get('unit_id')

    return product_map


def _fetch_hpp_price_references(conn, company_id, snapshot_date, monitoring_index=None):
    hpp_batch_product_columns = get_table_columns(conn, 'hpp_batch_products')
    if 'stock_monitoring_id' in hpp_batch_product_columns and 'product_id' in hpp_batch_product_columns:
        reference_expr = "COALESCE(bp.stock_monitoring_id, bp.product_id)"
    elif 'stock_monitoring_id' in hpp_batch_product_columns:
        reference_expr = "bp.stock_monitoring_id"
    else:
        reference_expr = "bp.product_id"

    has_products = bool(get_table_columns(conn, 'products'))
    product_join = "LEFT JOIN products p ON p.id = {reference_expr}".format(reference_expr=reference_expr) if has_products else ""
    local_name_expr = "COALESCE(p.name, CAST({reference_expr} AS CHAR))".format(reference_expr=reference_expr) if has_products else f"CAST({reference_expr} AS CHAR)"
    monitoring_index = monitoring_index or {}

    rows = conn.execute(text(f"""
        SELECT
            CAST(bp.id AS CHAR) AS reference_id,
            CAST({reference_expr} AS CHAR) AS product_id,
            {local_name_expr} AS product_name,
            bp.calculated_unit_idr_hpp AS unit_price,
            CAST(b.id AS CHAR) AS batch_id,
            b.memo AS batch_memo,
            COALESCE(b.batch_date, DATE(b.created_at)) AS effective_date
        FROM hpp_batch_products bp
        JOIN hpp_batches b ON b.id = bp.batch_id
        {product_join}
        WHERE b.company_id = :company_id
          AND COALESCE(b.batch_date, DATE(b.created_at)) <= :snapshot_date
        ORDER BY {reference_expr} ASC, COALESCE(b.batch_date, DATE(b.created_at)) DESC, b.created_at DESC, bp.id DESC
    """), {
        'company_id': company_id,
        'snapshot_date': snapshot_date,
    }).fetchall()

    return [
        {
            'reference_id': str(row.reference_id),
            'batch_id': str(row.batch_id),
            'product_id': str(row.product_id),
            'product_name': (
                monitoring_index.get(str(row.product_id), {}).get('name')
                or row.product_name
            ),
            'unit_price': float(row.unit_price or 0.0),
            'effective_date': str(row.effective_date)[:10] if row.effective_date else None,
            'batch_memo': row.batch_memo or '',
        }
        for row in rows
    ]


def _price_reference_sort_key(row):
    effective_date = str(row.get('effective_date') or '')
    batch_id = str(row.get('batch_id') or '')
    reference_id = str(row.get('reference_id') or '')
    return (
        effective_date,
        batch_id,
        reference_id,
    )


def _build_hpp_price_map(price_references):
    price_map = {}
    sorted_references = sorted(
        price_references,
        key=_price_reference_sort_key,
        reverse=True,
    )
    for row in sorted_references:
        product_id = str(row['product_id'])
        if product_id in price_map:
            continue
        price_map[product_id] = {
            'product_id': product_id,
            'product_name': row.get('product_name'),
            'unit_price': float(row.get('unit_price') or 0.0),
            'effective_date': row.get('effective_date'),
            'batch_id': row.get('batch_id'),
            'batch_memo': row.get('batch_memo'),
            'reference_id': row.get('reference_id'),
        }
    return price_map


def _group_hpp_price_references(price_references):
    grouped = {}
    sorted_references = sorted(
        price_references,
        key=_price_reference_sort_key,
        reverse=True,
    )
    for row in sorted_references:
        product_id = str(row.get('product_id') or '')
        if not product_id:
            continue
        grouped.setdefault(product_id, []).append({
            'reference_id': row.get('reference_id'),
            'batch_id': row.get('batch_id'),
            'batch_memo': row.get('batch_memo'),
            'effective_date': row.get('effective_date'),
            'unit_price': float(row.get('unit_price') or 0.0),
            'product_id': product_id,
            'product_name': row.get('product_name') or product_id,
        })
    return grouped


def _build_hpp_price_name_map(price_references):
    grouped = {}
    sorted_references = sorted(
        price_references,
        key=_price_reference_sort_key,
        reverse=True,
    )
    for row in sorted_references:
        name_key = _normalize_product_key(row.get('product_name'))
        if not name_key:
            continue
        grouped.setdefault(name_key, []).append({
            'reference_id': row.get('reference_id'),
            'batch_id': row.get('batch_id'),
            'batch_memo': row.get('batch_memo'),
            'effective_date': row.get('effective_date'),
            'unit_price': float(row.get('unit_price') or 0.0),
            'product_id': str(row.get('product_id') or ''),
            'product_name': row.get('product_name') or '',
        })
    return grouped


def _fetch_monitoring_product_coefficients():
    engine = _require_sagansa_engine()

    with engine.connect() as conn:
        sm_columns = get_table_columns(conn, 'stock_monitorings')
        smd_table = 'stock_monitoring_details'
        smd_columns = get_table_columns(conn, smd_table)
        if not smd_columns:
            smd_table = 'detail_stock_monitorings'
            smd_columns = get_table_columns(conn, smd_table)

        if not sm_columns or not smd_columns or 'product_id' not in smd_columns:
            return {}

        if 'stock_monitoring_id' in smd_columns:
            smd_monitoring_fk = 'stock_monitoring_id'
        elif 'monitoring_id' in smd_columns:
            smd_monitoring_fk = 'monitoring_id'
        else:
            return {}

        if 'coefficient' in smd_columns:
            coefficient_expr = "COALESCE(smd.`coefficient`, 1)"
        elif 'coefisien' in smd_columns:
            coefficient_expr = "COALESCE(smd.`coefisien`, 1)"
        elif 'koefisien' in smd_columns:
            coefficient_expr = "COALESCE(smd.`koefisien`, 1)"
        else:
            coefficient_expr = "1"

        category_filter = "WHERE sm.`category` = 'storage'" if 'category' in sm_columns else ''

        rows = conn.execute(text(f"""
            SELECT
                CAST(smd.`product_id` AS CHAR) AS product_id,
                p.name AS product_name,
                sm.name AS monitoring_name,
                {coefficient_expr} AS coefficient_value
            FROM stock_monitorings sm
            JOIN {smd_table} smd
                ON smd.`{smd_monitoring_fk}` = sm.id
            LEFT JOIN products p
                ON p.id = smd.`product_id`
            {category_filter}
            ORDER BY p.name ASC, sm.name ASC
        """)).fetchall()

    coefficient_map = {}
    for row in rows:
        product_id = str(row.product_id or '').strip()
        product_name = str(row.product_name or '').strip()
        if not product_id and not product_name:
            continue

        key = product_id or f"name:{_normalize_product_key(product_name)}"
        current = coefficient_map.get(key)
        coefficient_value = to_float(row.coefficient_value, 1.0)

        if current is None:
            coefficient_map[key] = {
                'product_id': product_id or None,
                'product_name': product_name or None,
                'normalized_name': _normalize_product_key(product_name),
                'coefficient': coefficient_value or 1.0,
                'monitoring_names': [row.monitoring_name] if row.monitoring_name else [],
            }
            continue

        if row.monitoring_name and row.monitoring_name not in current['monitoring_names']:
            current['monitoring_names'].append(row.monitoring_name)
        if current.get('coefficient') in (None, 0):
            current['coefficient'] = coefficient_value or 1.0

    return coefficient_map


def _fetch_monitoring_quantity_map(api_url, token, snapshot_date):
    engine = _require_sagansa_engine()
    remote_rows = _fetch_all_remote_remaining_storages(
        api_url=api_url,
        token=token,
        selected_date=snapshot_date,
    )

    remote_product_totals = {}
    for row in remote_rows:
        for detail in row.get('details') or []:
            product_id = detail.get('product_id')
            if product_id in (None, ''):
                continue
            key = str(product_id)
            quantity_value = to_float(detail.get('quantity'), 0.0)
            remote_product_totals[key] = remote_product_totals.get(key, 0.0) + quantity_value

    with engine.connect() as conn:
        sm_columns = get_table_columns(conn, 'stock_monitorings')
        smd_table = 'stock_monitoring_details'
        smd_columns = get_table_columns(conn, smd_table)
        if not smd_columns:
            smd_table = 'detail_stock_monitorings'
            smd_columns = get_table_columns(conn, smd_table)

        if not sm_columns or not smd_columns or 'product_id' not in smd_columns:
            return {}, snapshot_date, 'monitoring_empty'

        if 'stock_monitoring_id' in smd_columns:
            smd_monitoring_fk = 'stock_monitoring_id'
        elif 'monitoring_id' in smd_columns:
            smd_monitoring_fk = 'monitoring_id'
        else:
            return {}, snapshot_date, 'monitoring_empty'

        if 'coefficient' in smd_columns:
            coefficient_expr = "COALESCE(smd.`coefficient`, 1)"
        elif 'coefisien' in smd_columns:
            coefficient_expr = "COALESCE(smd.`coefisien`, 1)"
        elif 'koefisien' in smd_columns:
            coefficient_expr = "COALESCE(smd.`koefisien`, 1)"
        else:
            coefficient_expr = "1"

        units_columns = get_table_columns(conn, 'units')
        if 'nickname' in units_columns:
            unit_column = 'nickname'
        elif 'unit' in units_columns:
            unit_column = 'unit'
        elif 'name' in units_columns:
            unit_column = 'name'
        else:
            unit_column = None

        product_unit_select = (
            f"pu.`{unit_column}` AS product_unit_name"
            if unit_column else
            "NULL AS product_unit_name"
        )
        category_filter = "WHERE sm.`category` = 'storage'" if 'category' in sm_columns else ''
        monitoring_query = build_monitoring_definition_query(
            smd_table=smd_table,
            smd_monitoring_fk=smd_monitoring_fk,
            coefficient_expr=coefficient_expr,
            product_unit_select=product_unit_select,
            category_filter=category_filter,
        )
        rows_raw = conn.execute(monitoring_query).fetchall()

    grouped = {}
    for row in rows_raw:
        detail = row._mapping
        monitoring_name = str(detail.get('monitoring_name') or '').strip()
        if not monitoring_name:
            continue

        monitoring_key = _normalize_product_key(monitoring_name)
        if monitoring_key not in grouped:
            grouped[monitoring_key] = {
                'monitoring_name': monitoring_name,
                'quantity': 0.0,
                'unit_name': str(detail.get('product_unit_name') or '').strip(),
                'component_count': 0,
            }

        product_id = detail.get('product_id')
        product_key = str(product_id) if product_id not in (None, '') else ''
        remaining_quantity = remote_product_totals.get(product_key, 0.0)
        coefficient_value = to_float(detail.get('coefficient_value'), 1.0)
        grouped[monitoring_key]['quantity'] += remaining_quantity * coefficient_value
        grouped[monitoring_key]['component_count'] += 1
        if not grouped[monitoring_key]['unit_name']:
            grouped[monitoring_key]['unit_name'] = str(detail.get('product_unit_name') or '').strip()

    return grouped, snapshot_date, 'dashboard_monitoring'


def _fetch_inventory_products(conn, company_id, coefficient_map=None):
    rows = conn.execute(text("""
        SELECT
            CAST(p.id AS CHAR) AS product_id,
            p.name AS product_name
        FROM products p
        WHERE p.company_id = :company_id OR p.company_id IS NULL
        ORDER BY p.name ASC
    """), {
        'company_id': company_id,
    }).fetchall()

    coefficient_map = coefficient_map or {}

    inventory_products = []
    for row in rows:
        product_id = str(row.product_id)
        product_name = row.product_name or str(row.product_id)
        normalized_name = _normalize_product_key(product_name)
        coefficient_info = (
            coefficient_map.get(product_id)
            or coefficient_map.get(f"name:{normalized_name}")
            or {}
        )
        inventory_products.append({
            'product_id': product_id,
            'product_name': product_name,
            'normalized_name': normalized_name,
            'unit_name': '',
            'monitoring_names': coefficient_info.get('monitoring_names') or [],
            'coefficient': to_float(coefficient_info.get('coefficient'), 1.0),
        })

    return inventory_products


def _calculate_inventory_snapshot(conn, company_id, year, api_url, token, inventory_products, monitoring_index=None):
    snapshot_date = f"{int(year)}-12-31"
    monitoring_quantity_map, as_of_date, snapshot_source = _fetch_monitoring_quantity_map(api_url, token, snapshot_date)
    price_references = _fetch_hpp_price_references(conn, company_id, snapshot_date, monitoring_index=monitoring_index)
    price_map = _build_hpp_price_map(price_references)
    price_options_by_product = _group_hpp_price_references(price_references)
    price_options_by_name = _build_hpp_price_name_map(price_references)

    line_items = []
    total_quantity = 0.0
    total_amount = 0.0
    missing_price_count = 0

    for inventory_product in inventory_products:
        product_id = str(inventory_product.get('product_id') or '')
        product_name_key = _normalize_product_key(inventory_product.get('product_name'))
        monitoring_quantity = monitoring_quantity_map.get(product_name_key)
        raw_quantity = 0.0
        coefficient_value = 1.0
        quantity = to_float(monitoring_quantity.get('quantity'), 0.0) if monitoring_quantity else 0.0
        total_quantity += quantity

        price_info = price_map.get(product_id)
        if price_info is None and product_name_key:
            name_options = price_options_by_name.get(product_name_key) or []
            price_info = name_options[0] if name_options else None
        unit_price = to_float(price_info.get('unit_price'), 0.0) if price_info else 0.0
        total_value = quantity * unit_price if price_info else 0.0
        total_amount += total_value
        if not price_info:
            missing_price_count += 1

        line_items.append({
            'product_id': product_id,
            'product_name': (
                inventory_product.get('product_name')
                or (price_info.get('product_name') if price_info else None)
                or product_id
            ),
            'unit_name': (
                monitoring_quantity.get('unit_name') if monitoring_quantity else None
            ) or inventory_product.get('unit_name') or '',
            'monitoring_names': (
                [monitoring_quantity.get('monitoring_name')] if monitoring_quantity else inventory_product.get('monitoring_names') or []
            ),
            'raw_quantity': raw_quantity,
            'coefficient': coefficient_value if not monitoring_quantity else 1.0,
            'quantity': quantity,
            'unit_price': unit_price if price_info else None,
            'total_value': total_value if price_info else None,
            'price_effective_date': price_info.get('effective_date') if price_info else None,
            'price_batch_id': price_info.get('batch_id') if price_info else None,
            'price_batch_memo': price_info.get('batch_memo') if price_info else None,
            'price_reference_id': price_info.get('reference_id') if price_info else None,
            'price_options': (
                price_options_by_product.get(product_id)
                or price_options_by_name.get(product_name_key, [])
            ),
            'has_price': bool(price_info),
        })

    line_items.sort(
        key=lambda item: (
            str(item.get('product_name') or '').lower(),
            str(item.get('product_id') or ''),
        )
    )

    available_prices = sorted(
        [
            {
                'product_id': key,
                'product_name': value.get('product_name') or key,
                'unit_price': to_float(value.get('unit_price'), 0.0),
                'effective_date': value.get('effective_date'),
            }
            for key, value in price_map.items()
        ],
        key=lambda item: str(item.get('product_name') or '').lower(),
    )

    missing_items = [item for item in line_items if not item.get('has_price')]

    return {
        'snapshot_date': snapshot_date,
        'as_of_date': as_of_date,
        'snapshot_source': snapshot_source,
        'year': int(year),
        'amount': total_amount,
        'quantity': total_quantity,
        'line_count': len(line_items),
        'missing_price_count': missing_price_count,
        'priced_line_count': len(line_items) - missing_price_count,
        'items': line_items,
        'missing_items': missing_items,
        'available_prices': available_prices,
    }


@inventory_bp.route('/api/inventory-balances', methods=['GET'])
@inventory_bp.route('/api/reports/inventory-balances', methods=['GET'])
def get_inventory_balances():
    engine = require_db_engine()

    year_raw = request.args.get('year') or datetime.now().year
    try:
        year = int(year_raw)
    except (TypeError, ValueError):
        raise BadRequestError('year must be numeric')

    company_id = request.args.get('company_id')
    if not company_id:
        raise BadRequestError('company_id is required')

    with engine.connect() as conn:
        balance = build_inventory_balance_with_carry(conn, year, company_id)
        return jsonify({'balance': balance})


@inventory_bp.route('/api/inventory-balances/auto', methods=['GET'])
@inventory_bp.route('/api/reports/inventory-balances/auto', methods=['GET'])
def get_inventory_auto_balances():
    engine = require_db_engine()

    year_raw = request.args.get('year') or datetime.now().year
    try:
        year = int(year_raw)
    except (TypeError, ValueError):
        raise BadRequestError('year must be numeric')

    company_id = request.args.get('company_id')
    if not company_id:
        raise BadRequestError('company_id is required')

    api_url = str(request.args.get('api_url') or DEFAULT_REMAINING_STORAGE_API_URL).strip()
    token = str(
        request.args.get('token')
        or request.args.get('access_token')
        or request.args.get('api_token')
        or DEFAULT_REMAINING_STORAGE_API_TOKEN
        or ''
    ).strip()
    _require_remaining_storage_token(token)
    with engine.connect() as conn:
        coefficient_map = _fetch_monitoring_product_coefficients()
        inventory_products = _fetch_inventory_products(conn, company_id, coefficient_map)
        monitoring_index = _fetch_stock_monitoring_index()
        beginning = _calculate_inventory_snapshot(conn, company_id, year - 1, api_url, token, inventory_products, monitoring_index=monitoring_index)
        ending = _calculate_inventory_snapshot(conn, company_id, year, api_url, token, inventory_products, monitoring_index=monitoring_index)

    return jsonify({
        'success': True,
        'beginning': beginning,
        'ending': ending,
    })


@inventory_bp.route('/api/inventory-balances', methods=['POST'])
@inventory_bp.route('/api/reports/inventory-balances', methods=['POST'])
def save_inventory_balances():
    engine = require_db_engine()

    payload = request.json or {}
    for field in ['year', 'company_id']:
        if field not in payload:
            raise BadRequestError(f'{field} is required')

    try:
        year = int(payload.get('year'))
    except (TypeError, ValueError):
        raise BadRequestError('year must be numeric')
    company_id = payload.get('company_id')

    beginning_amount = to_float(payload.get('beginning_inventory_amount'), 0.0)
    beginning_qty = to_float(payload.get('beginning_inventory_qty'), 0.0)
    ending_amount = to_float(payload.get('ending_inventory_amount'), 0.0)
    ending_qty = to_float(payload.get('ending_inventory_qty'), 0.0)
    base_value = to_float(payload.get('base_value'), 0.0)

    with engine.begin() as conn:
        now = datetime.now()

        existing = conn.execute(inventory_balance_id_query(), {
            'year': year,
            'company_id': company_id
        }).fetchone()

        if existing:
            conn.execute(update_inventory_balance_query(), {
                'beginning_amount': beginning_amount,
                'beginning_qty': beginning_qty,
                'ending_amount': ending_amount,
                'ending_qty': ending_qty,
                'base_value': base_value,
                'year': year,
                'company_id': company_id,
                'updated_at': now
            })
        else:
            conn.execute(insert_inventory_balance_query(), {
                'id': str(uuid.uuid4()),
                'company_id': company_id,
                'year': year,
                'beginning_amount': beginning_amount,
                'beginning_qty': beginning_qty,
                'ending_amount': ending_amount,
                'ending_qty': ending_qty,
                'base_value': base_value,
                'created_at': now,
                'updated_at': now
            })

        next_year = year + 1
        next_existing = conn.execute(inventory_balance_id_query(), {
            'year': next_year,
            'company_id': company_id
        }).fetchone()

        if not next_existing:
            conn.execute(insert_carry_forward_inventory_balance_query(), {
                'id': str(uuid.uuid4()),
                'company_id': company_id,
                'year': next_year,
                'beginning_amount': ending_amount,
                'beginning_qty': ending_qty,
                'base_value': ending_amount,
                'created_at': now,
                'updated_at': now
            })

        balance = build_inventory_balance_with_carry(conn, year, company_id)

    return jsonify({
        'success': True,
        'message': 'Inventory balance saved successfully',
        'balance': balance
    })
