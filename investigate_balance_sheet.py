#!/usr/bin/env python3
"""
Investigasi lengkap balance sheet untuk menemukan masalah
"""

import sys, os, json
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import create_engine, text

def investigate_balance_sheet():
    # Database connection
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASS = os.environ.get('DB_PASS', 'root')
    DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'bank_converter')
    
    DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    try:
        engine = create_engine(DB_URL)
        
        with engine.connect() as conn:
            print("=== INVESTIGASI BALANCE SHEET ===")
            
            # 1. Cek asset COAs yang seharusnya ada
            print("\n1. ASSET COAs yang ada:")
            asset_query = text("""
                SELECT code, name, subcategory, normal_balance
                FROM chart_of_accounts 
                WHERE category = 'ASSET' AND is_active = TRUE
                ORDER BY code
            """)
            
            asset_result = conn.execute(asset_query)
            for row in asset_result:
                print(f"  {row.code}: {row.name} - {row.subcategory} - NB: {row.normal_balance}")
            
            # 2. Cek amortization assets yang aktif
            print("\n2. AMORTIZATION ASSETS yang aktif:")
            amort_query = text("""
                SELECT id, name, original_cost, acquisition_date, useful_life_years, 
                       depreciation_method, is_active
                FROM amortization_assets 
                WHERE is_active = TRUE
                ORDER BY name
            """)
            
            amort_result = conn.execute(amort_query)
            total_original_cost = 0
            for row in amort_result:
                total_original_cost += float(row.original_cost or 0)
                print(f"  {row.name}: Rp {float(row.original_cost or 0):,.2f}")
            
            print(f"\nTotal Original Cost Amortization: Rp {total_original_cost:,.2f}")
            
            # 3. Cek akumulasi penyusutan COAs
            print("\n3. AKUMULASI PENYUSUTAN COAs:")
            acc_depr_query = text("""
                SELECT code, name, normal_balance
                FROM chart_of_accounts 
                WHERE code LIKE '13%' AND category = 'ASSET' AND is_active = TRUE
                ORDER BY code
            """)
            
            acc_depr_result = conn.execute(acc_depr_query)
            for row in acc_depr_result:
                print(f"  {row.code}: {row.name} - NB: {row.normal_balance}")
            
            # 4. Cek inventory balances
            print("\n4. INVENTORY BALANCES:")
            inv_query = text("""
                SELECT year, beginning_inventory_amount, ending_inventory_amount
                FROM inventory_balances 
                WHERE year >= :min_year
                ORDER BY year DESC
                LIMIT 3
            """)
            
            inv_result = conn.execute(inv_query, {'min_year': 2023})
            for row in inv_result:
                print(f"  {row.year}: Awal Rp {float(row.beginning_inventory_amount or 0):,.2f}, Akhir Rp {float(row.ending_inventory_amount or 0):,.2f}")
            
            # 5. Test balance sheet API
            print("\n5. BALANCE SHEET API TEST:")
            try:
                import urllib.request
                api_url = "http://localhost:5001/api/reports/balance-sheet?as_of_date=2025-12-31"
                with urllib.request.urlopen(api_url) as response:
                    api_data = json.loads(response.read().decode())
                    
                    print(f"  Total Assets API: Rp {api_data.get('total_assets', 0):,.2f}")
                    print(f"  Total Liabilities API: Rp {api_data.get('total_liabilities', 0):,.2f}")
                    print(f"  Total Equity API: Rp {api_data.get('total_equity', 0):,.2f}")
                    print(f"  Is Balanced: {api_data.get('is_balanced', False)}")
                    
                    assets = api_data.get('assets', {})
                    current_assets = assets.get('current', [])
                    non_current_assets = assets.get('non_current', [])
                    
                    print(f"  Current Assets count: {len(current_assets)}")
                    print(f"  Non-Current Assets count: {len(non_current_assets)}")
                    
                    if len(current_assets) > 0:
                        print("  Current Assets:")
                        for asset in current_assets:
                            print(f"    {asset.get('code', 'N/A')}: {asset.get('name', 'N/A')} = Rp {asset.get('amount', 0):,.2f}")
                    
                    if len(non_current_assets) > 0:
                        print("  Non-Current Assets:")
                        for asset in non_current_assets:
                            print(f"    {asset.get('code', 'N/A')}: {asset.get('name', 'N/A')} = Rp {asset.get('amount', 0):,.2f}")
                    
            except Exception as e:
                print(f"  ❌ API Error: {e}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = investigate_balance_sheet()
    sys.exit(0 if success else 1)
