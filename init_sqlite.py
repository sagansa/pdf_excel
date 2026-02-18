#!/usr/bin/env python3
"""
Initialize SQLite database with required tables for the pdf_excel application
"""

import os
import sqlite3
from datetime import datetime

def init_sqlite_db():
    """Initialize SQLite database with all required tables"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'database.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Creating SQLite database tables...")
    
    # Create companies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create chart_of_accounts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            id TEXT PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            normal_balance TEXT DEFAULT 'DEBIT',
            account_type TEXT,
            account_subtype TEXT,
            is_active BOOLEAN DEFAULT 1,
            company_id TEXT,
            parent_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert basic COA codes
    cursor.execute("""
        INSERT OR IGNORE INTO chart_of_accounts (id, code, name, normal_balance) 
        VALUES 
            ('1421', '1421', 'Biaya Dibayar di Muka', 'DEBIT'),
            ('5315', '5315', 'Beban Sewa', 'DEBIT'),
            ('2191', '2191', 'Utang Pajak', 'CREDIT')
    """)
    
    # Create marks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id TEXT PRIMARY KEY,
            personal_use TEXT,
            internal_report TEXT,
            tax_report TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            txn_date DATE,
            description TEXT,
            amount DECIMAL(15,2),
            db_cr TEXT,
            bank_code TEXT,
            source_file TEXT,
            file_hash TEXT,
            mark_id TEXT,
            company_id TEXT,
            rental_contract_id TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mark_id) REFERENCES marks(id),
            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (rental_contract_id) REFERENCES rental_contracts(id)
        )
    """)
    
    # Create filters table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS filters (
            id TEXT PRIMARY KEY,
            view_name TEXT NOT NULL,
            filters TEXT,
            company_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create amortization_settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS amortization_settings (
            id TEXT PRIMARY KEY,
            company_id TEXT,
            setting_name TEXT NOT NULL,
            setting_value TEXT,
            setting_type TEXT DEFAULT 'text',
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert default prepaid settings
    cursor.execute("""
        INSERT OR IGNORE INTO amortization_settings 
        (id, company_id, setting_name, setting_value, setting_type, description) 
        VALUES 
            (LOWER(HEX(randomblob(16))), NULL, 'prepaid_prepaid_asset_coa', '1421', 'text', 'Default COA for Prepaid Assets (1421)'),
            (LOWER(HEX(randomblob(16))), NULL, 'prepaid_rent_expense_coa', '5315', 'text', 'Default COA for Rent Expenses (5315)'),
            (LOWER(HEX(randomblob(16))), NULL, 'prepaid_tax_payable_coa', '2191', 'text', 'Default COA for Tax Payables (2191)'),
            (LOWER(HEX(randomblob(16))), NULL, 'prepaid_default_tax_rate', '10', 'number', 'Default PPh 4(2) Tax Rate for Rent')
    """)
    
    # Create prepaid_expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prepaid_expenses (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            description TEXT NOT NULL,
            prepaid_coa_id TEXT,
            expense_coa_id TEXT,
            tax_payable_coa_id TEXT,
            start_date DATE,
            end_date DATE,
            duration_months INTEGER,
            amount_net DECIMAL(15,2) DEFAULT 0.00,
            amount_bruto DECIMAL(15,2) DEFAULT 0.00,
            monthly_amortization DECIMAL(15,2) DEFAULT 0.00,
            tax_rate DECIMAL(5,2) DEFAULT 10.00,
            is_gross_up BOOLEAN DEFAULT 0,
            notes TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create rental_locations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rental_locations (
            id TEXT PRIMARY KEY,
            company_id TEXT,
            location_name TEXT,
            address TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create rental_stores table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rental_stores (
            id TEXT PRIMARY KEY,
            company_id TEXT,
            store_name TEXT,
            store_code TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create rental_contracts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rental_contracts (
            id TEXT PRIMARY KEY,
            company_id TEXT,
            store_id TEXT,
            location_id TEXT,
            contract_number TEXT,
            landlord_name TEXT,
            start_date DATE,
            end_date DATE,
            total_amount DECIMAL(15,2),
            status TEXT DEFAULT 'active',
            notes TEXT,
            prepaid_expense_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create amortization_items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS amortization_items (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            description TEXT NOT NULL,
            coa_id TEXT NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            tax_rate DECIMAL(5,2) DEFAULT 0.00,
            useful_life_years INTEGER,
            acquisition_date DATE,
            is_active BOOLEAN DEFAULT 1,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (coa_id) REFERENCES chart_of_accounts(id)
        )
    """)
    
    # Create inventory_balances table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_balances (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            item_code TEXT,
            item_name TEXT,
            opening_quantity DECIMAL(10,2) DEFAULT 0.00,
            opening_value DECIMAL(15,2) DEFAULT 0.00,
            purchases_quantity DECIMAL(10,2) DEFAULT 0.00,
            purchases_value DECIMAL(15,2) DEFAULT 0.00,
            sales_quantity DECIMAL(10,2) DEFAULT 0.00,
            sales_value DECIMAL(15,2) DEFAULT 0.00,
            closing_quantity DECIMAL(10,2) DEFAULT 0.00,
            closing_value DECIMAL(15,2) DEFAULT 0.00,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert sample data
    cursor.execute("""
        INSERT OR IGNORE INTO companies (id, name, description) 
        VALUES ('demo-company', 'Demo Company', 'Sample company for testing')
    """)
    
    cursor.execute("""
        INSERT OR IGNORE INTO marks (id, personal_use, internal_report, tax_report)
        VALUES 
            ('mark-sewa', 'sewa', 'sewa', 'sewa'),
            ('mark-operasional', 'operasional', 'operasional', 'operasional')
    """)
    
    # Insert sample transactions
    cursor.execute("""
        INSERT OR IGNORE INTO transactions (id, txn_date, description, amount, db_cr, company_id, mark_id)
        VALUES 
            ('txn-1', '2024-01-15', 'Pembayaran Sewa Toko Januari', 5000000, 'CR', 'demo-company', 'mark-sewa'),
            ('txn-2', '2024-02-15', 'Pembayaran Sewa Toko Februari', 5000000, 'CR', 'demo-company', 'mark-sewa'),
            ('txn-3', '2024-01-10', 'Biaya Listrik', 1500000, 'CR', 'demo-company', 'mark-operasional')
    """)
    
    # Insert sample location and store
    cursor.execute("""
        INSERT OR IGNORE INTO rental_locations (id, company_id, location_name, address)
        VALUES ('loc-1', 'demo-company', 'Tokopedia Tower', 'Jakarta Selatan')
    """)
    
    cursor.execute("""
        INSERT OR IGNORE INTO rental_stores (id, company_id, store_name, store_code)
        VALUES ('store-1', 'demo-company', 'Toko Mainan', 'TM001')
    """)
    
    conn.commit()
    conn.close()
    
    print("SQLite database initialization completed successfully!")

if __name__ == "__main__":
    init_sqlite_db()
