import os
from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from backend.db.schema import get_table_columns
from backend.db.session import get_sagansa_engine
from backend.errors import ApiError, BadRequestError, NotFoundError
from backend.routes.accounting_utils import serialize_result_rows
from backend.routes.inventory.remaining_storage_helpers import (
    build_remaining_storage_store_options,
    derive_api_root_from_remaining_storage_url,
    extract_detail_stock_card_rows,
    extract_remaining_storage_detail_item,
    extract_remaining_storage_rows,
    normalize_detail_stock_card_item,
    normalize_remaining_storage_row,
    normalize_stock_card_for,
    remaining_storage_sort_key,
    to_iso_date,
)
from backend.routes.inventory.remaining_storage_queries import (
    build_all_store_query,
    build_monitoring_query,
    build_reported_store_query,
)
from backend.routes.route_utils import (
    _fetch_remote_json,
    _normalize_iso_date,
    _parse_bool,
    _safe_int,
    _to_float,
)

remaining_storage_bp = Blueprint('remaining_storage_bp', __name__)

DEFAULT_REMAINING_STORAGE_API_URL = os.environ.get(
    'SAGANSA_REMAINING_STORAGE_API_URL',
    'https://superadmin.sagansa.id/api/remaining-storages'
)
DEFAULT_REMAINING_STORAGE_API_TOKEN = os.environ.get(
    'SAGANSA_REMAINING_STORAGE_TOKEN',
    ''
)


def _require_remaining_storage_token(token):
    if not token:
        raise BadRequestError('Remaining storage API token is required')


def _require_sagansa_engine():
    engine, error_msg = get_sagansa_engine()
    if engine is None:
        raise ApiError(error_msg or 'Sagansa DB connection failed', status_code=500, code='db_unavailable')
    return engine


@remaining_storage_bp.route('/api/remaining-storages', methods=['GET'])
@remaining_storage_bp.route('/api/remaining-storages/', methods=['GET'])
def get_remaining_storages():
    api_url = str(request.args.get('api_url') or DEFAULT_REMAINING_STORAGE_API_URL).strip()
    token = str(
        request.args.get('token')
        or request.args.get('access_token')
        or request.args.get('api_token')
        or DEFAULT_REMAINING_STORAGE_API_TOKEN
        or ''
    ).strip()
    store_id = str(request.args.get('store_id') or '').strip()
    store_keyword = str(request.args.get('store') or '').strip().lower()
    date_filter = _normalize_iso_date(request.args.get('date'))
    page = max(1, _safe_int(request.args.get('page'), 1))
    per_page = _safe_int(request.args.get('per_page'), 15)
    per_page = min(max(per_page, 1), 200)
    recent_only = _parse_bool(request.args.get('recent_only', True))
    scan_pages = _safe_int(request.args.get('scan_pages'), 4)
    scan_pages = min(max(scan_pages, 1), 30)

    if request.args.get('date') not in (None, '') and not date_filter:
        raise BadRequestError('date must use YYYY-MM-DD format')
    _require_remaining_storage_token(token)

    base_query_params = {}
    if store_id:
        base_query_params['store_id'] = store_id
    if date_filter:
        base_query_params['date'] = date_filter

    meta_payload = _fetch_remote_json(
        api_url=api_url,
        token=token,
        query_params={**base_query_params, 'page': 1, 'per_page': 1},
        resource_name='RemainingStorage API'
    )
    _, meta_info = extract_remaining_storage_rows(meta_payload)
    remote_last_page = max(1, _safe_int(meta_info.get('last_page'), 1))

    if recent_only:
        first_remote_page = max(1, remote_last_page - scan_pages + 1)
        remote_pages = range(remote_last_page, first_remote_page - 1, -1)
    else:
        remote_pages = range(remote_last_page, 0, -1)

    remote_per_page = 200
    all_rows = []
    scanned_page_count = 0
    for remote_page in remote_pages:
        scanned_page_count += 1
        page_payload = _fetch_remote_json(
            api_url=api_url,
            token=token,
            query_params={
                **base_query_params,
                'page': remote_page,
                'per_page': remote_per_page
            },
            resource_name='RemainingStorage API'
        )
        raw_rows, _ = extract_remaining_storage_rows(page_payload)
        for item in raw_rows:
            normalized = normalize_remaining_storage_row(item)
            normalized_for = normalize_stock_card_for(normalized.get('for'))
            if normalized_for != 'remaining storage':
                continue
            if store_keyword:
                haystack = str(normalized.get('store_name') or '').strip().lower()
                if store_keyword not in haystack:
                    continue
            all_rows.append(normalized)

    all_rows.sort(key=remaining_storage_sort_key, reverse=True)
    store_options = build_remaining_storage_store_options(all_rows)

    total = len(all_rows)
    last_page = max(1, ((total - 1) // per_page) + 1) if total > 0 else 1
    current_page = min(page, last_page)
    start_idx = (current_page - 1) * per_page
    end_idx = start_idx + per_page
    rows = all_rows[start_idx:end_idx]

    for row in rows:
        row['details'] = []
        row['detail_count'] = int(row.get('detail_count') or 0)
        row['total_quantity'] = _to_float(row.get('total_quantity'), 0.0)

    return jsonify({
        'success': True,
        'data': rows,
        'remaining_storages': rows,
        'store_options': store_options,
        'pagination': {
            'page': current_page,
            'per_page': per_page,
            'total': total,
            'last_page': last_page
        },
        'meta': {
            'recent_only': bool(recent_only),
            'scan_pages': scan_pages,
            'source_last_page': remote_last_page,
            'source_pages_scanned': scanned_page_count,
            'partial_result': bool(recent_only and remote_last_page > scan_pages)
        },
        'count': len(rows)
    })


@remaining_storage_bp.route('/api/remaining-storages/<stock_card_id>/details', methods=['GET'])
def get_remaining_storage_details(stock_card_id):
    api_url = str(request.args.get('api_url') or DEFAULT_REMAINING_STORAGE_API_URL).strip()
    token = str(
        request.args.get('token')
        or request.args.get('access_token')
        or request.args.get('api_token')
        or DEFAULT_REMAINING_STORAGE_API_TOKEN
        or ''
    ).strip()

    _require_remaining_storage_token(token)

    show_payload = _fetch_remote_json(
        api_url=f"{str(api_url).rstrip('/')}/{stock_card_id}",
        token=token,
        resource_name='RemainingStorage API detail'
    )
    detail_item = extract_remaining_storage_detail_item(show_payload)
    normalized = normalize_remaining_storage_row(detail_item)

    normalized_for = normalize_stock_card_for(normalized.get('for'))
    if normalized_for != 'remaining storage':
        raise NotFoundError('Stock card is not remaining_storage')

    api_root = derive_api_root_from_remaining_storage_url(api_url)
    detail_stock_cards_url = f"{api_root}/detail-stock-cards" if api_root else ''
    if detail_stock_cards_url:
        try:
            detail_rows_payload = _fetch_remote_json(
                api_url=detail_stock_cards_url,
                token=token,
                query_params={'stock_card_id': stock_card_id},
                resource_name='DetailStockCard API'
            )
            detail_rows_raw = extract_detail_stock_card_rows(detail_rows_payload)
            detail_rows_normalized = []
            for detail_row in detail_rows_raw:
                normalized_detail = normalize_detail_stock_card_item(detail_row)
                if normalized_detail:
                    detail_rows_normalized.append(normalized_detail)

            if detail_rows_normalized:
                normalized['details'] = detail_rows_normalized
                normalized['detail_count'] = len(detail_rows_normalized)
                normalized['total_quantity'] = sum(
                    _to_float(detail.get('quantity'), 0.0) for detail in detail_rows_normalized
                )
                first_detail = detail_rows_raw[0] if isinstance(detail_rows_raw[0], dict) else {}
                normalized['store_name'] = (
                    first_detail.get('store_name')
                    or first_detail.get('store_nickname')
                    or normalized.get('store_name')
                )
        except Exception:
            pass

    return jsonify({'success': True, 'data': normalized})


@remaining_storage_bp.route('/api/dashboard/remaining-storage', methods=['GET'])
def get_dashboard_remaining_storage():
    engine = _require_sagansa_engine()

    raw_date = request.args.get('date')
    if raw_date in (None, ''):
        selected_date = (date.today() - timedelta(days=1)).isoformat()
    else:
        selected_date = _normalize_iso_date(raw_date)
    if raw_date not in (None, '') and not selected_date:
        raise BadRequestError('date must use YYYY-MM-DD format')

    limit = _safe_int(request.args.get('limit'), 12)
    limit = min(max(limit, 1), 100)

    with engine.connect() as conn:
        sm_columns = get_table_columns(conn, 'stock_monitorings')
        if not sm_columns:
            raise ApiError('Table stock_monitorings not found', status_code=500, code='schema_missing')

        smd_table = 'stock_monitoring_details'
        smd_columns = get_table_columns(conn, smd_table)
        if not smd_columns:
            smd_table = 'detail_stock_monitorings'
            smd_columns = get_table_columns(conn, smd_table)
        if not smd_columns:
            raise ApiError(
                'Table stock_monitoring_details/detail_stock_monitorings not found',
                status_code=500,
                code='schema_missing'
            )

        if 'stock_monitoring_id' in smd_columns:
            smd_monitoring_fk = 'stock_monitoring_id'
        elif 'monitoring_id' in smd_columns:
            smd_monitoring_fk = 'monitoring_id'
        else:
            raise ApiError(
                'Monitoring detail table missing stock_monitoring_id/monitoring_id column',
                status_code=500,
                code='schema_missing'
            )

        if 'product_id' not in smd_columns:
            raise ApiError('Monitoring detail table missing product_id column', status_code=500, code='schema_missing')

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

        stores_columns = get_table_columns(conn, 'stores')
        if 'nickname' in stores_columns:
            store_name_column = 'nickname'
        elif 'store_name' in stores_columns:
            store_name_column = 'store_name'
        elif 'name' in stores_columns:
            store_name_column = 'name'
        else:
            store_name_column = None

        stock_card_columns = get_table_columns(conn, 'stock_cards')
        stock_date_column = 'date' if 'date' in stock_card_columns else 'created_at'
        has_for_column = 'for' in stock_card_columns
        has_store_column = 'store_id' in stock_card_columns

        product_unit_select = (
            f"pu.`{unit_column}` AS product_unit_name"
            if unit_column else
            "NULL AS product_unit_name"
        )
        category_filter = (
            "WHERE sm.`category` = 'storage'"
            if 'category' in sm_columns else
            ''
        )
        remaining_for_filter = (
            "LOWER(REPLACE(REPLACE(TRIM(sc.`for`), '_', ' '), '-', ' ')) = 'remaining storage'"
            if has_for_column else
            "1 = 1"
        )
        date_filter_sql = (
            f"AND DATE(sc.`{stock_date_column}`) = :selected_date"
            if selected_date else
            ''
        )

        monitoring_query = build_monitoring_query(
            smd_table=smd_table,
            smd_monitoring_fk=smd_monitoring_fk,
            coefficient_expr=coefficient_expr,
            product_unit_select=product_unit_select,
            category_filter=category_filter,
            remaining_for_filter=remaining_for_filter,
            date_filter_sql=date_filter_sql,
            stock_date_column=stock_date_column,
        )
        rows_raw = conn.execute(monitoring_query, {'selected_date': selected_date}).fetchall()

        all_store_query = build_all_store_query(
            store_name_column=store_name_column,
            stores_columns=stores_columns,
            has_store_column=has_store_column,
        )
        all_store_rows = conn.execute(all_store_query).fetchall() if all_store_query is not None else []

        if selected_date and has_store_column:
            reported_store_rows = conn.execute(
                build_reported_store_query(remaining_for_filter, stock_date_column),
                {'selected_date': selected_date}
            ).fetchall()
        else:
            reported_store_rows = []

        grouped = {}
        for row in rows_raw:
            d = row._mapping
            monitoring_id = d.get('monitoring_id')
            if monitoring_id is None:
                continue

            if monitoring_id not in grouped:
                grouped[monitoring_id] = {
                    'monitoring_id': monitoring_id,
                    'monitoring_name': d.get('monitoring_name'),
                    'category': d.get('category'),
                    'quantity_low': _to_float(d.get('quantity_low'), 0.0),
                    'total_stock': 0.0,
                    'unit_name': '',
                    'detail_count': 0,
                    'latest_stock_card_date': None,
                    'product_details': []
                }

            group_item = grouped[monitoring_id]
            has_product = d.get('product_id') is not None
            if has_product:
                group_item['detail_count'] += 1

            unit_name = str(d.get('product_unit_name') or '').strip()
            if unit_name and not group_item['unit_name']:
                group_item['unit_name'] = unit_name

            remaining_raw = d.get('remaining_quantity')
            has_remaining_quantity = remaining_raw not in (None, '')
            remaining_quantity = _to_float(remaining_raw, 0.0)
            coefficient_value = _to_float(d.get('coefficient_value'), 1.0)
            weighted_quantity = remaining_quantity * coefficient_value if has_remaining_quantity else 0.0
            group_item['total_stock'] += weighted_quantity

            stock_card_date = to_iso_date(d.get('stock_card_date'))
            if stock_card_date and (
                group_item['latest_stock_card_date'] is None
                or stock_card_date > group_item['latest_stock_card_date']
            ):
                group_item['latest_stock_card_date'] = stock_card_date

            if has_product:
                group_item['product_details'].append({
                    'product_id': d.get('product_id'),
                    'product_name': d.get('product_name'),
                    'quantity': remaining_quantity if has_remaining_quantity else None,
                    'coefficient': coefficient_value,
                    'weighted_quantity': weighted_quantity if has_remaining_quantity else None,
                    'unit_name': unit_name or None,
                    'stock_card_date': stock_card_date
                })

        rows = []
        for item in grouped.values():
            if item['detail_count'] == 0:
                status = 'no_data'
            elif item['total_stock'] < item['quantity_low']:
                status = 'low'
            else:
                status = 'ok'

            product_summary = [
                str(detail.get('product_name') or '').strip()
                for detail in item['product_details']
                if str(detail.get('product_name') or '').strip()
            ]

            rows.append({
                'monitoring_id': item['monitoring_id'],
                'monitoring_name': item['monitoring_name'],
                'category': item['category'],
                'unit_name': item['unit_name'],
                'quantity_low': item['quantity_low'],
                'total_stock': item['total_stock'],
                'status': status,
                'detail_count': item['detail_count'],
                'latest_stock_card_date': item['latest_stock_card_date'],
                'sample_products': product_summary[:3],
                'product_details': item['product_details']
            })

        rows.sort(
            key=lambda item: (
                _to_float(item.get('total_stock'), 0.0),
                item.get('latest_stock_card_date') or ''
            ),
            reverse=True
        )
        limited_rows = rows[:limit]

        total_monitored = len(rows)
        low_count = sum(1 for item in rows if item.get('status') == 'low')
        safe_count = sum(1 for item in rows if item.get('status') == 'ok')
        missing_count = sum(1 for item in rows if item.get('status') == 'no_data')
        as_of_dates = [item.get('latest_stock_card_date') for item in rows if item.get('latest_stock_card_date')]
        as_of_date = max(as_of_dates) if as_of_dates else None

        all_stores = []
        for mapping in serialize_result_rows(all_store_rows):
            row_store_id = str(mapping.get('store_id') or '').strip()
            if not row_store_id:
                continue
            row_store_name = str(mapping.get('store_name') or '').strip() or row_store_id
            all_stores.append({
                'store_id': row_store_id,
                'store_name': row_store_name
            })

        reported_store_ids = {
            str(row.get('store_id') or '').strip()
            for row in serialize_result_rows(reported_store_rows)
            if str(row.get('store_id') or '').strip()
        }
        missing_report_stores = []
        if selected_date and has_store_column:
            for store in all_stores:
                if store['store_id'] not in reported_store_ids:
                    missing_report_stores.append(store)

    return jsonify({
        'success': True,
        'summary': {
            'total_monitored': total_monitored,
            'low_count': low_count,
            'safe_count': safe_count,
            'missing_count': missing_count,
            'as_of_date': as_of_date,
            'selected_date': selected_date,
            'missing_report_store_count': len(missing_report_stores)
        },
        'items': limited_rows,
        'missing_report_stores': missing_report_stores
    })
