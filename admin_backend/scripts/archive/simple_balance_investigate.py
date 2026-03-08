#!/usr/bin/env python3
"""
Investigasi sederhana balance sheet
"""

import sys, os, json, urllib.request

def simple_balance_investigate():
    print("=== BALANCE SHEET INVESTIGATION ===")
    
    # 1. Test API response
    try:
        api_url = "http://localhost:5001/api/reports/balance-sheet?as_of_date=2025-12-31"
        with urllib.request.urlopen(api_url) as response:
            data = json.loads(response.read().decode())
            
            print(f"Total Assets: Rp {data.get('total_assets', 0):,.2f}")
            print(f"Total Liabilities: Rp {data.get('total_liabilities', 0):,.2f}")
            print(f"Total Equity: Rp {data.get('total_equity', 0):,.2f}")
            print(f"Is Balanced: {data.get('is_balanced', False)}")
            
            # Asset breakdown
            assets = data.get('assets', {})
            current_assets = assets.get('current', [])
            non_current_assets = assets.get('non_current', [])
            
            print(f"\nCurrent Assets ({len(current_assets)}):")
            for asset in current_assets:
                print(f"  {asset.get('code', 'N/A')}: {asset.get('name', 'N/A')} = Rp {asset.get('amount', 0):,.2f}")
            
            print(f"\nNon-Current Assets ({len(non_current_assets)}):")
            for asset in non_current_assets:
                print(f"  {asset.get('code', 'N/A')}: {asset.get('name', 'N/A')} = Rp {asset.get('amount', 0):,.2f}")
                
            print(f"\nAsset Total: Rp {assets.get('total', 0):,.2f}")
            
            # Liabilities breakdown
            liabilities = data.get('liabilities', {})
            current_liab = liabilities.get('current', [])
            non_current_liab = liabilities.get('non_current', [])
            
            print(f"\nCurrent Liabilities ({len(current_liab)}):")
            for liab in current_liab:
                print(f"  {liab.get('code', 'N/A')}: {liab.get('name', 'N/A')} = Rp {liab.get('amount', 0):,.2f}")
            
            print(f"\nNon-Current Liabilities ({len(non_current_liab)}):")
            for liab in non_current_liab:
                print(f"  {liab.get('code', 'N/A')}: {liab.get('name', 'N/A')} = Rp {liab.get('amount', 0):,.2f}")
                
            print(f"\nLiability Total: Rp {liabilities.get('total', 0):,.2f}")
            
            # Equity breakdown
            equity = data.get('equity', {})
            equity_items = equity.get('items', [])
            
            print(f"\nEquity Items ({len(equity_items)}):")
            for eq in equity_items:
                print(f"  {eq.get('code', 'N/A')}: {eq.get('name', 'N/A')} = Rp {eq.get('amount', 0):,.2f}")
                
            print(f"\nEquity Total: Rp {equity.get('total', 0):,.2f}")
            
            # Manual calculation checks
            print(f"\n=== MANUAL CALCULATION CHECK ===")
            manual_assets = sum(asset.get('amount', 0) for asset in current_assets + non_current_assets)
            manual_liabilities = sum(liab.get('amount', 0) for liab in current_liab + non_current_liab)
            manual_equity = sum(eq.get('amount', 0) for eq in equity_items)
            
            print(f"Manual Assets: Rp {manual_assets:,.2f}")
            print(f"Manual Liabilities: Rp {manual_liabilities:,.2f}")
            print(f"Manual Equity: Rp {manual_equity:,.2f}")
            
            print(f"Balance Check: Assets ({manual_assets}) = Liabilities ({manual_liabilities}) + Equity ({manual_equity})?")
            balance_diff = manual_assets - (manual_liabilities + manual_equity)
            print(f"Balance Difference: Rp {balance_diff:,.2f}")
            
            if abs(balance_diff) < 0.01:
                print("✅ BALANCED!")
            else:
                print("❌ NOT BALANCED!")
                
            # Check for missing assets
            print(f"\n=== CHECKING FOR ASSET ISSUES ===")
            
            expected_assets = ['1101', '1102', '1103', '1104', '1105', '1122', '1123', '1124', '1125', '1131', '1181', '1200', '1401', '1405', '1421', '1422', '1423', '1499']
            expected_non_current = ['1501', '1520', '1523', '1524', '1529', '1530', '1531', '1533', '1534', '1551', '1599', '1600', '1601', '1611', '1651', '1658', '1698']
            expected_depr = ['1301', '1302', '1303']
            
            current_asset_codes = [asset.get('code', '') for asset in current_assets]
            non_current_asset_codes = [asset.get('code', '') for asset in non_current_assets]
            
            missing_current = [code for code in expected_assets if code not in current_asset_codes]
            missing_non_current = [code for code in expected_non_current if code not in non_current_asset_codes]
            
            if missing_current:
                print(f"Missing Current Assets: {missing_current}")
            
            if missing_non_current:
                print(f"Missing Non-Current Assets: {missing_non_current}")
                
            print(f"Kas (1101) amount: Rp {next((asset.get('amount', 0) for asset in current_assets if asset.get('code') == '1101'), 0):,.2f}")
            
            if balance_diff != 0:
                print(f"\n=== POTENTIAL ISSUES ===")
                if missing_current:
                    print("❌ Some current assets are missing from balance sheet")
                if missing_non_current:
                    print("❌ Some non-current assets are missing from balance sheet")
                if manual_assets < 0:
                    print("❌ Total assets is negative - possible calculation error")
                    
    except Exception as e:
        print(f"❌ API Error: {e}")

if __name__ == "__main__":
    simple_balance_investigate()
