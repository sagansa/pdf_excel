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


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fetch_inventory_balance_row(conn, year, company_id):
    result = conn.execute(text("""
        SELECT *
        FROM inventory_balances
        WHERE year = :year AND company_id = :company_id
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
    """), {
        'year': int(year),
        'company_id': company_id
    })
    row = result.fetchone()
    return dict(row._mapping) if row else None


def _serialize_inventory_balance(row_dict):
    if not row_dict:
        return {}
    serialized = {}
    for key, value in row_dict.items():
        if isinstance(value, Decimal):
            serialized[key] = float(value)
        elif isinstance(value, datetime):
            serialized[key] = value.strftime('%Y-%m-%d %H:%M:%S')
        else:
            serialized[key] = value
    return serialized


def _build_inventory_balance_with_carry(conn, year, company_id):
    year = int(year)
    current = _serialize_inventory_balance(_fetch_inventory_balance_row(conn, year, company_id))
    previous = _serialize_inventory_balance(_fetch_inventory_balance_row(conn, year - 1, company_id))

    prev_ending_amount = _to_float(previous.get('ending_inventory_amount')) if previous else 0.0
    prev_ending_qty = _to_float(previous.get('ending_inventory_qty')) if previous else 0.0

    if not current:
        if abs(prev_ending_amount) < 0.000001 and abs(prev_ending_qty) < 0.000001:
            return {}
        return {
            'id': None,
            'company_id': company_id,
            'year': year,
            'beginning_inventory_amount': prev_ending_amount,
            'beginning_inventory_qty': prev_ending_qty,
            'ending_inventory_amount': 0.0,
            'ending_inventory_qty': 0.0,
            'base_value': prev_ending_amount,
            'is_manual': True,
            'is_carry_forward': True,
            'carried_from_year': year - 1
        }

    current_beginning_amount = _to_float(current.get('beginning_inventory_amount'))
    current_beginning_qty = _to_float(current.get('beginning_inventory_qty'))
    carry_allowed = (
        abs(current_beginning_amount) < 0.000001 and
        abs(current_beginning_qty) < 0.000001 and
        (abs(prev_ending_amount) >= 0.000001 or abs(prev_ending_qty) >= 0.000001)
    )

    if carry_allowed:
        current['beginning_inventory_amount'] = prev_ending_amount
        current['beginning_inventory_qty'] = prev_ending_qty
        current['is_carry_forward'] = True
        current['carried_from_year'] = year - 1
    else:
        current['is_carry_forward'] = False
        current['carried_from_year'] = None

    if 'is_manual' not in current:
        current['is_manual'] = True
    return current

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
        report_type = request.args.get('report_type', 'real')
        comparative = request.args.get('comparative', 'false').lower() == 'true'

        with engine.connect() as conn:
            data = fetch_income_statement_data(conn, start_date, end_date, company_id, report_type, comparative=comparative)
            data['period'] = {'start_date': start_date, 'end_date': end_date}
            data['comparative'] = comparative
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
        report_type = request.args.get('report_type', 'real')

        with engine.connect() as conn:
            data = fetch_balance_sheet_data(conn, as_of_date, company_id, report_type)
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
        report_type = request.args.get('report_type', 'real')
            
        with engine.connect() as conn:
            current_data = fetch_monthly_revenue_data(conn, year, company_id, report_type)
            prev_data = fetch_monthly_revenue_data(conn, year - 1, company_id, report_type)
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
        report_type = request.args.get('report_type', 'real')

        with engine.connect() as conn:
            data = fetch_cash_flow_data(conn, start_date, end_date, company_id, report_type)
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
        report_type = request.args.get('report_type', 'real')

        with engine.connect() as conn:
            data = fetch_payroll_salary_summary_data(conn, start_date, end_date, company_id, report_type)
            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@accounting_bp.route('/api/reports/available-years', methods=['GET'])
def get_available_report_years():
    """Get available transaction years for reports filter."""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    try:
        company_id = request.args.get('company_id')

        with engine.connect() as conn:
            split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
            if conn.dialect.name == 'sqlite':
                year_expr = "CAST(strftime('%Y', t.txn_date) AS INTEGER)"
            else:
                year_expr = "YEAR(t.txn_date)"

            query = text(f"""
                SELECT DISTINCT {year_expr} AS year
                FROM transactions t
                WHERE t.txn_date IS NOT NULL
                  AND (:company_id IS NULL OR t.company_id = :company_id)
                  {split_exclusion_clause}
                ORDER BY year DESC
            """)

            years = []
            for row in conn.execute(query, {'company_id': company_id}):
                try:
                    year_val = int(row.year)
                    if year_val > 0:
                        years.append(year_val)
                except (TypeError, ValueError):
                    continue

            if not years:
                years = [datetime.now().year]

            return jsonify({'years': years})
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

            txn_columns = _table_columns(conn, 'transactions')
            npwp_expr = "t.service_npwp" if 'service_npwp' in txn_columns else "NULL"
            method_expr = "COALESCE(t.service_calculation_method, 'BRUTO')" if 'service_calculation_method' in txn_columns else "'BRUTO'"
            
            query = text(f"""
                SELECT 
                    t.id, t.txn_date, t.description, t.amount, t.db_cr,
                    m.personal_use as mark_name, m.is_service, c.name as company_name, mcm.mapping_type,
                    {npwp_expr} AS service_npwp,
                    {method_expr} AS service_calculation_method
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
                
                # Apply service tax gross-up for Income Statement reports
                if coa_category in ('EXPENSE', 'REVENUE'):
                    is_service = str(d.get('is_service', '0')).lower() in ('1', 'true', 'yes', 'y')
                    has_npwp_col = d.get('service_npwp') is not None
                    
                    if is_service or has_npwp_col:
                        npwp_digits = ''.join(ch for ch in str(d.get('service_npwp') or '') if ch.isdigit())
                        has_npwp = len(npwp_digits) == 15
                        tax_rate = 2.0 if has_npwp else 4.0
                        
                        amount_abs = abs(float(d['amount']))
                        method = str(d.get('service_calculation_method') or 'BRUTO').strip().upper()
                        
                        tax_to_add = 0.0
                        if method == 'NETTO':
                            divisor = max(0.000001, 1.0 - (tax_rate / 100.0))
                            tax_to_add = (amount_abs / divisor) - amount_abs
                        else:
                            tax_to_add = amount_abs * (tax_rate / 100.0)
                            
                        if tax_to_add > 0:
                            # If it's a positive effective_amount (standard expense), add tax.
                            # If it's negative (reversal), subtract tax.
                            if d['effective_amount'] >= 0:
                                d['effective_amount'] += tax_to_add
                            else:
                                d['effective_amount'] -= tax_to_add
                            
                            # Update the base amount as well for display
                            d['amount'] = float(d['amount']) + (tax_to_add if d['amount'] >= 0 else -tax_to_add)

                total += d['effective_amount']
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
        year_raw = request.args.get('year') or datetime.now().year
        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            return jsonify({'error': 'year must be numeric'}), 400

        company_id = request.args.get('company_id')
        
        if not company_id:
            return jsonify({'error': 'company_id is required'}), 400
            
        with engine.connect() as conn:
            balance = _build_inventory_balance_with_carry(conn, year, company_id)
            return jsonify({'balance': balance})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@accounting_bp.route('/api/inventory-balances', methods=['POST'])
@accounting_bp.route('/api/reports/inventory-balances', methods=['POST'])
def save_inventory_balances():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    payload = request.json or {}
    
    # Validate required fields
    required_fields = ['year', 'company_id']
    for field in required_fields:
        if field not in payload:
            return jsonify({'error': f'{field} is required'}), 400
    
    try:
        year = int(payload.get('year'))
        company_id = payload.get('company_id')
        
        # Extract optional fields
        beginning_amount = _to_float(payload.get('beginning_inventory_amount'), 0.0)
        beginning_qty = _to_float(payload.get('beginning_inventory_qty'), 0.0)
        ending_amount = _to_float(payload.get('ending_inventory_amount'), 0.0)
        ending_qty = _to_float(payload.get('ending_inventory_qty'), 0.0)
        base_value = _to_float(payload.get('base_value'), 0.0)
        
        with engine.connect() as conn:
            from sqlalchemy import text
            from datetime import datetime
            import uuid
            
            now = datetime.now()
            
            # Check if record exists
            existing_query = text("""
                SELECT id FROM inventory_balances 
                WHERE year = :year AND company_id = :company_id
            """)
            existing = conn.execute(existing_query, {
                'year': year,
                'company_id': company_id
            }).fetchone()
            
            if existing:
                # Update existing record
                update_query = text("""
                    UPDATE inventory_balances SET
                        beginning_inventory_amount = :beginning_amount,
                        beginning_inventory_qty = :beginning_qty,
                        ending_inventory_amount = :ending_amount,
                        ending_inventory_qty = :ending_qty,
                        base_value = :base_value,
                        is_manual = 1,
                        updated_at = :updated_at
                    WHERE year = :year AND company_id = :company_id
                """)
                
                conn.execute(update_query, {
                    'beginning_amount': beginning_amount,
                    'beginning_qty': beginning_qty,
                    'ending_amount': ending_amount,
                    'ending_qty': ending_qty,
                    'base_value': base_value,
                    'year': year,
                    'company_id': company_id,
                    'updated_at': now
                })
                
                record_id = existing.id
                conn.commit()  # Commit the transaction!
                
            else:
                # Insert new record
                record_id = str(uuid.uuid4())
                insert_query = text("""
                    INSERT INTO inventory_balances (
                        id, company_id, year,
                        beginning_inventory_amount, beginning_inventory_qty,
                        ending_inventory_amount, ending_inventory_qty,
                        base_value, is_manual, created_at, updated_at
                    ) VALUES (
                        :id, :company_id, :year,
                        :beginning_amount, :beginning_qty,
                        :ending_amount, :ending_qty,
                        :base_value, 1, :created_at, :updated_at
                    )
                """)
                
                conn.execute(insert_query, {
                    'id': record_id,
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
                conn.commit()  # Commit transaction!
            
            # Auto-carry forward to next year if it doesn't exist
            next_year = year + 1
            next_check_query = text("""
                SELECT id FROM inventory_balances 
                WHERE year = :next_year AND company_id = :company_id
            """)
            next_existing = conn.execute(next_check_query, {
                'next_year': next_year,
                'company_id': company_id
            }).fetchone()
            
            if not next_existing:
                next_id = str(uuid.uuid4())
                insert_next_query = text("""
                    INSERT INTO inventory_balances (
                        id, company_id, year,
                        beginning_inventory_amount, beginning_inventory_qty,
                        ending_inventory_amount, ending_inventory_qty,
                        base_value, is_carry_forward, is_manual, created_at, updated_at
                    ) VALUES (
                        :id, :company_id, :year,
                        :beginning_amount, :beginning_qty,
                        0, 0,
                        :base_value, 1, 0, :created_at, :updated_at
                    )
                """)
                
                conn.execute(insert_next_query, {
                    'id': next_id,
                    'company_id': company_id,
                    'year': next_year,
                    'beginning_amount': ending_amount,
                    'beginning_qty': ending_qty,
                    'base_value': ending_amount,
                    'created_at': now,
                    'updated_at': now
                })
                conn.commit()  # Commit transaction for carry forward!
            
            # Get updated balance
            balance = _build_inventory_balance_with_carry(conn, year, company_id)
            
            return jsonify({
                'success': True,
                'message': 'Inventory balance saved successfully',
                'balance': balance
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@accounting_bp.route('/api/reports/marks-summary', methods=['GET'])
def get_marks_summary():
    """
    Get summary of debit and credit amounts grouped by mark.
    Bank accounting perspective:
    - DB (Debit) = Money IN (bank receives money)
    - CR (Credit) = Money OUT (bank pays money)
    Net = Debit - Credit (positive = more money in, negative = more money out)
    """
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        company_id = request.args.get('company_id')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400
        
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    m.id as mark_id,
                    m.personal_use as mark_name,
                    SUM(CASE 
                        WHEN t.db_cr = 'DB' THEN t.amount 
                        WHEN t.db_cr = 'CR' THEN 0 
                        ELSE 0 
                    END) as total_debit,
                    SUM(CASE 
                        WHEN t.db_cr = 'CR' THEN t.amount 
                        WHEN t.db_cr = 'DB' THEN 0 
                        ELSE 0 
                    END) as total_credit,
                    COUNT(t.id) as transaction_count
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                WHERE t.txn_date >= :start_date AND t.txn_date <= :end_date
                    AND (:company_id IS NULL OR t.company_id = :company_id)
                GROUP BY m.id, m.personal_use
                ORDER BY mark_name ASC
            """)
            
            result = conn.execute(query, {
                'start_date': start_date,
                'end_date': end_date,
                'company_id': company_id
            })
            
            marks = []
            total_debit_all = 0
            total_credit_all = 0
            
            for row in result:
                d = dict(row._mapping)
                total_debit = float(d['total_debit'] or 0)
                total_credit = float(d['total_credit'] or 0)
                
                total_debit_all += total_debit
                total_credit_all += total_credit
                
                # Bank accounting: Net = Debit - Credit
                # Positive = more money in (inflow)
                # Negative = more money out (outflow)
                net_amount = total_debit - total_credit
                
                marks.append({
                    'mark_id': d['mark_id'],
                    'mark_name': d['mark_name'] or 'Unnamed Mark',
                    'total_debit': total_debit,
                    'total_credit': total_credit,
                    'net_amount': net_amount,
                    'transaction_count': d['transaction_count']
                })
            
            # Calculate overall summary
            net_difference_all = total_debit_all - total_credit_all
            
            return jsonify({
                'marks': marks,
                'summary': {
                    'total_debit': total_debit_all,
                    'total_credit': total_credit_all,
                    'net_difference': net_difference_all,
                    'total_marks': len(marks)
                }
            })
            
    except Exception as e:
        import traceback
        print(f"Error in marks-summary: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500
    company_id = str(payload.get('company_id') or '').strip()
    if not company_id:
        return jsonify({'error': 'company_id is required'}), 400

    year_raw = payload.get('year')
    try:
        year = int(year_raw)
    except (TypeError, ValueError):
        return jsonify({'error': 'year must be numeric'}), 400

    beginning_amount = _to_float(payload.get('beginning_inventory_amount'), 0.0)
    beginning_qty = _to_float(payload.get('beginning_inventory_qty'), 0.0)
    ending_amount = _to_float(payload.get('ending_inventory_amount'), 0.0)
    ending_qty = _to_float(payload.get('ending_inventory_qty'), 0.0)
    base_value = _to_float(payload.get('base_value'), beginning_amount)

    now = datetime.now()
    eps = 0.000001

    try:
        with engine.begin() as conn:
            existing = _fetch_inventory_balance_row(conn, year, company_id)
            old_ending_amount = _to_float(existing.get('ending_inventory_amount'), 0.0) if existing else 0.0
            old_ending_qty = _to_float(existing.get('ending_inventory_qty'), 0.0) if existing else 0.0
            if existing:
                conn.execute(text("""
                    UPDATE inventory_balances
                    SET
                        beginning_inventory_amount = :beginning_inventory_amount,
                        beginning_inventory_qty = :beginning_inventory_qty,
                        ending_inventory_amount = :ending_inventory_amount,
                        ending_inventory_qty = :ending_inventory_qty,
                        base_value = :base_value,
                        updated_at = :updated_at
                    WHERE id = :id
                """), {
                    'id': existing.get('id'),
                    'beginning_inventory_amount': beginning_amount,
                    'beginning_inventory_qty': beginning_qty,
                    'ending_inventory_amount': ending_amount,
                    'ending_inventory_qty': ending_qty,
                    'base_value': base_value,
                    'updated_at': now
                })
                saved_id = existing.get('id')
            else:
                saved_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO inventory_balances (
                        id, company_id, year,
                        beginning_inventory_amount, beginning_inventory_qty,
                        ending_inventory_amount, ending_inventory_qty,
                        base_value, created_at, updated_at
                    ) VALUES (
                        :id, :company_id, :year,
                        :beginning_inventory_amount, :beginning_inventory_qty,
                        :ending_inventory_amount, :ending_inventory_qty,
                        :base_value, :created_at, :updated_at
                    )
                """), {
                    'id': saved_id,
                    'company_id': company_id,
                    'year': year,
                    'beginning_inventory_amount': beginning_amount,
                    'beginning_inventory_qty': beginning_qty,
                    'ending_inventory_amount': ending_amount,
                    'ending_inventory_qty': ending_qty,
                    'base_value': base_value,
                    'created_at': now,
                    'updated_at': now
                })

            # Auto-carry forward to next year.
            # Keep syncing if next-year beginning still looks auto-carried (not manually changed yet).
            next_year = year + 1
            next_row = _fetch_inventory_balance_row(conn, next_year, company_id)
            if not next_row:
                conn.execute(text("""
                    INSERT INTO inventory_balances (
                        id, company_id, year,
                        beginning_inventory_amount, beginning_inventory_qty,
                        ending_inventory_amount, ending_inventory_qty,
                        base_value, created_at, updated_at
                    ) VALUES (
                        :id, :company_id, :year,
                        :beginning_inventory_amount, :beginning_inventory_qty,
                        0, 0, :base_value, :created_at, :updated_at
                    )
                """), {
                    'id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'year': next_year,
                    'beginning_inventory_amount': ending_amount,
                    'beginning_inventory_qty': ending_qty,
                    'base_value': ending_amount,
                    'created_at': now,
                    'updated_at': now
                })
            else:
                next_beginning_amount = _to_float(next_row.get('beginning_inventory_amount'), 0.0)
                next_beginning_qty = _to_float(next_row.get('beginning_inventory_qty'), 0.0)
                next_ending_amount = _to_float(next_row.get('ending_inventory_amount'), 0.0)
                next_ending_qty = _to_float(next_row.get('ending_inventory_qty'), 0.0)

                beginning_is_empty = abs(next_beginning_amount) < eps and abs(next_beginning_qty) < eps
                beginning_matches_old_carry = (
                    abs(next_beginning_amount - old_ending_amount) < eps and
                    abs(next_beginning_qty - old_ending_qty) < eps
                )
                next_year_has_manual_activity = abs(next_ending_amount) >= eps or abs(next_ending_qty) >= eps

                should_sync_to_next_year = beginning_is_empty or (
                    beginning_matches_old_carry and not next_year_has_manual_activity
                )

                if should_sync_to_next_year:
                    conn.execute(text("""
                        UPDATE inventory_balances
                        SET
                            beginning_inventory_amount = :beginning_inventory_amount,
                            beginning_inventory_qty = :beginning_inventory_qty,
                            base_value = :base_value,
                            updated_at = :updated_at
                        WHERE id = :id
                    """), {
                        'id': next_row.get('id'),
                        'beginning_inventory_amount': ending_amount,
                        'beginning_inventory_qty': ending_qty,
                        'base_value': ending_amount,
                        'updated_at': now
                    })

        return jsonify({'message': 'Inventory balances saved successfully', 'id': saved_id})
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
