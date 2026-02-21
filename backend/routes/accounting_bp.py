import uuid
import io
import pandas as pd
import xml.etree.ElementTree as ET
from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, date
from sqlalchemy import text
from decimal import Decimal
from backend.db.session import get_db_engine
from backend.services.report_service import (
    fetch_balance_sheet_data,
    fetch_income_statement_data,
    fetch_monthly_revenue_data,
    fetch_cash_flow_data,
    fetch_payroll_salary_summary_data
)

accounting_bp = Blueprint('accounting_bp', __name__)


def _table_columns(conn, table_name):
    if conn.dialect.name == 'sqlite':
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return {str(row[1]) for row in rows}

    rows = conn.execute(text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
    """), {'table_name': table_name}).fetchall()
    return {str(row[0]) for row in rows}


def _split_parent_exclusion_clause(conn, alias='t'):
    txn_columns = _table_columns(conn, 'transactions')
    if 'parent_id' not in txn_columns:
        return ''
    return f" AND NOT EXISTS (SELECT 1 FROM transactions t_child WHERE t_child.parent_id = {alias}.id)"

@accounting_bp.route('/api/coa', methods=['GET'])
def get_chart_of_accounts():
    """Get all Chart of Accounts entries"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM chart_of_accounts 
                WHERE is_active = TRUE
                ORDER BY code ASC
            """))
            coa_list = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                coa_list.append(d)
            return jsonify({'coa': coa_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@accounting_bp.route('/api/coa', methods=['POST'])
def create_coa():
    """Create a new COA entry"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        code = data.get('code')
        name = data.get('name')
        category = data.get('category')
        
        if not all([code, name, category]):
            return jsonify({'error': 'Code, name, and category are required'}), 400
        
        coa_id = str(uuid.uuid4())
        now = datetime.now()
        
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO chart_of_accounts 
                (id, code, name, category, subcategory, description, is_active, parent_id, created_at, updated_at)
                VALUES (:id, :code, :name, :category, :subcategory, :description, :is_active, :parent_id, :created_at, :updated_at)
            """), {
                'id': coa_id,
                'code': code,
                'name': name,
                'category': category,
                'subcategory': data.get('subcategory'),
                'description': data.get('description'),
                'is_active': data.get('is_active', True),
                'parent_id': data.get('parent_id'),
                'created_at': now,
                'updated_at': now
            })
            return jsonify({'message': 'COA created successfully', 'id': coa_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@accounting_bp.route('/api/reports/income-statement', methods=['GET'])
def get_income_statement():
    """Generate Income Statement (Laba Rugi)"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        now = datetime.now()
        start_date = request.args.get('start_date') or f"{now.year}-01-01"
        end_date = request.args.get('end_date') or now.strftime('%Y-%m-%d')
        company_id = request.args.get('company_id')
        
        with engine.connect() as conn:
            data = fetch_income_statement_data(conn, start_date, end_date, company_id)
            data['period'] = {'start_date': start_date, 'end_date': end_date}
            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@accounting_bp.route('/api/reports/balance-sheet', methods=['GET'])
def get_balance_sheet():
    """Generate Balance Sheet (Neraca)"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        as_of_date = request.args.get('date') or request.args.get('as_of_date') or datetime.now().strftime('%Y-%m-%d')
        company_id = request.args.get('company_id')

        with engine.connect() as conn:
            data = fetch_balance_sheet_data(conn, as_of_date, company_id)
            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@accounting_bp.route('/api/reports/monthly-revenue', methods=['GET'])
def get_monthly_revenue():
    """Get monthly revenue summary for a specific year"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
        
    try:
        year = request.args.get('year')
        company_id = request.args.get('company_id')
        
        if not year:
            year = datetime.now().year
        else:
            year = int(year)
            
        with engine.connect() as conn:
            current_data = fetch_monthly_revenue_data(conn, year, company_id)
            prev_data = fetch_monthly_revenue_data(conn, year - 1, company_id)
            return jsonify({
                'year': year, 
                'data': current_data,
                'prev_year_data': prev_data
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@accounting_bp.route('/api/reports/cash-flow', methods=['GET'])
def get_cash_flow():
    """Generate Cash Flow statement"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        now = datetime.now()
        start_date = request.args.get('start_date') or f"{now.year}-01-01"
        end_date = request.args.get('end_date') or now.strftime('%Y-%m-%d')
        company_id = request.args.get('company_id')

        with engine.connect() as conn:
            data = fetch_cash_flow_data(conn, start_date, end_date, company_id)
            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@accounting_bp.route('/api/reports/payroll-salary-summary', methods=['GET'])
def get_payroll_salary_summary():
    """Generate payroll salary summary grouped by month, employee, and mark."""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        now = datetime.now()
        start_date = request.args.get('start_date') or f"{now.year}-01-01"
        end_date = request.args.get('end_date') or now.strftime('%Y-%m-%d')
        company_id = request.args.get('company_id')

        with engine.connect() as conn:
            data = fetch_payroll_salary_summary_data(conn, start_date, end_date, company_id)
            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@accounting_bp.route('/api/reports/coa-detail', methods=['GET'])
def get_coa_detail_report():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        coa_id = request.args.get('coa_id')
        as_of_date = request.args.get('as_of_date')
        
        # Determine date range based on account category - need to get COA info first
        temp_coa_id = request.args.get('coa_id')
        if not temp_coa_id:
            with engine.connect() as conn:
                first_coa = conn.execute(text("SELECT id FROM chart_of_accounts WHERE is_active = TRUE LIMIT 1")).fetchone()
                if not first_coa:
                    return jsonify({'error': 'coa_id is required'}), 400
                temp_coa_id = first_coa[0]
        
        with engine.connect() as conn:
            coa_result = conn.execute(text("SELECT * FROM chart_of_accounts WHERE id = :id"), {'id': temp_coa_id})
            coa_row = coa_result.fetchone()
            if not coa_row:
                return jsonify({'error': 'COA not found'}), 404
            
            coa_info = dict(coa_row._mapping)
            coa_category = coa_info.get('category', '')

        coa_id = temp_coa_id
        
        if as_of_date:
            if coa_category in ('ASSET', 'LIABILITY', 'EQUITY'):
                # For balance sheet accounts: from beginning of time to as_of_date
                start_date = None
                end_date = as_of_date
            else:
                # For income statement accounts: from beginning of the as_of_date year to as_of_date
                as_of_year = datetime.strptime(as_of_date, '%Y-%m-%d').year
                start_date = f"{as_of_year}-01-01"
                end_date = as_of_date
        else:
            start_date = request.args.get('start_date') or f"{datetime.now().year}-01-01"
            end_date = request.args.get('end_date') or datetime.now().strftime('%Y-%m-%d')
        
        company_id = request.args.get('company_id')
        
        if not coa_id:
            with engine.connect() as conn:
                first_coa = conn.execute(text("SELECT id FROM chart_of_accounts WHERE is_active = TRUE LIMIT 1")).fetchone()
                if not first_coa:
                    return jsonify({'error': 'coa_id is required'}), 400
                coa_id = first_coa[0]
        
        with engine.connect() as conn:
            coa_result = conn.execute(text("SELECT * FROM chart_of_accounts WHERE id = :id"), {'id': coa_id})
            coa_row = coa_result.fetchone()
            if not coa_row:
                return jsonify({'error': 'COA not found'}), 404
            
            coa_info = dict(coa_row._mapping)
            coa_category = coa_info.get('category', '')
            split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')

            query = text(f"""
                SELECT 
                    t.id, t.txn_date, t.description, t.amount, t.db_cr,
                    m.personal_use as mark_name, c.name as company_name, mcm.mapping_type
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
                LEFT JOIN companies c ON t.company_id = c.id
                WHERE mcm.coa_id = :coa_id
                  AND (:start_date IS NULL OR t.txn_date >= :start_date)
                  AND (:end_date IS NULL OR t.txn_date <= :end_date)
                  AND (:company_id IS NULL OR t.company_id = :company_id)
                  {split_exclusion_clause}
                ORDER BY t.txn_date DESC
            """)

            result = conn.execute(query, {
                'coa_id': coa_id,
                'start_date': start_date,
                'end_date': end_date,
                'company_id': company_id
            })

            transactions = []
            total = 0
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, Decimal):
                        d[key] = float(value)

                amount = float(d['amount'])

                # For Balance Sheet accounts (ASSET, LIABILITY, EQUITY):
                # - DEBIT mapping = positive (increases balance)
                # - CREDIT mapping = negative (decreases balance)
                # For Income Statement accounts (REVENUE, EXPENSE):
                # - Use DB/CR + mapping_type logic
                if coa_category in ('ASSET', 'LIABILITY', 'EQUITY'):
                    if d['mapping_type'] == 'DEBIT':
                        effective_amount = amount
                    else:  # CREDIT
                        effective_amount = -amount
                else:
                    # Income Statement logic
                    if (d['db_cr'] == 'CR' and d['mapping_type'] == 'CREDIT') or \
                       (d['db_cr'] == 'DB' and d['mapping_type'] == 'DEBIT'):
                        effective_amount = amount
                    else:
                        effective_amount = -amount

                d['effective_amount'] = effective_amount
                total += effective_amount
                transactions.append(d)
            
            return jsonify({
                'coa': {'code': coa_info['code'], 'name': coa_info['name'], 'category': coa_info['category']},
                'transactions': transactions,
                'total': total
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@accounting_bp.route('/api/inventory-balances', methods=['GET'])
@accounting_bp.route('/api/reports/inventory-balances', methods=['GET'])
def get_inventory_balances():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
        
    try:
        year = request.args.get('year') or datetime.now().year
        company_id = request.args.get('company_id')
        
        if not company_id:
            return jsonify({'error': 'company_id is required'}), 400
            
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM inventory_balances WHERE year = :year AND company_id = :company"),
                {'year': year, 'company': company_id}
            )
            row = result.fetchone()
            if row:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, Decimal):
                        d[key] = float(value)
                    elif isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                return jsonify({'balance': d})
            return jsonify({'balance': {}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@accounting_bp.route('/api/reports/prepaid-expenses', methods=['GET'])
def get_prepaid_expenses():
    return jsonify({
        'items': [],
        'message': 'Prepaid Rent & Amortization feature has been retired'
    })

@accounting_bp.route('/api/reports/prepaid-linkable-transactions', methods=['GET'])
@accounting_bp.route('/api/reports/prepaid-eligible-transactions', methods=['GET'])
def get_prepaid_linkable_transactions():
    return jsonify({
        'transactions': [],
        'message': 'Prepaid Rent & Amortization feature has been retired'
    })
