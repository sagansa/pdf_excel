#!/usr/bin/env python3
"""
Debug specific financial reports endpoints to see exact errors
"""

import urllib.request
import json

def debug_reports():
    """Debug reports endpoints with exact error details"""
    base_url = 'http://127.0.0.1:5001'
    
    # Get first company
    try:
        req = urllib.request.Request(f'{base_url}/api/companies')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                companies = data.get('companies', [])
                if companies:
                    company_id = companies[0]['id']
                    company_name = companies[0]['name']
                    print(f"Using company: {company_name} (ID: {company_id})")
                else:
                    print("No companies found!")
                    return
            else:
                print(f"Error getting companies: {response.status}")
                return
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Test failing endpoints one by one
    failing_endpoints = [
        ('/api/reports/income-statement', 'Income Statement', {'start_date': '2024-01-01', 'end_date': '2024-12-31'}),
        ('/api/reports/balance-sheet', 'Balance Sheet', {'date': '2024-12-31'}),
        ('/api/reports/coa-detail', 'COA Detail', {'start_date': '2024-01-01', 'end_date': '2024-12-31'}),
        ('/api/reports/amortization-items', 'Amortization Items', {}),
        ('/api/reports/inventory-balances', 'Inventory Balances', {'year': 2024}),
    ]
    
    for endpoint, description, params in failing_endpoints:
        print(f"\n{description}:")
        print(f"  Endpoint: {endpoint}")
        print(f"  Params: {params}")
        
        try:
            # Build URL with params
            url = f'{base_url}{endpoint}?company_id={company_id}'
            for key, value in params.items():
                url += f'&{key}={value}'
            
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                print(f"  Status: {response.status}")
                content = response.read().decode()
                
                if response.status == 200:
                    data = json.loads(content)
                    print(f"  Success: {type(data)} with {len(str(data))} chars")
                    if isinstance(data, dict):
                        print(f"  Keys: {list(data.keys())}")
                    elif isinstance(data, list):
                        print(f"  List length: {len(data)}")
                else:
                    print(f"  Error response: {content[:300]}...")
                    
        except Exception as e:
            print(f"  Connection error: {e}")

if __name__ == "__main__":
    debug_reports()
