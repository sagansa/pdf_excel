import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from backend.errors import ApiError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return jsonify({
            'error': error.description,
            'code': str(error.name or 'http_error').lower().replace(' ', '_')
        }), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        logger.exception('Unhandled exception during request', exc_info=error)
        return jsonify({
            'error': 'Internal server error',
            'code': 'internal_server_error'
        }), 500
