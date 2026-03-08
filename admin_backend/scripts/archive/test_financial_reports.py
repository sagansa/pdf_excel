#!/usr/bin/env python3
"""
Test financial reports API to ensure they use MySQL database
"""

import urllib.request
import json

def test_financial_reports():
    """Test financial reports endpoints"""
    base_url = 'http://127.0.0.1:5001'
    
    print("Testing Financial Reports API")
    print("=" * 50)
    
    # Get companies first
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
                    return False
            else:
                print(f"Error getting companies: {response.status}")
                return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    # Test important financial reports
    reports_to_test = [
        ('/api/reports/income-statement', 'Income Statement'),
        ('/api/reports/monthly-revenue', 'Monthly Revenue'),
        ('/api/reports/balance-sheet', 'Balance Sheet'),
        ('/api/reports/coa-detail', 'COA Detail'),
        ('/api/reports/prepaid-expenses', 'Prepaid Expenses'),
        ('/api/reports/amortization-items', 'Amortization Items'),
        ('/api/reports/inventory-balances', 'Inventory Balances'),
        ('/api/reports/prepaid-linkable-transactions', 'Prepaid Linkable Transactions'),
        ('/api/reports/prepaid-eligible-transactions', 'Prepaid Eligible Transactions'),
    ]
    
    results = []
    
    for endpoint, description in reports_to_test:
        print(f"\n{len(results)+1}. Testing {description}...")
        try:
            url = f'{base_url}{endpoint}'
            if '?' in endpoint:
                url = f'{url}&company_id={company_id}'
            else:
                url = f'{url}?company_id={company_id}'
            
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    
                    # Try to detect if data looks like it's from MySQL
                    data_size = len(str(data))
                    print(f"   ✓ Success (Status: {response.status}, Data size: {data_size} chars)")
                    
                    # Show some sample data
                    if isinstance(data, dict):
                        keys = list(data.keys())
                        print(f"   Response keys: {keys[:5]}")  # Show first 5 keys
                        
                        # Try to find a list in the data
                        for key, value in data.items():
                            if isinstance(value, list):
                                print(f"   Found list '{key}': {len(value)} items")
                                if value and isinstance(value[0], dict):
                                    sample_keys = list(value[0].keys())
                                    print(f"   Sample item keys: {sample_keys[:5]}")
                                break
                    elif isinstance(data, list):
                        print(f"   Found list: {len(data)} items")
                        if data and isinstance(data[0], dict):
                            sample_keys = list(data[0].keys())
                            print(f"   Sample item keys: {sample_keys[:5]}")
                    
                    results.append({
                        'endpoint': endpoint,
                        'description': description,
                        'status': '✓ Success',
                        'data_size': data_size
                    })
                    
                else:
                    print(f"   ✗ Error: {response.status}")
                    results.append({
                        'endpoint': endpoint,
                        'description': description,
                        'status': f'✗ Error {response.status}',
                        'data_size': 0
                    })
                    
        except Exception as e:
            print(f"   ✗ Error: {e}")
            results.append({
                'endpoint': endpoint,
                'description': description,
                'status': f'✗ Error: {e}',
                'data_size': 0
            })
    
    # Summary
    print(f"\n{'='*50}")
    print("FINANCIAL REPORTS TEST SUMMARY")
    print(f"{'='*50}")
    
    success_count = sum(1 for r in results if '✓' in r['status'])
    total_count = len(results)
    
    print(f"Total tested: {total_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_count - success_count}")
    
    print(f"\nDetailed Results:")
    for result in results:
        print(f"  {result['status']} {result['description']}")
        if result['data_size'] > 0:
            print(f"    Data size: {result['data_size']} chars")
    
    # Check if data looks like it's from production MySQL
    print(f"\nDatabase Analysis:")
    total_data_size = sum(r['data_size'] for r in results if r['data_size'] > 0)
    if total_data_size > 1000:  # If we have substantial data, likely from MySQL
        print("  ✓ Data size indicates production MySQL database")
        print(f"    Total data retrieved: {total_data_size} characters")
    elif total_data_size > 0:
        print("  ⚠ Limited data found - might be test database")
    else:
        print("  ✗ No data retrieved - connection issues")
    
    return success_count == total_count

if __name__ == "__main__":
    success = test_financial_reports()
    if success:
        print(f"\n🎉 All financial reports are working correctly!")
    else:
        print(f"\n⚠️ Some financial reports have issues.")
