import os
from datetime import date, timedelta
from flask import Blueprint, request, jsonify
from backend.errors import ApiError, BadRequestError, ServiceUnavailableError
from backend.db.session import get_sagansa_engine

sales_by_date_bp = Blueprint('sales_by_date_bp', __name__)

DEFAULT_SALES_BY_DATE_API_URL = os.environ.get(
    'SAGANSA_SALES_BY_DATE_API_URL',
    'https://superadmin.sagansa.id/api/detail-sales-orders/sales-by-date'
)
DEFAULT_SALES_BY_DATE_TOKEN = os.environ.get(
    'SAGANSA_SALES_BY_DATE_TOKEN',
    ''
)


def _require_sales_by_date_token(token):
    if not token:
        raise BadRequestError(
            'Missing API token for Sales by Date. Provide `token` query parameter.',
            code='sales_by_date_token_missing'
        )


def _handle_sales_by_date_remote_error(exc):
    message = str(exc)
    status_code = getattr(exc, 'code', 500)
    if status_code == 401:
        message = 'Invalid token for Sales by Date API'
        raise BadRequestError(message, code='sales_by_date_token_invalid')
    if status_code == 403:
        message = 'Access denied to Sales by Date API'
        raise BadRequestError(message, code='sales_by_date_forbidden')
    if status_code == 404:
        message = 'Sales by Date endpoint not found'
        raise ServiceUnavailableError(message, code='sales_by_date_not_found')
    if status_code >= 500:
        message = 'Sales by Date API is unavailable'
        raise ServiceUnavailableError(message, code='sales_by_date_unavailable')
    raise ApiError(message, status_code=502, code='sales_by_date_remote_error')


from backend.routes.route_utils import _fetch_remote_json

def _fetch_sales_by_date(api_url, token, selected_date):
    try:
        payload = _fetch_remote_json(
            api_url=api_url,
            token=token,
            query_params={'date': selected_date},
            resource_name='Sales by Date API'
        )
        if not payload.get('success'):
            raise ApiError('Sales by Date API returned unsuccessful response', status_code=502, code='sales_by_date_error')
        return payload.get('data', [])
    except RuntimeError as exc:
        _handle_sales_by_date_remote_error(exc)


def _normalize_iso_date(raw_date):
    if not raw_date:
        return None
    raw_date = str(raw_date).strip()
    if not raw_date:
        return None
    try:
        parsed = date.fromisoformat(raw_date)
        return parsed.isoformat()
    except ValueError:
        return None


@sales_by_date_bp.route('/api/dashboard/sales-by-date', methods=['GET'])
def get_dashboard_sales_by_date():
    api_url = str(request.args.get('api_url') or DEFAULT_SALES_BY_DATE_API_URL).strip()
    token = str(
        request.args.get('token')
        or request.args.get('access_token')
        or request.args.get('api_token')
        or DEFAULT_SALES_BY_DATE_TOKEN
        or ''
    ).strip()
    _require_sales_by_date_token(token)

    engine = get_sagansa_engine()

    raw_date = request.args.get('date')
    if raw_date in (None, ''):
        selected_date = (date.today() - timedelta(days=1)).isoformat()
    else:
        selected_date = _normalize_iso_date(raw_date)
    if raw_date not in (None, '') and not selected_date:
        raise BadRequestError('date must use YYYY-MM-DD format')

    remote_data = _fetch_sales_by_date(
        api_url=api_url,
        token=token,
        selected_date=selected_date,
    )

    result = {
        'success': True,
        'date': selected_date,
        'data': remote_data,
    }

    return jsonify(result)
