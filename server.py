import os
from flask import Flask
from flask_cors import CORS
from migrate import run_migrations
from backend.routes.transaction_bp import transaction_bp
from backend.routes.company_bp import company_bp
from backend.routes.accounting_bp import accounting_bp
from backend.routes.amortization_bp import amortization_bp
from backend.routes.pdf_bp import pdf_bp
from backend.routes.pdf_bp import pdf_bp
from backend.routes.rental_bp import rental_bp
from backend.routes.hpp_bp import hpp_bp
from backend.routes.initial_capital_bp import initial_capital_bp
from backend.routes.general_ledger_bp import general_ledger_bp

app = Flask(__name__)
# Configure CORS
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "expose_headers": "*"}})

# Configure upload folder
UPLOAD_FOLDER = 'pdfs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Register Blueprints
app.register_blueprint(transaction_bp)
app.register_blueprint(company_bp)
app.register_blueprint(accounting_bp)
app.register_blueprint(amortization_bp)
app.register_blueprint(pdf_bp)
app.register_blueprint(rental_bp)
app.register_blueprint(hpp_bp)
app.register_blueprint(initial_capital_bp)
app.register_blueprint(general_ledger_bp)


if __name__ == '__main__':
    # Run migrations on startup
    run_migrations()
    
    # Get port from environment variable with a default of 5001
    port = int(os.environ.get('PORT', 5001))
    # In production, disable debug mode
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
