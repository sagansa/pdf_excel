import logging
import os
import secrets
from datetime import timedelta
from pathlib import Path
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from migrate import run_migrations
from backend.error_handlers import register_error_handlers
from backend.routes.auth_bp import auth_bp, get_user_if_active
from backend.routes.transactions.service_bp import service_bp
from backend.routes.master_data.company_bp import company_bp
from backend.routes.master_data.coa_bp import coa_bp
from backend.routes.reporting.report_bp import report_bp
from backend.routes.inventory.inventory_bp import inventory_bp
from backend.routes.amortization.amortization_item_bp import amortization_item_bp
from backend.routes.amortization.amortization_asset_bp import amortization_asset_bp
from backend.routes.amortization.amortization_config_bp import amortization_config_bp
from backend.routes.uploads.pdf_bp import pdf_bp
from backend.routes.integrations.n8n_bp import integrations_bp
from backend.routes.rental.rental_location_bp import rental_location_bp
from backend.routes.rental.rental_store_bp import rental_store_bp
from backend.routes.rental.rental_contract_bp import rental_contract_bp
from backend.routes.inventory.hpp_bp import hpp_bp
from backend.routes.master_data.initial_capital_bp import initial_capital_bp
from backend.routes.reporting.general_ledger_bp import general_ledger_bp
from backend.routes.inventory.remaining_storage_bp import remaining_storage_bp
from backend.routes.inventory.sales_by_date_bp import sales_by_date_bp
from backend.routes.inventory.stock_comparison_bp import stock_comparison_bp
from backend.routes.transactions.history_bp import history_bp
from backend.routes.transactions.ai_bp import ai_bp
from backend.routes.transactions.payroll_bp import payroll_bp
from backend.routes.master_data.mark_bp import mark_bp
from backend.routes.reporting.fiscal_corrections_bp import fiscal_corrections_bp

app = Flask(__name__)
register_error_handlers(app)

logger = logging.getLogger(__name__)

# Session configuration (HttpOnly signed cookie).
# In production (FLASK_ENV != development) a missing SECRET_KEY is fatal: fail closed.
_secret_key = os.environ.get('SECRET_KEY', '').strip()
if not _secret_key:
    if os.environ.get('FLASK_ENV') == 'development':
        _secret_key = secrets.token_hex(32)
        logger.warning('SECRET_KEY not set; using an ephemeral key (sessions reset on restart).')
    else:
        raise SystemExit('SECRET_KEY must be set (add it to admin_backend/.env).')

app.config['SECRET_KEY'] = _secret_key
app.config.update(
    SESSION_COOKIE_NAME='esta_session',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', '').strip().lower()
    in {'1', 'true', 'yes'},
)

# CORS: same-origin by default (SPA + API are served by this app; dev uses the vite proxy).
# Set CORS_ORIGINS (comma separated) only if a cross-origin client is really needed.
_cors_origins = [o.strip() for o in os.environ.get('CORS_ORIGINS', '').split(',') if o.strip()]
if _cors_origins:
    CORS(app, resources={r"/*": {"origins": _cors_origins, "expose_headers": "*"}})

# Configure upload folder
UPLOAD_FOLDER = BASE_DIR / "pdfs"
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Register Blueprints
app.register_blueprint(service_bp)
app.register_blueprint(company_bp)
app.register_blueprint(coa_bp)
app.register_blueprint(report_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(amortization_item_bp)
app.register_blueprint(amortization_asset_bp)
app.register_blueprint(amortization_config_bp)
app.register_blueprint(pdf_bp)
app.register_blueprint(integrations_bp)
app.register_blueprint(rental_location_bp)
app.register_blueprint(rental_store_bp)
app.register_blueprint(rental_contract_bp)
app.register_blueprint(hpp_bp)
app.register_blueprint(initial_capital_bp)
app.register_blueprint(general_ledger_bp)
app.register_blueprint(remaining_storage_bp)
app.register_blueprint(sales_by_date_bp)
app.register_blueprint(stock_comparison_bp)
app.register_blueprint(history_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(payroll_bp)
app.register_blueprint(mark_bp)
app.register_blueprint(fiscal_corrections_bp)
app.register_blueprint(auth_bp)


# Global auth guard: every /api/* route requires a logged-in session.
# Non-API paths (SPA shell and assets) stay public so the login page can load;
# data protection happens at the API layer.
PUBLIC_API_PATHS = {
    '/api/auth/login',
    '/api/auth/forgot-password',
    '/api/auth/reset-password',
    # Integrasi n8n: tanpa session — diautentikasi API key di blueprint-nya.
    '/api/integrations/statement',
    '/api/integrations/statement-check',
}


@app.before_request
def require_login():
    if request.method == 'OPTIONS':
        return None
    if not request.path.startswith('/api/'):
        return None
    if request.path in PUBLIC_API_PATHS:
        return None
    user = get_user_if_active(session.get('user_id'))
    if user is None or session.get('credential_version') != int(user['credential_version']):
        session.clear()
        return jsonify({'error': 'Authentication required', 'code': 'not_authenticated'}), 401
    return None


if __name__ == '__main__':
    # Run migrations on startup
    if not run_migrations():
        raise SystemExit(1)
    
    # Get port from environment variable with a default of 5001
    port = int(os.environ.get('PORT', 5001))
    # In production, disable debug mode
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
