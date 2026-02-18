import logging
import calendar
from datetime import datetime, date
from sqlalchemy import text

logger = logging.getLogger(__name__)

def fetch_balance_sheet_data(conn, as_of_date, company_id=None):
    """
    Helper function to fetch balance sheet data.
    Returns calculated values and lists of items.
    """
    as_of_date_obj = datetime.strptime(as_of_date, '%Y-%m-%d').date()

    # 1. Get asset, liability, and equity COA balances
    query = text("""
        WITH coa_balances AS (
            SELECT 
                mcm.coa_id,
                SUM(CASE WHEN t.db_cr = 'CR' THEN -t.amount ELSE t.amount END) as total_amount
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
            WHERE t.txn_date <= :as_of_date
                AND (:company_id IS NULL OR t.company_id = :company_id)
            GROUP BY mcm.coa_id
        )
        SELECT
            coa.id,
            coa.code,
            coa.name,
            coa.category,
            coa.subcategory,
            COALESCE(b.total_amount, 0) as total_amount
        FROM chart_of_accounts coa
        LEFT JOIN coa_balances b ON b.coa_id = coa.id
        WHERE coa.category IN ('ASSET', 'LIABILITY', 'EQUITY')
            AND coa.is_active = TRUE
            AND COALESCE(b.total_amount, 0) != 0
        ORDER BY coa.code
    """)

    result = conn.execute(query, {
        'as_of_date': as_of_date,
        'company_id': company_id
    })

    assets_current = []
    assets_non_current = []
    liabilities_current = []
    liabilities_non_current = []
    equity = []

    total_assets = 0
    total_liabilities = 0
    total_equity = 0

    for row in result:
        d = dict(row._mapping)
        amount = float(d['total_amount']) if d['total_amount'] else 0

        item = {
            'id': d['id'],
            'code': d['code'],
            'name': d['name'],
            'subcategory': d['subcategory'],
            'amount': amount,
            'category': d['category']
        }

        # Determine asset/non-asset based on code prefix
        if d['category'] == 'ASSET':
            # Current assets: 1xxx
            if d['code'] and d['code'].startswith('1'):
                assets_current.append(item)
            # Non-current assets: 1xxx (other than current)
            else:
                assets_non_current.append(item)
            total_assets += amount
        elif d['category'] == 'LIABILITY':
            # Current liabilities: 2xxx
            if d['code'] and d['code'].startswith('2'):
                liabilities_current.append(item)
            # Non-current liabilities
            else:
                liabilities_non_current.append(item)
            total_liabilities += amount
        elif d['category'] == 'EQUITY':
            equity.append(item)
            total_equity += amount

    return {
        'as_of_date': as_of_date,
        'assets': {
            'current': assets_current,
            'non_current': assets_non_current,
            'total': total_assets
        },
        'liabilities': {
            'current': liabilities_current,
            'non_current': liabilities_non_current,
            'total': total_liabilities
        },
        'equity': {
            'items': equity,
            'total': total_equity
        },
        'total_liabilities_and_equity': total_liabilities + total_equity,
        'is_balanced': abs(total_assets - (total_liabilities + total_equity)) < 0.01
    }

def fetch_income_statement_data(conn, start_date, end_date, company_id=None):
    """
    Helper function to fetch income statement data.
    Returns calculated values and lists of items.
    """
    query = text("""
        SELECT 
            coa.code,
            coa.name,
            coa.category,
            coa.subcategory,
            SUM(
                CASE 
                    WHEN t.db_cr = 'CR' AND mcm.mapping_type = 'CREDIT' THEN t.amount
                    WHEN t.db_cr = 'CR' AND mcm.mapping_type = 'DEBIT' THEN -t.amount
                    WHEN t.db_cr = 'DB' AND mcm.mapping_type = 'DEBIT' THEN t.amount
                    WHEN t.db_cr = 'DB' AND mcm.mapping_type = 'CREDIT' THEN -t.amount
                    ELSE 0
                END
            ) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
            AND coa.category IN ('REVENUE', 'EXPENSE')
            AND (:company_id IS NULL OR t.company_id = :company_id)
        GROUP BY coa.id, coa.code, coa.name, coa.category, coa.subcategory
        ORDER BY coa.code
    """)
    
    result = conn.execute(query, {
        'start_date': start_date,
        'end_date': end_date,
        'company_id': company_id
    })
    
    revenue = []
    expenses = []
    total_revenue = 0
    total_expenses = 0
    
    for row in result:
        d = dict(row._mapping)
        amount = float(d['total_amount']) if d['total_amount'] else 0
        
        item = {
            'code': d['code'],
            'name': d['name'],
            'subcategory': d['subcategory'],
            'amount': amount,
            'category': d['category'] 
        }
        
        if d['category'] == 'REVENUE':
            revenue.append(item)
            total_revenue += amount
        else:  # EXPENSE
            expenses.append(item)
            total_expenses += amount
    
    # 2.5 Add 5314 (Amortisasi Aktiva Berwujud) from Calculated + Manual Amortization
    calculated_amort_total = 0
    try:
        # Get calculated asset amortization
        assets_query = text("""
            SELECT 
                a.id, a.asset_name, a.acquisition_cost, a.residual_value,
                a.amortization_start_date, a.book_value,
                ag.group_number, ag.group_name, ag.asset_type,
                ag.tarif_rate, ag.tarif_half_rate, ag.useful_life_years
            FROM amortization_assets a
            INNER JOIN amortization_asset_groups ag ON a.asset_group_id = ag.id
            WHERE (a.company_id = :company OR :company IS NULL)
            AND a.is_active = TRUE
            AND a.is_fully_amortized = FALSE
        """)
        assets_result = conn.execute(assets_query, {'company': company_id})
        
        for row in assets_result:
            asset = dict(row._mapping)
            a_start_date = asset.get('amortization_start_date')
            acquisition_cost = float(asset.get('acquisition_cost', 0))
            residual_value = float(asset.get('residual_value', 0))
            tarif_rate = float(asset.get('tarif_rate', 20))
            useful_life = int(asset.get('useful_life_years', 5))
            
            if a_start_date:
                if isinstance(a_start_date, str):
                    a_start_date = datetime.strptime(a_start_date[:10], '%Y-%m-%d').date()
            else:
                continue
            
            report_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            report_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            report_year = report_start.year
            
            if a_start_date.year > report_year:
                continue
            
            base_amount = acquisition_cost - residual_value
            annual_amort = base_amount * (tarif_rate / 100)
            
            if a_start_date.year == report_year:
                months_active = report_end.month - a_start_date.month + 1
                if months_active > 12:
                    months_active = 12
                annual_amort = annual_amort * (months_active / 12)
            else:
                years_passed = report_year - a_start_date.year
                if years_passed >= useful_life:
                    annual_amort = 0
                annual_amort = min(annual_amort, base_amount)
            
            calculated_amort_total += annual_amort
        
        # Get manual amortization items
        manual_query = text("""
            SELECT ai.*, coa.code as coa_code, coa.name as coa_name
            FROM amortization_items ai
            INNER JOIN chart_of_accounts coa ON ai.coa_id = coa.id
            WHERE (ai.company_id = :company OR :company IS NULL)
            AND coa.code = '5314'
        """)
        manual_result = conn.execute(manual_query, {'company': company_id})
        
        manual_amort_total = 0
        for row in manual_result:
            d = dict(row._mapping)
            item_year = d.get('year')
            if item_year:
                if isinstance(item_year, str):
                    try:
                        item_year = int(item_year)
                    except:
                        pass
                report_year = datetime.strptime(start_date, '%Y-%m-%d').year
                if item_year != report_year:
                    continue
            
            annual_amount = d.get('amount', 0)
            if annual_amount:
                manual_amort_total += float(annual_amount)
        
        # Add 5314 to expenses
        total_5314_amort = calculated_amort_total + manual_amort_total
        if total_5314_amort > 0:
            expenses.append({
                'code': '5314',
                'name': 'Amortisasi Aktiva Berwujud',
                'subcategory': 'Operating Expenses',
                'amount': total_5314_amort,
                'category': 'EXPENSE'
            })
            total_expenses += total_5314_amort
    except Exception as e:
        logger.error(f"Failed to fetch amortization for 5314: {e}")
    
    # 3. Add 5315 (Beban Sewa) from Prepaid Expenses
    try:
        prepaid_query = text("""
            SELECT p.*, coa.code as expense_coa_code
            FROM prepaid_expenses p
            INNER JOIN chart_of_accounts coa ON p.expense_coa_id = coa.id
            WHERE (p.company_id = :company OR :company IS NULL)
            AND p.is_active = TRUE
            AND coa.code = '5315'
        """)
        prepaid_result = conn.execute(prepaid_query, {'company': company_id})
        
        # Calculate amortization for period
        report_start = datetime.strptime(start_date, '%Y-%m-%d').date()
        report_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        prepaid_5315_amortization = 0
        for row in prepaid_result:
            p_item = dict(row._mapping)
            p_start = p_item['start_date']
            if isinstance(p_start, str):
                p_start = datetime.strptime(p_start[:10], '%Y-%m-%d').date()
            
            duration = int(p_item['duration_months'])
            bruto = float(p_item['amount_bruto'])
            monthly = bruto / duration if duration > 0 else bruto
            
            # Calculate period end date
            if duration > 0:
                # Manual calculation: add months to start date
                year = p_start.year + (p_start.month - 1 + duration) // 12
                month = (p_start.month - 1 + duration) % 12
                if month == 0:
                    month = 12
                    year -= 1
                # Get last day of the target month
                last_day = calendar.monthrange(year, month)[1]
                p_end = date(year, month, last_day)
            else:
                p_end = p_start
            
            # Calculate intersection between [p_start, p_end] and [report_start, report_end]
            overlap_start = max(p_start, report_start)
            overlap_end = min(p_end, report_end)
            
            if overlap_start <= overlap_end:
                # Calculate number of months in overlap
                diff_years = overlap_end.year - overlap_start.year
                diff_months = overlap_end.month - overlap_start.month
                months_in_period = (diff_years * 12) + diff_months + 1
                
                period_expense = round(monthly * months_in_period, 2)
                prepaid_5315_amortization += period_expense
        
        # Add to expenses if has value
        if prepaid_5315_amortization > 0:
            expenses.append({
                'code': '5315',
                'name': 'Beban Sewa',
                'subcategory': 'Operating Expenses',
                'amount': prepaid_5315_amortization,
                'category': 'EXPENSE'
            })
            total_expenses += prepaid_5315_amortization
    except Exception as e:
        logger.error(f"Failed to fetch prepaid amortization: {e}")
    
    # 2. Handle COGS (HPP) with Manual Inventory Adjustments
    beginning_inv = 0
    ending_inv = 0
    
    # We use start_date's year for the inventory balance
    year = datetime.strptime(start_date, '%Y-%m-%d').year
    
    try:
        inventory_query = text("""
            SELECT beginning_inventory_amount, ending_inventory_amount
            FROM inventory_balances
            WHERE year = :year AND (:company_id IS NULL OR company_id = :company_id)
            LIMIT 1
        """)
        inv_result = conn.execute(inventory_query, {'year': year, 'company_id': company_id}).fetchone()
        if inv_result:
            beginning_inv = float(inv_result[0] or 0)
            ending_inv = float(inv_result[1] or 0)
    except Exception as e:
        logger.error(f"Failed to fetch inventory balances: {e}")

    # Identify 'Purchases' and 'Other COGS' from expenses
    purchases = 0
    other_cogs_items = []
    
    cogs_items = [e for e in expenses if e.get('subcategory') == 'Cost of Goods Sold']
    
    for item in cogs_items:
        if item['code'] == '5001':
            purchases += item['amount']
        else:
            other_cogs_items.append(item)
    
    total_other_cogs = sum(item['amount'] for item in other_cogs_items)
    calculate_hpp = beginning_inv + purchases + total_other_cogs - ending_inv
    
    # Provide a specific breakdown for the UI
    cogs_breakdown = {
        'beginning_inventory': beginning_inv,
        'purchases': purchases,
        'other_cogs_items': other_cogs_items,
        'total_other_cogs': total_other_cogs,
        'ending_inventory': ending_inv,
        'total_cogs': calculate_hpp,
        'year': year
    }

    return {
        'revenue': revenue,
        'expenses': [e for e in expenses if e.get('subcategory') != 'Cost of Goods Sold'],
        'total_revenue': total_revenue,
        'total_expenses': total_expenses - sum(e['amount'] for e in cogs_items),
        'cogs_breakdown': cogs_breakdown,
        'net_income': total_revenue - (total_expenses - sum(e['amount'] for e in cogs_items)) - calculate_hpp
    }

def fetch_monthly_revenue_data(conn, year, company_id=None):
    """
    Fetch total revenue grouped by month for a specific year.
    Used for Coretax summary.
    """
    query = text("""
        SELECT 
            MONTH(t.txn_date) as month_num,
            SUM(
                CASE 
                    WHEN t.db_cr = 'CR' AND mcm.mapping_type = 'CREDIT' THEN t.amount
                    WHEN t.db_cr = 'CR' AND mcm.mapping_type = 'DEBIT' THEN -t.amount
                    WHEN t.db_cr = 'DB' AND mcm.mapping_type = 'DEBIT' THEN t.amount
                    WHEN t.db_cr = 'DB' AND mcm.mapping_type = 'CREDIT' THEN -t.amount
                    ELSE 0
                END
            ) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE YEAR(t.txn_date) = :year
            AND coa.category = 'REVENUE'
            AND (:company_id IS NULL OR t.company_id = :company_id)
        GROUP BY MONTH(t.txn_date)
        ORDER BY month_num
    """)
    
    result = conn.execute(query, {
        'year': year,
        'company_id': company_id
    })
    
    # Initialize all months with 0
    monthly_data = {i: 0.0 for i in range(1, 13)}
    
    for row in result:
        d = dict(row._mapping)
        if d['month_num']:
            monthly_data[int(d['month_num'])] = float(d['total_amount']) if d['total_amount'] else 0.0
            
    # Convert to list of objects for easier frontend consumption
    return [
        {'month': m, 'revenue': monthly_data[m]} 
        for m in range(1, 13)
    ]
