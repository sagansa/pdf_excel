import uuid
import datetime
from sqlalchemy import text
from backend.db.session import get_db_engine

def get_prepaid_settings(company_id):
    """Retrieve prepaid expense settings for a company"""
    settings = {}
    if not company_id:
        return settings
        
    engine, _ = get_db_engine()
    with engine.connect() as conn:
        # Check settings from both amortization_settings (if they exist there) or companies table
        query = text("""
            SELECT * FROM amortization_settings 
            WHERE company_id = :company_id
        """)
        result = conn.execute(query, {'company_id': company_id}).fetchone()
        if result:
            settings = dict(result._mapping)
    return settings

def create_or_update_prepaid_from_contract(contract_id, company_id):
    """Create or update prepaid expense entry from a rental contract"""
    if not company_id:
        return {}
        
    engine, _ = get_db_engine()
    
    with engine.begin() as conn:
        # Get contract details
        contract = conn.execute(text("""
            SELECT c.*, s.store_name, l.location_name
            FROM rental_contracts c
            JOIN rental_stores s ON c.store_id = s.id
            JOIN rental_locations l ON c.location_id = l.id
            WHERE c.id = :id
        """), {'id': contract_id}).fetchone()
        
        if not contract:
            return {}
            
        # Sum linked transactions
        result = conn.execute(text("""
            SELECT SUM(ABS(amount)) FROM transactions 
            WHERE rental_contract_id = :id
        """), {'id': contract_id}).fetchone()
        
        total_amount = float(result[0] or 0)
        if total_amount == 0:
            total_amount = float(contract.total_amount or 0)
            
        # Calculate duration
        start_date = contract.start_date
        end_date = contract.end_date
        
        if isinstance(start_date, str):
            start_date = datetime.date.fromisoformat(start_date[:10])
        elif isinstance(start_date, datetime.datetime):
            start_date = start_date.date()
            
        if isinstance(end_date, str):
            end_date = datetime.date.fromisoformat(end_date[:10])
        elif isinstance(end_date, datetime.datetime):
            end_date = end_date.date()
            
        duration_days = (end_date - start_date).days
        duration_months = max(1, round(duration_days / 30.44))
        
        # Default COA codes if settings not found
        # In a real system these would come from the mapping or settings
        # For now we use common Indonesian COA codes for Prepaid (1104) and Rent Expense (5315)
        # We need the IDs for these COAs
        prepaid_coa_id = None
        expense_coa_id = None
        
        coa_res = conn.execute(text("SELECT id FROM chart_of_accounts WHERE code = '1105' LIMIT 1")).fetchone()
        if coa_res: prepaid_coa_id = coa_res[0]
        
        coa_res = conn.execute(text("SELECT id FROM chart_of_accounts WHERE code = '5315' LIMIT 1")).fetchone()
        if coa_res: expense_coa_id = coa_res[0]
        
        # Calculate Gross-up
        tax_rate = 10.0
        amount_bruto = total_amount / (1 - (tax_rate / 100))
        monthly_amount = amount_bruto / duration_months
        
        description = f"Sewa {contract.store_name} - {contract.location_name}"
        
        # Check if already has prepaid
        prepaid_id = contract.prepaid_expense_id
        is_new = False
        
        if prepaid_id:
            existing = conn.execute(text("SELECT id FROM prepaid_expenses WHERE id = :id"), {'id': prepaid_id}).fetchone()
            if not existing:
                prepaid_id = None
        
        if not prepaid_id:
            prepaid_id = str(uuid.uuid4())
            is_new = True
            
            # Insert using correct column names from DESCRIBE: contract_id, prepaid_coa_id
            query = text("""
                INSERT INTO prepaid_expenses (
                    id, company_id, contract_id, description,
                    prepaid_coa_id, expense_coa_id,
                    start_date, end_date, duration_months,
                    amount_bruto, monthly_amortization, tax_rate,
                    created_at, updated_at
                ) VALUES (
                    :id, :company_id, :contract_id, :description,
                    :prepaid_coa_id, :expense_coa_id,
                    :start_date, :end_date, :duration,
                    :bruto, :monthly, :tax_rate,
                    NOW(), NOW()
                )
            """)
        else:
            # Update
            query = text("""
                UPDATE prepaid_expenses SET
                    description = :description,
                    start_date = :start_date,
                    end_date = :end_date,
                    duration_months = :duration,
                    amount_bruto = :bruto,
                    monthly_amortization = :monthly,
                    tax_rate = :tax_rate,
                    updated_at = NOW()
                WHERE id = :id
            """)
            
        conn.execute(query, {
            'id': prepaid_id,
            'company_id': company_id,
            'contract_id': contract_id,
            'description': description,
            'prepaid_coa_id': prepaid_coa_id,
            'expense_coa_id': expense_coa_id,
            'start_date': start_date,
            'end_date': end_date,
            'duration': duration_months,
            'bruto': amount_bruto,
            'monthly': monthly_amount,
            'tax_rate': tax_rate
        })
        
        if is_new:
            # Update contract back
            conn.execute(text("UPDATE rental_contracts SET prepaid_expense_id = :prepaid_id WHERE id = :contract_id"),
                        {'prepaid_id': prepaid_id, 'contract_id': contract_id})
            
        return {
            'created': is_new,
            'updated': not is_new,
            'prepaid_id': prepaid_id,
            'total_amount': total_amount,
            'amount_bruto': amount_bruto
        }
