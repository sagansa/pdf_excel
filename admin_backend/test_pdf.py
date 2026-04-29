from backend.services.reporting.income_statement_service import fetch_income_statement_data
from backend.services.reporting.pdf_service import generate_income_statement_pdf
from backend.routes.accounting_utils import require_db_engine
from server import app
import traceback

def test():
    with app.app_context():
        try:
            engine = require_db_engine()
            with engine.connect() as conn:
                data = fetch_income_statement_data(conn, '2025-01-01', '2025-12-31', '8ab69d4a-e591-4f05-909e-25ff12352efb', 'real', False)
                data['settings'] = {}
                data['period'] = {'start_date': '2025-01-01', 'end_date': '2025-12-31'}
                data['company_name'] = 'Test'
                generate_income_statement_pdf(data)
                print("SUCCESS")
        except Exception as e:
            traceback.print_exc()

if __name__ == '__main__':
    test()
