import os
from datetime import date, timedelta
from flask import Blueprint, request, jsonify
from backend.errors import ApiError, BadRequestError, ServiceUnavailableError
from backend.db.session import get_sagansa_engine

stock_comparison_bp = Blueprint('stock_comparison_bp', __name__)

DEFAULT_STOCK_COMPARISON_API_URL = os.environ.get(
    'SAGANSA_STOCK_COMPARISON_API_URL',
    'https://superadmin.sagansa.id/api/detail-stock-cards/compare-periods'
)
DEFAULT_STOCK_COMPARISON_TOKEN = os.environ.get(
    'SAGANSA_STOCK_COMPARISON_TOKEN',
    '6091|gLEyp5W0Y0QsKvCw8N8AA0opr8247BoUv0RYV2jyd76f2048'
)


def _require_stock_comparison_token(token):
    if not token:
        raise BadRequestError(
            'Missing API token for Stock Comparison. Provide `token` query parameter.',
            code='stock_comparison_token_missing'
        )


def _handle_stock_comparison_remote_error(exc):
    message = str(exc)
    status_code = getattr(exc, 'code', 500)
    if status_code == 401:
        message = 'Invalid token for Stock Comparison API'
        raise BadRequestError(message, code='stock_comparison_token_invalid')
    if status_code == 403:
        message = 'Access denied to Stock Comparison API'
        raise BadRequestError(message, code='stock_comparison_forbidden')
    if status_code == 404:
        message = 'Stock Comparison endpoint not found'
        raise ServiceUnavailableError(message, code='stock_comparison_not_found')
    if status_code >= 500:
        message = 'Stock Comparison API is unavailable'
        raise ServiceUnavailableError(message, code='stock_comparison_unavailable')
    raise ApiError(message, status_code=502, code='stock_comparison_remote_error')


from backend.routes.route_utils import _fetch_remote_json

def _fetch_stock_comparison(api_url, token, from_date, to_date):
    try:
        payload = _fetch_remote_json(
            api_url=api_url,
            token=token,
            query_params={'from_date': from_date, 'to_date': to_date},
            resource_name='Stock Comparison API'
        )
        if not payload.get('success'):
            raise ApiError('Stock Comparison API returned unsuccessful response', status_code=502, code='stock_comparison_error')
        return payload
    except RuntimeError as exc:
        _handle_stock_comparison_remote_error(exc)


@stock_comparison_bp.route('/api/stock-comparison', methods=['GET'])
def get_stock_comparison():
    api_url = str(request.args.get('api_url') or DEFAULT_STOCK_COMPARISON_API_URL).strip()
    token = str(
        request.args.get('token')
        or request.args.get('access_token')
        or request.args.get('api_token')
        or DEFAULT_STOCK_COMPARISON_TOKEN
        or ''
    ).strip()
    _require_stock_comparison_token(token)

    engine = get_sagansa_engine()

    raw_from_date = request.args.get('from_date')
    raw_to_date = request.args.get('to_date')
    
    if raw_from_date in (None, ''):
        from_date = (date.today() - timedelta(days=1)).isoformat()
    else:
        from_date = str(raw_from_date).strip()
    
    if raw_to_date in (None, ''):
        to_date = date.today().isoformat()
    else:
        to_date = str(raw_to_date).strip()

    try:
        remote_data = _fetch_stock_comparison(
            api_url=api_url,
            token=token,
            from_date=from_date,
            to_date=to_date
        )
        
        return jsonify({
            'success': True,
            'data': remote_data.get('data', []),
            'summary': remote_data.get('summary', {})
        })
    except Exception as e:
        raise e
