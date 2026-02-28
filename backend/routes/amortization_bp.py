import uuid
import json
from flask import Blueprint, request, jsonify, current_app as app
from datetime import datetime, date
from sqlalchemy import text
from decimal import Decimal
from backend.db.session import get_db_engine

amortization_bp = Blueprint('amortization_bp', __name__)


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    return False

@amortization_bp.route('/api/amortization/asset-groups', methods=['GET'])
def get_amortization_asset_groups():
    """Retrieve amortization asset groups"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        company_id = request.args.get('company_id')
        asset_type = request.args.get('asset_type')
        
        with engine.connect() as conn:
            query_params = {}
            conditions = []

            if company_id:
                conditions.append("(company_id = :company_id OR company_id IS NULL)")
                query_params['company_id'] = company_id
            else:
                # Default mode for settings: use global groups only.
                conditions.append("company_id IS NULL")

            if asset_type:
                conditions.append("asset_type = :asset_type")
                query_params['asset_type'] = asset_type

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = text(f"""
                SELECT id, group_name, group_number, asset_type, tarif_rate,
                       tarif_half_rate, useful_life_years, company_id
                FROM amortization_asset_groups
                {where_clause}
                ORDER BY asset_type, group_number,
                         CASE WHEN company_id = :company_id THEN 0 ELSE 1 END
            """) if company_id else text(f"""
                SELECT id, group_name, group_number, asset_type, tarif_rate,
                       tarif_half_rate, useful_life_years, company_id
                FROM amortization_asset_groups
                {where_clause}
                ORDER BY asset_type, group_number
            """)

            result = conn.execute(query, query_params)
            groups = []
            merged_by_key = {}

            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, Decimal):
                        d[key] = float(value)

                # If company_id is provided, prefer company row over global row
                # for the same (asset_type, group_number).
                if company_id:
                    merge_key = f"{d.get('asset_type')}::{d.get('group_number')}"
                    existing = merged_by_key.get(merge_key)
                    if existing is None or (d.get('company_id') and not existing.get('company_id')):
                        merged_by_key[merge_key] = d
                else:
                    groups.append(d)

            if company_id:
                groups = sorted(
                    merged_by_key.values(),
                    key=lambda g: (str(g.get('asset_type') or ''), int(g.get('group_number') or 0))
                )

            return jsonify({'groups': groups})
    except Exception as e:
        app.logger.error(f"Failed to fetch asset groups: {e}")
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/amortization/asset-groups', methods=['POST'])
def create_amortization_asset_group():
    """Create a new amortization asset group"""
    data = request.json
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        group_id = str(uuid.uuid4())
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO amortization_asset_groups 
                    (id, company_id, group_name, group_number, asset_type, 
                     tarif_rate, tarif_half_rate, useful_life_years)
                    VALUES 
                    (:id, :company_id, :group_name, :group_number, :asset_type,
                     :tarif_rate, :tarif_half_rate, :useful_life_years)
                """),
                {
                    'id': group_id,
                    'company_id': data.get('company_id'),
                    'group_name': data.get('group_name'),
                    'group_number': data.get('group_number'),
                    'asset_type': data.get('asset_type'),
                    'tarif_rate': data.get('tarif_rate'),
                    'tarif_half_rate': data.get('tarif_half_rate'),
                    'useful_life_years': data.get('useful_life_years')
                }
            )
            conn.commit()
            data['id'] = group_id
            return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/amortization/asset-groups/<group_id>', methods=['PUT'])
def update_amortization_asset_group(group_id):
    """Update an amortization asset group"""
    data = request.json
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE amortization_asset_groups 
                    SET group_name = :group_name,
                        group_number = :group_number,
                        asset_type = :asset_type,
                        tarif_rate = :tarif_rate,
                        tarif_half_rate = :tarif_half_rate,
                        useful_life_years = :useful_life_years
                    WHERE id = :id
                """),
                {
                    'id': group_id,
                    'group_name': data.get('group_name'),
                    'group_number': data.get('group_number'),
                    'asset_type': data.get('asset_type'),
                    'tarif_rate': data.get('tarif_rate'),
                    'tarif_half_rate': data.get('tarif_half_rate'),
                    'useful_life_years': data.get('useful_life_years')
                }
            )
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/reports/amortization-items', methods=['GET'])
@amortization_bp.route('/api/amortization-items', methods=['GET'])
def get_amortization_items():
    """Retrieve amortization items for a company and year"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        year = request.args.get('year') or datetime.now().year
        company_id = request.args.get('company_id')
        
        if not company_id:
            # Fallback for testing: get first company
            with engine.connect() as conn:
                first_comp = conn.execute(text("SELECT id FROM companies LIMIT 1")).fetchone()
                if first_comp:
                    company_id = first_comp[0]
                else:
                    return jsonify({'error': 'company_id is required'}), 400
        
        with engine.connect() as conn:
            settings_query = text("""
                SELECT setting_name, setting_value, setting_type 
                FROM amortization_settings 
                WHERE company_id = :company_id OR company_id IS NULL
                ORDER BY company_id ASC
            """)
            settings_result = conn.execute(settings_query, {'company_id': company_id})
            
            use_mark_based = False
            asset_marks = []
            default_rate = 20.0
            default_life = 5
            allow_partial_year = True
            
            for row in settings_result:
                if row.setting_name == 'use_mark_based_amortization':
                    use_mark_based = row.setting_value.lower() == 'true'
                elif row.setting_name == 'amortization_asset_marks':
                    try:
                        asset_marks = json.loads(row.setting_value)
                    except:
                        asset_marks = []
                elif row.setting_name == 'default_amortization_rate':
                    try:
                        default_rate = float(row.setting_value)
                    except:
                        default_rate = 20.0
                elif row.setting_name == 'default_asset_useful_life':
                    try:
                        default_life = int(row.setting_value)
                    except:
                        default_life = 5
                elif row.setting_name == 'allow_partial_year':
                    allow_partial_year = row.setting_value.lower() == 'true'

            items_query = text("""
                SELECT 
                    ai.id, ai.company_id, ai.year, 
                    COALESCE(ai.mark_id, ai.coa_id) as mark_id,
                    COALESCE(m.personal_use, coa.name) as mark_name,
                    ai.coa_id, coa.code as coa_code, coa.name as coa_name,
                    ai.description, ai.amount, ai.amortization_date,
                    ai.asset_group_id, ai.use_half_rate, ai.notes, ai.is_manual,
                    ai.created_at, ai.updated_at,
                    ag.group_name, ag.tarif_rate, ag.useful_life_years, ag.asset_type
                FROM amortization_items ai
                LEFT JOIN chart_of_accounts coa ON ai.coa_id = coa.id
                LEFT JOIN marks m ON ai.mark_id = m.id
                LEFT JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
                WHERE ai.company_id = :company_id
                ORDER BY ai.amortization_date DESC, ai.created_at DESC
            """)
            
            items_result = conn.execute(items_query, {'company_id': company_id, 'year': year})
            items = []
            manual_total_amort = 0
            automatic_total_amort = 0
            total_amount = 0
            
            for row in items_result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, Decimal):
                        d[key] = float(value)
                    elif isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d') if key == 'amortization_date' else value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, date) and not isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d')
                
                amount = float(d.get('amount', 0))
                report_year = int(year)
                
                # Determine if we should include this item
                purchase_date_str = d.get('amortization_date')
                purchase_year = report_year
                if purchase_date_str:
                    try:
                        if isinstance(purchase_date_str, str):
                            purchase_year = int(purchase_date_str[:4])
                        else:
                            purchase_year = purchase_date_str.year
                    except:
                        pass
                
                # Skip if it's a one-time adjustment for another year
                if not d.get('asset_group_id') and d.get('year') != report_year:
                    continue
                # Skip if it's an asset not yet purchased
                if purchase_year > report_year:
                    continue
                
                tarif_rate = float(d.get('tarif_rate') or 20)
                
                # Check if it has an asset group for multi-year calc
                if d.get('asset_group_id'):
                    # Multi-year accumulation loop
                    annual_amort_base = amount * (tarif_rate / 100)
                    accum_prev = 0
                    current_year_amort = 0
                    
                    start_date_val = d.get('amortization_date')
                    if isinstance(start_date_val, str):
                        try:
                            start_date_val = datetime.strptime(start_date_val[:10], '%Y-%m-%d').date()
                        except:
                            start_date_val = date(report_year, 1, 1)
                    
                    acquisition_year = start_date_val.year
                    
                    for y in range(acquisition_year, report_year + 1):
                        y_amort = annual_amort_base
                        if y == acquisition_year:
                            if allow_partial_year:
                                months = 12 - start_date_val.month + 1
                                y_amort = annual_amort_base * (months / 12)
                            elif d.get('use_half_rate'):
                                y_amort = annual_amort_base * 0.5
                        
                        remaining = amount - accum_prev
                        y_amort = min(y_amort, remaining)
                        
                        if y < report_year:
                            accum_prev += y_amort
                        else:
                            current_year_amort = y_amort
                    
                    annual_amortization = current_year_amort
                    accum_prev_val = accum_prev
                    
                    # Calculate multiplier string for display
                    multiplier_display = "1"
                    if report_year == acquisition_year:
                        if allow_partial_year:
                            months = 12 - start_date_val.month + 1
                            multiplier_display = f"{months}/12"
                        elif d.get('use_half_rate'):
                            multiplier_display = "1/2"
                    elif report_year < acquisition_year:
                        multiplier_display = "0"
                else:
                    # One-time adjustment / Direct expense (must be ai.year == report_year)
                    annual_amortization = amount
                    accum_prev_val = 0
                    tarif_rate = 100 
                    multiplier_display = "-"
                
                # Asset Type Label mapping
                type_labels = {
                    'Tangible': 'Harta Berwujud',
                    'Intangible': 'Harta Tidak Berwujud',
                    'Building': 'Bangunan'
                }
                
                asset_type = d.get('asset_type') or 'Tangible'
                type_label = type_labels.get(asset_type, asset_type)
                
                group_display = f"{type_label}"
                if d.get('group_name'):
                    group_display += f" - {d['group_name']}"
                useful_life_display = d.get('useful_life_years')
                if useful_life_display not in (None, '', 0):
                    group_display += f" ({int(useful_life_display)} tahun)"
                else:
                    group_display += f" ({tarif_rate}%)"

                deductible_display = "50%" if _as_bool(d.get('use_half_rate')) else "100%"
                
                d.update({
                    'accumulated_depreciation_prev_year': accum_prev_val,
                    'multiplier': multiplier_display,
                    'annual_amortization': annual_amortization,
                    'total_accumulated_depreciation': accum_prev_val + annual_amortization,
                    'book_value_end_year': max(0, amount - (accum_prev_val + annual_amortization)),
                    'group': group_display,
                    'rate_type': deductible_display,
                    'is_manual': bool(d.get('is_manual')),
                    'is_from_ledger': False,
                    'is_manual_asset': d.get('is_manual'),
                    'asset_id': None
                })
                
                items.append(d)
                total_amount += amount
                manual_total_amort += annual_amortization
            
            # Prepare mark condition for transactions
            query_params = {'company_id': company_id, 'year': year}
            
            # Query transactions - use separate approach to avoid duplication
            # We'll query transactions with COA 5314 first, then add other types separately
            query_params = {'company_id': company_id, 'year': year}
            
            # Query 1: Transactions with COA 5314 (fixed join)
            txn_5314_query = text("""
                SELECT DISTINCT
                    t.id as asset_id, t.txn_date, t.description,
                    t.amount as acquisition_cost, t.amortization_asset_group_id as asset_group_id,
                    t.amortization_start_date, t.use_half_rate, t.amortization_notes as notes,
                    ag.group_name, ag.tarif_rate, ag.useful_life_years, ag.asset_type,
                    m.personal_use as mark_name,
                    coa.code as coa_code, coa.name as coa_name
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                INNER JOIN mark_coa_mapping mcm ON t.mark_id = mcm.mark_id
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                LEFT JOIN amortization_asset_groups ag ON t.amortization_asset_group_id = ag.id
                WHERE coa.code = '5314'
                AND (t.company_id = :company_id OR :company_id IS NULL)
                AND YEAR(t.txn_date) <= :year
                ORDER BY t.txn_date DESC
            """)
            
            txn_query = txn_5314_query
            
            txn_result = conn.execute(txn_query, query_params)
            
            for row in txn_result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, Decimal):
                        d[key] = float(value)
                    elif isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d') if 'date' in key else value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, date) and not isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d')
                
                tarif_rate = d.get('tarif_rate') or default_rate
                base_amount = float(d.get('acquisition_cost', 0))
                useful_life = int(d.get('useful_life_years') or default_life)
                
                # Multi-year calculation
                report_year = int(year)
                start_date_val = d.get('amortization_start_date') or d.get('txn_date')
                if isinstance(start_date_val, str):
                    try:
                        start_date_val = datetime.strptime(start_date_val[:10], '%Y-%m-%d').date()
                    except:
                        start_date_val = date(report_year, 1, 1)
                
                acquisition_year = start_date_val.year
                annual_amort_base = base_amount * (tarif_rate / 100)
                
                accum_prev = 0
                current_year_amort = 0
                
                for y in range(acquisition_year, report_year + 1):
                    y_amort = annual_amort_base
                    if y == acquisition_year:
                        if allow_partial_year:
                            months = 12 - start_date_val.month + 1
                            y_amort = annual_amort_base * (months / 12)
                        elif d.get('use_half_rate'):
                            y_amort = annual_amort_base * 0.5
                    
                    remaining = base_amount - accum_prev
                    y_amort = min(y_amort, remaining)
                    
                    if y < report_year:
                        accum_prev += y_amort
                    else:
                        current_year_amort = y_amort
                
                # Calculate multiplier string for display
                multiplier_display = "1"
                if report_year == acquisition_year:
                    if allow_partial_year:
                        months = 12 - start_date_val.month + 1
                        multiplier_display = f"{months}/12"
                    elif d.get('use_half_rate'):
                        multiplier_display = "1/2"
                elif report_year < acquisition_year:
                    multiplier_display = "0"
                
                # Asset Type Label mapping
                type_labels = {
                    'Tangible': 'Harta Berwujud',
                    'Intangible': 'Harta Tidak Berwujud',
                    'Building': 'Bangunan'
                }
                
                asset_type = d.get('asset_type') or 'Tangible'
                type_label = type_labels.get(asset_type, asset_type)
                
                group_display = f"{type_label}"
                if d.get('group_name'):
                    group_display += f" - {d['group_name']}"
                elif d.get('mark_name'):
                    group_display += f" - {d['mark_name']}"

                useful_life_display = d.get('useful_life_years')
                if useful_life_display not in (None, '', 0):
                    group_display += f" ({int(useful_life_display)} tahun)"
                else:
                    group_display += f" ({tarif_rate}%)"

                deductible_display = "50%" if _as_bool(d.get('use_half_rate')) else "100%"
                
                d.update({
                    'annual_amortization': current_year_amort,
                    'accumulated_depreciation_prev_year': accum_prev,
                    'total_accumulated_depreciation': accum_prev + current_year_amort,
                    'book_value_end_year': max(0, base_amount - (accum_prev + current_year_amort)),
                    'multiplier': multiplier_display,
                    'group': group_display,
                    'rate_type': deductible_display,
                    'is_manual': False,
                    'is_from_ledger': True,
                    'is_manual_asset': False,
                    'amount': base_amount,
                    'acquisition_cost': base_amount,
                    'amortization_date': d.get('amortization_start_date') or d.get('txn_date'),
                    'asset_name': d.get('description', '')
                })
                
                items.append(d)
                total_amount += base_amount
                automatic_total_amort += current_year_amort

            # 3. Fetch from amortization_assets (Registered Assets)
            assets_query = text("""
                SELECT 
                    a.id as asset_id, a.asset_name, a.asset_description as description,
                    a.acquisition_cost, a.acquisition_date,
                    a.amortization_start_date, a.asset_group_id, a.use_half_rate,
                    ag.group_name, ag.tarif_rate, ag.useful_life_years, ag.asset_type
                FROM amortization_assets a
                LEFT JOIN amortization_asset_groups ag ON a.asset_group_id = ag.id
                WHERE (a.company_id = :company_id OR :company_id IS NULL)
                AND a.is_active = TRUE
            """)
            assets_result = conn.execute(assets_query, {'company_id': company_id})
            
            for row in assets_result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, Decimal):
                        d[key] = float(value)
                    elif isinstance(value, (datetime, date)):
                        d[key] = value.strftime('%Y-%m-%d')
                
                tarif_rate = d.get('tarif_rate') or default_rate
                base_amount = float(d.get('acquisition_cost', 0))
                useful_life = int(d.get('useful_life_years') or default_life)
                
                report_year = int(year)
                start_date_val = d.get('amortization_start_date') or d.get('acquisition_date')
                if isinstance(start_date_val, str):
                    try:
                        start_date_val = datetime.strptime(start_date_val[:10], '%Y-%m-%d').date()
                    except:
                        start_date_val = date(report_year, 1, 1)
                
                acquisition_year = start_date_val.year
                annual_amort_base = base_amount * (tarif_rate / 100)
                
                accum_prev = 0
                current_year_amort = 0
                
                for y in range(acquisition_year, report_year + 1):
                    y_amort = annual_amort_base
                    if y == acquisition_year:
                        if allow_partial_year:
                            months = 12 - start_date_val.month + 1
                            y_amort = annual_amort_base * (months / 12)
                        elif d.get('use_half_rate'):
                            y_amort = annual_amort_base * 0.5
                    
                    remaining = base_amount - accum_prev
                    y_amort = min(y_amort, remaining)
                    
                    if y < report_year:
                        accum_prev += y_amort
                    else:
                        current_year_amort = y_amort
                
                # Calculate multiplier string for display
                multiplier_display = "1"
                if report_year == acquisition_year:
                    if allow_partial_year:
                        months = 12 - start_date_val.month + 1
                        multiplier_display = f"{months}/12"
                    elif d.get('use_half_rate'):
                        multiplier_display = "1/2"
                elif report_year < acquisition_year:
                    multiplier_display = "0"
                
                # Asset Type Label mapping
                type_labels = {
                    'Tangible': 'Harta Berwujud',
                    'Intangible': 'Harta Tidak Berwujud',
                    'Building': 'Bangunan'
                }
                
                asset_type = d.get('asset_type') or 'Tangible'
                type_label = type_labels.get(asset_type, asset_type)
                
                group_display = f"{type_label}"
                if d.get('group_name'):
                    group_display += f" - {d['group_name']}"
                useful_life_display = d.get('useful_life_years')
                if useful_life_display not in (None, '', 0):
                    group_display += f" ({int(useful_life_display)} tahun)"
                else:
                    group_display += f" ({tarif_rate}%)"

                deductible_display = "50%" if _as_bool(d.get('use_half_rate')) else "100%"
                
                d.update({
                    'annual_amortization': current_year_amort,
                    'accumulated_depreciation_prev_year': accum_prev,
                    'total_accumulated_depreciation': accum_prev + current_year_amort,
                    'book_value_end_year': max(0, base_amount - (accum_prev + current_year_amort)),
                    'multiplier': multiplier_display,
                    'group': group_display,
                    'rate_type': deductible_display,
                    'is_manual': False,
                    'is_from_ledger': False,
                    'is_manual_asset': False,
                    'amount': base_amount,
                    'acquisition_cost': base_amount,
                    'amortization_date': d.get('amortization_start_date') or d.get('acquisition_date'),
                    'txn_date': d.get('acquisition_date')
                })
                
                items.append(d)
                total_amount += base_amount
                automatic_total_amort += current_year_amort
            
            return jsonify({
                'items': items,
                'totalAmount': total_amount,
                'manual_total': manual_total_amort,
                'calculated_total': automatic_total_amort,
                'grand_total': manual_total_amort + automatic_total_amort,
                'settings': {}
            })
    except Exception as e:
        app.logger.error(f"Failed to fetch amortization items: {e}")
        return jsonify({'error': str(e)}), 500

# OLD COA-BASED FUNCTION - REMOVED
# @amortization_bp.route('/api/amortization-items', methods=['POST'])
# def create_amortization_item():
#     # This function has been replaced with mark-based version below

# OLD DELETE FUNCTION - REMOVED TO FIX DUPLICATE
# @amortization_bp.route('/api/amortization-items/<item_id>', methods=['DELETE'])
# def delete_amortization_item(item_id):
#     # This function has been replaced with the one below

@amortization_bp.route('/api/amortization-coa-codes', methods=['GET'])
def get_amortization_coa_codes():
    """Retrieve COA codes that can be used for amortization"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, code, name, category, subcategory
                FROM chart_of_accounts
                WHERE code LIKE '531%' OR code LIKE '6%'
                ORDER BY code
            """)
            
            result = conn.execute(query)
            coa_codes = []
            coa_details = []
            
            for row in result:
                d = dict(row._mapping)
                coa_codes.append(d['code'])
                coa_details.append(d)
            
            return jsonify({
                'coa_codes': coa_codes,
                'coa_details': coa_details
            })
    except Exception as e:
        app.logger.error(f"Failed to fetch amortization COA codes: {e}")
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/amortization-settings', methods=['GET'])
@amortization_bp.route('/api/amortization/settings', methods=['GET'])
@amortization_bp.route('/api/amortization/mark-settings', methods=['GET'])
def get_amortization_settings():
    """Retrieve amortization settings for a company"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        company_id = request.args.get('company_id')
        
        with engine.connect() as conn:
            # Fetch all settings for the company or general settings
            # ORDER BY company_id ASC ensures NULL (global) settings are processed first,
            # and company-specific settings overwrite them.
            query = text("""
                SELECT setting_name, setting_value, setting_type 
                FROM amortization_settings 
                WHERE company_id = :company_id OR company_id IS NULL
                ORDER BY company_id ASC
            """)
            result = conn.execute(query, {'company_id': company_id})
            
            settings = {
                'default_asset_useful_life': 5,
                'default_amortization_rate': 20.0,
                'allow_partial_year': True,
                'accumulated_depreciation_coa_codes': {
                    'Building': '1524',
                    'Tangible': '1530',
                    'LandRights': '1534',
                    'Intangible': '1601'
                }
            }
            
            for row in result:
                name = row.setting_name
                val = row.setting_value
                typ = row.setting_type
                
                if typ == 'boolean':
                    settings[name] = str(val).lower() == 'true'
                elif typ == 'json':
                    try:
                        settings[name] = json.loads(val)
                    except:
                        settings[name] = {}
                elif typ == 'number':
                    try:
                        settings[name] = float(val)
                    except:
                        settings[name] = 0
                else:
                    settings[name] = val
            
            return jsonify({
                'settings': settings,
                'available_marks': []
            })
    except Exception as e:
        app.logger.error(f"Failed to fetch amortization settings: {e}")
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/amortization-settings', methods=['POST'])
@amortization_bp.route('/api/amortization/settings', methods=['POST'])
@amortization_bp.route('/api/amortization/mark-settings', methods=['POST'])
def save_amortization_settings():
    """Save amortization settings for a company"""
    data = request.json
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        company_id = (data.get('company_id') or '').strip() or None

        default_settings = {
            'default_asset_useful_life': 5,
            'default_amortization_rate': 20.0,
            'allow_partial_year': True,
            'accumulated_depreciation_coa_codes': {
                'Building': '1524',
                'Tangible': '1530',
                'LandRights': '1534',
                'Intangible': '1601'
            },
            'prepaid_prepaid_asset_coa': '1135',
            'prepaid_rent_expense_coa': '5315',
            'prepaid_tax_payable_coa': '2191',
            'rental_cash_coa': '1101'
        }

        with engine.begin() as conn:
            read_query = text("""
                SELECT setting_name, setting_value, setting_type
                FROM amortization_settings
                WHERE (company_id = :company_id OR company_id IS NULL)
                ORDER BY company_id ASC
            """)
            rows = conn.execute(read_query, {'company_id': company_id})

            existing_settings = {}
            for row in rows:
                if row.setting_type == 'boolean':
                    parsed = str(row.setting_value).lower() == 'true'
                elif row.setting_type == 'number':
                    try:
                        parsed = float(row.setting_value)
                    except Exception:
                        parsed = 0
                elif row.setting_type == 'json':
                    try:
                        parsed = json.loads(row.setting_value)
                    except Exception:
                        parsed = []
                else:
                    parsed = row.setting_value
                existing_settings[row.setting_name] = parsed

            merged_settings = {**default_settings, **existing_settings}
            for key in default_settings.keys():
                if key in data:
                    merged_settings[key] = data.get(key)

            settings_to_save = [
                ('default_asset_useful_life', str(merged_settings.get('default_asset_useful_life', 5)), 'number'),
                ('default_amortization_rate', str(merged_settings.get('default_amortization_rate', 20.0)), 'number'),
                ('allow_partial_year', str(bool(merged_settings.get('allow_partial_year', True))).lower(), 'boolean'),
                ('accumulated_depreciation_coa_codes', json.dumps(merged_settings.get('accumulated_depreciation_coa_codes', default_settings['accumulated_depreciation_coa_codes'])), 'json'),
                ('prepaid_prepaid_asset_coa', str(merged_settings.get('prepaid_prepaid_asset_coa', '1135')), 'text'),
                ('prepaid_rent_expense_coa', str(merged_settings.get('prepaid_rent_expense_coa', '5315')), 'text'),
                ('prepaid_tax_payable_coa', str(merged_settings.get('prepaid_tax_payable_coa', '2191')), 'text'),
                ('rental_cash_coa', str(merged_settings.get('rental_cash_coa', '1101')), 'text')
            ]

            update_query = text("""
                UPDATE amortization_settings
                SET setting_value = :val,
                    setting_type = :typ,
                    updated_at = CURRENT_TIMESTAMP
                WHERE setting_name = :name
                  AND (
                    (:company_id IS NULL AND company_id IS NULL)
                    OR company_id = :company_id
                  )
            """)
            insert_query = text("""
                INSERT INTO amortization_settings
                (id, company_id, setting_name, setting_value, setting_type, created_at, updated_at)
                VALUES (:id, :company_id, :name, :val, :typ, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """)

            for name, val, typ in settings_to_save:
                update_result = conn.execute(
                    update_query,
                    {
                        'company_id': company_id,
                        'name': name,
                        'val': val,
                        'typ': typ
                    }
                )

                if update_result.rowcount == 0:
                    conn.execute(
                        insert_query,
                        {
                            'id': str(uuid.uuid4()),
                            'company_id': company_id,
                            'name': name,
                            'val': val,
                            'typ': typ
                        }
                    )
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Failed to save amortization settings: {e}")
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/mark-amortization-mappings', methods=['GET'])
def get_mark_amortization_mappings():
    """Retrieve all mark amortization mappings"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT mam.*, m.personal_use as mark_name, ag.group_name,
                       ag.tarif_rate as group_tarif_rate, ag.group_number
                FROM mark_amortization_mappings mam
                LEFT JOIN marks m ON mam.mark_id = m.id
                LEFT JOIN amortization_asset_groups ag ON mam.asset_group_id = ag.id
                ORDER BY m.personal_use, mam.asset_type
            """)
            
            result = conn.execute(query)
            mappings = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, Decimal):
                        d[key] = float(value)
                    elif isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                d['is_deductible_50_percent'] = bool(d.get('is_deductible_50_percent'))
                mappings.append(d)
            
            return jsonify({'mappings': mappings})
    except Exception as e:
        app.logger.error(f"Failed to fetch mark amortization mappings: {e}")
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/mark-amortization-mappings', methods=['POST'])
def create_mark_amortization_mapping():
    """Create a new mark amortization mapping"""
    data = request.json
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        mapping_id = str(uuid.uuid4())
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO mark_amortization_mappings 
                    (id, mark_id, asset_type, useful_life_years, amortization_rate,
                     asset_group_id, is_deductible_50_percent)
                    VALUES 
                    (:id, :mark_id, :asset_type, :useful_life_years, :amortization_rate,
                     :asset_group_id, :is_deductible_50_percent)
                """),
                {
                    'id': mapping_id,
                    'mark_id': data.get('mark_id'),
                    'asset_type': data.get('asset_type'),
                    'useful_life_years': data.get('useful_life_years', 5),
                    'amortization_rate': data.get('amortization_rate', 20.0),
                    'asset_group_id': data.get('asset_group_id'),
                    'is_deductible_50_percent': data.get('is_deductible_50_percent', False)
                }
            )
            conn.commit()
            data['id'] = mapping_id
            return jsonify(data), 201
    except Exception as e:
        app.logger.error(f"Failed to create mark amortization mapping: {e}")
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/mark-amortization-mappings/<mapping_id>', methods=['PUT'])
def update_mark_amortization_mapping(mapping_id):
    """Update a mark amortization mapping"""
    data = request.json
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE mark_amortization_mappings 
                    SET mark_id = :mark_id, asset_type = :asset_type,
                        useful_life_years = :useful_life_years, amortization_rate = :amortization_rate,
                        asset_group_id = :asset_group_id, is_deductible_50_percent = :is_deductible_50_percent,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    'id': mapping_id, 'mark_id': data.get('mark_id'), 'asset_type': data.get('asset_type'),
                    'useful_life_years': data.get('useful_life_years'), 'amortization_rate': data.get('amortization_rate'),
                    'asset_group_id': data.get('asset_group_id'), 'is_deductible_50_percent': data.get('is_deductible_50_percent')
                }
            )
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Failed to update mark amortization mapping: {e}")
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/mark-amortization-mappings/<mapping_id>', methods=['DELETE'])
def delete_mark_amortization_mapping(mapping_id):
    """Delete a mark amortization mapping"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            conn.execute(
                text("DELETE FROM mark_amortization_mappings WHERE id = :id"),
                {'id': mapping_id}
            )
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Failed to delete mark amortization mapping: {e}")
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/marks/<mark_id>/amortization', methods=['GET'])
def get_mark_amortization_config(mark_id):
    """Get amortization configuration for a specific mark"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT mam.*, m.personal_use as mark_name, ag.group_name,
                       ag.tarif_rate as group_tarif_rate, ag.group_number
                FROM mark_amortization_mappings mam
                LEFT JOIN marks m ON mam.mark_id = m.id
                LEFT JOIN amortization_asset_groups ag ON mam.asset_group_id = ag.id
                WHERE mam.mark_id = :mark_id
            """)
            
            result = conn.execute(query, {'mark_id': mark_id})
            row = result.fetchone()
            
            if row:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, Decimal):
                        d[key] = float(value)
                    elif isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                d['is_deductible_50_percent'] = bool(d.get('is_deductible_50_percent'))
                return jsonify(d)
            else:
                return jsonify(None)
    except Exception as e:
        app.logger.error(f"Failed to fetch mark amortization config: {e}")
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/amortization-items/generate-journal', methods=['POST'])
def generate_manual_amortization_journal():
    """Generate journal entries for manual amortization items using mark-based approach"""
    data = request.json
    company_id = data.get('company_id')
    year = data.get('year')
    
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            # Get manual amortization items for the year
            manual_query = text("""
                SELECT ai.*, m.personal_use as mark_name,
                       ag.group_name, ag.tarif_rate, ag.asset_type
                FROM amortization_items ai
                LEFT JOIN marks m ON ai.mark_id = m.id
                LEFT JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
                WHERE ai.company_id = :company_id
                AND ai.year = :year
                AND ai.is_manual = TRUE
            """)
            
            manual_result = conn.execute(manual_query, {
                'company_id': company_id,
                'year': year
            })
            
            # Check if journal entries already exist for this year
            existing_query = text("""
                SELECT COUNT(*) as count
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                WHERE m.personal_use LIKE 'Manual Amortization-%'
                AND t.company_id = :company_id
                AND YEAR(t.txn_date) = :year
            """)
            
            existing_result = conn.execute(existing_query, {
                'company_id': company_id,
                'year': year
            }).fetchone()
            
            if existing_result and existing_result.count > 0:
                return jsonify({
                    'message': 'Journal entries already exist for manual amortization items',
                    'existing_count': existing_result.count
                }), 400
            
            # Get COA IDs for accumulated depreciation
            accumulated_coa_codes = {
                'Tangible': '1530',  # Akumulasi Penyusutan - Aset Tetap Lainnya
                'Intangible': '1601',  # Akumulasi Amortisasi - Aset Tak Berwujud
                'Building': '1524',  # Akumulasi Penyusutan - Bangunan
                'LandRights': '1534'  # Akumulasi Penyusutan - Hak Guna
            }
            
            # Get COA IDs
            coa_ids = {}
            expense_coa_id = conn.execute(text("""
                SELECT id FROM chart_of_accounts WHERE code = '5314'
            """)).fetchone()[0]
            
            for asset_type, coa_code in accumulated_coa_codes.items():
                coa_result = conn.execute(text("""
                    SELECT id FROM chart_of_accounts WHERE code = :code
                """), {'code': coa_code}).fetchone()
                if coa_result:
                    coa_ids[asset_type] = coa_result[0]
            
            # Generate journal entries for each manual item
            journal_count = 0
            for row in manual_result:
                d = dict(row._mapping)
                amount = float(d['amount'])
                asset_type = d.get('asset_type', 'Tangible')
                
                # Create debit mark for expense (5314)
                debit_mark_id = str(uuid.uuid4())
                debit_mark_name = f"Manual Amortization-Debit-{d['id'][:8]}"
                
                conn.execute(text("""
                    INSERT INTO marks (id, personal_use, internal_report, tax_report, created_at, updated_at)
                    VALUES (:id, :name, 1, 1, NOW(), NOW())
                """), {
                    'id': debit_mark_id,
                    'name': debit_mark_name
                })
                
                # Create credit mark for accumulated depreciation
                credit_mark_id = str(uuid.uuid4())
                credit_mark_name = f"Manual Amortization-Credit-{d['id'][:8]}"
                
                conn.execute(text("""
                    INSERT INTO marks (id, personal_use, internal_report, tax_report, created_at, updated_at)
                    VALUES (:id, :name, 1, 1, NOW(), NOW())
                """), {
                    'id': credit_mark_id,
                    'name': credit_mark_name
                })
                
                # Create COA mappings
                conn.execute(text("""
                    INSERT INTO mark_coa_mapping (id, mark_id, coa_id, mapping_type, created_at, updated_at)
                    VALUES (:id, :mark_id, :coa_id, 'DEBIT', NOW(), NOW())
                """), {
                    'id': str(uuid.uuid4()),
                    'mark_id': debit_mark_id,
                    'coa_id': expense_coa_id
                })
                
                # Credit mapping to accumulated depreciation
                if asset_type in coa_ids:
                    conn.execute(text("""
                        INSERT INTO mark_coa_mapping (id, mark_id, coa_id, mapping_type, created_at, updated_at)
                        VALUES (:id, :mark_id, :coa_id, 'CREDIT', NOW(), NOW())
                    """), {
                        'id': str(uuid.uuid4()),
                        'mark_id': credit_mark_id,
                        'coa_id': coa_ids[asset_type]
                    })
                
                # Create transactions
                txn_date = d.get('amortization_date', f'{year}-12-31')
                description = f"Manual Amortization - {d['description']}"
                
                # Debit transaction (expense)
                debit_txn_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO transactions (id, txn_date, description, amount, db_cr, mark_id, 
                                     company_id, created_at, updated_at, source_file)
                    VALUES (:id, :date, :desc, :amount, 'DB', :mark_id, 
                            :company_id, NOW(), NOW(), :source)
                """), {
                    'id': debit_txn_id,
                    'date': txn_date,
                    'desc': description,
                    'amount': amount,
                    'mark_id': debit_mark_id,
                    'company_id': company_id,
                    'source': 'manual_amortization_journal'
                })
                
                # Credit transaction (accumulated depreciation)
                if asset_type in coa_ids:
                    credit_txn_id = str(uuid.uuid4())
                    conn.execute(text("""
                        INSERT INTO transactions (id, txn_date, description, amount, db_cr, mark_id, 
                                         company_id, created_at, updated_at, source_file)
                        VALUES (:id, :date, :desc, :amount, 'CR', :mark_id, 
                                :company_id, NOW(), NOW(), :source)
                    """), {
                        'id': credit_txn_id,
                        'date': txn_date,
                        'desc': description,
                        'amount': amount,
                        'mark_id': credit_mark_id,
                        'company_id': company_id,
                        'source': 'manual_amortization_journal'
                    })
                
                journal_count += 1
            
            conn.commit()
            
            return jsonify({
                'message': f'Successfully generated {journal_count} journal entries',
                'journal_count': journal_count,
                'items_processed': len(manual_result.fetchall())
            }), 201
            
    except Exception as e:
        app.logger.error(f"Failed to generate manual amortization journal: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/marks/amortization-eligible', methods=['GET'])
def get_amortization_eligible_marks():
    """Get marks that are eligible for amortization (have asset-related COA mappings)"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            # Get marks that have asset-related COA mappings and are marked as assets
            query = text("""
                SELECT DISTINCT m.id, m.personal_use,
                       COALESCE(am.asset_type, 'Tangible') as asset_type
                FROM marks m
                INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                LEFT JOIN mark_amortization_mappings am ON m.id = am.mark_id
                WHERE (coa.code LIKE '1%' OR coa.code LIKE '15%' OR coa.code LIKE '16%')
                  AND m.is_asset = 1
                ORDER BY m.personal_use
            """)
            
            result = conn.execute(query)
            marks = []
            for row in result:
                d = dict(row._mapping)
                marks.append({
                    'id': d['id'],
                    'personal_use': d['personal_use'],
                    'asset_type': d['asset_type']
                })
            
            return jsonify({
                'marks': marks
            }), 201
            
    except Exception as e:
        app.logger.error(f"Failed to fetch amortization eligible marks: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/amortization-items', methods=['POST'])
def create_amortization_item():
    """Create a new amortization item"""
    data = request.json
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            item_id = str(uuid.uuid4())
            
            # Create the amortization item
            conn.execute(
                text("""
                    INSERT INTO amortization_items (
                        id, company_id, year, mark_id, description, amount,
                        amortization_date, asset_group_id, use_half_rate, notes,
                        is_manual, created_at, updated_at
                    ) VALUES (
                        :id, :company_id, :year, :mark_id, :description, :amount,
                        :amortization_date, :asset_group_id, :use_half_rate, :notes,
                        :is_manual, NOW(), NOW()
                    )
                """),
                {
                    'id': item_id,
                    'company_id': data.get('company_id'),
                    'year': data.get('year'),
                    'mark_id': data.get('mark_id'),
                    'description': data.get('description'),
                    'amount': data.get('amount'),
                    'amortization_date': data.get('amortization_date'),
                    'asset_group_id': data.get('asset_group_id'),
                    'use_half_rate': data.get('use_half_rate', False),
                    'notes': data.get('notes'),
                    'is_manual': data.get('is_manual', True)
                }
            )
            conn.commit()
            data['id'] = item_id
            return jsonify(data), 201
    except Exception as e:
        app.logger.error(f"Failed to create amortization item: {e}")
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/amortization-items/<item_id>', methods=['PUT'])
def update_amortization_item(item_id):
    """Update an amortization item"""
    data = request.json
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE amortization_items 
                    SET mark_id = :mark_id,
                        description = :description,
                        amount = :amount,
                        amortization_date = :amortization_date,
                        asset_group_id = :asset_group_id,
                        use_half_rate = :use_half_rate,
                        notes = :notes,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    'id': item_id,
                    'mark_id': data.get('mark_id'),
                    'description': data.get('description'),
                    'amount': data.get('amount'),
                    'amortization_date': data.get('amortization_date'),
                    'asset_group_id': data.get('asset_group_id'),
                    'use_half_rate': data.get('use_half_rate'),
                    'notes': data.get('notes')
                }
            )
            conn.commit()
            return jsonify({'id': item_id, **data})
    except Exception as e:
        app.logger.error(f"Failed to update amortization item: {e}")
        return jsonify({'error': str(e)}), 500

@amortization_bp.route('/api/amortization-items/<item_id>', methods=['DELETE'])
def delete_amortization_item(item_id):
    """Delete an amortization item"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM amortization_items WHERE id = :id"), {'id': item_id})
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Failed to delete amortization item: {e}")
        return jsonify({'error': str(e)}), 500
