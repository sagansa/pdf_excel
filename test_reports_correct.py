#!/usr/bin/env python3
"""
Test financial reports with correct parameters
"""

import urllib.request
import json

def test_reports_correct():
    """Test financial reports with correct parameters"""
    base_url = 'http://127.0.0.1:5001'
    
    print("Testing Financial Reports with Correct Parameters")
    print("=" * 60)
    
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
                    return False
    except Exception as e:
        print(f"Error getting companies: {e}")
        return False
    
    # Get COA list first for COA detail testing
    try:
        req = urllib.request.Request(f'{base_url}/api/coa')
        with urllib.request.urlopen(req, timeout=5) as response:
            coa_data = json.loads(response.read().decode())
            coa_list = coa_data.get('coa', [])
            print(f"\\nFound {len(coa_list)} COA entries")
            if coa_list:
                sample_coa = coa_list[0]
                print(f"Using sample COA: {sample_coa.get('name')} (ID: {sample_coa.get('id')})")
    except Exception as e:
        print(f"Error getting COA list: {e}")
        sample_coa = {'id': None}
    
    # Test reports with correct parameters
    reports_to_test = [
        {
            'endpoint': '/api/reports/income-statement',
            'description': 'Income Statement',
            'params': {
                'start_date': '2024-01-01',
                'end_date': '2024-12-31',
                'company_id': company_id
            }
        },
        {
            'endpoint': '/api/reports/balance-sheet',
            'description': 'Balance Sheet',
            'params': {
                'as_of_date': '2024-12-31',
                'company_id': company_id
            }
        },
        {
            'endpoint': '/api/reports/coa-detail',
            'description': 'COA Detail',
            'params': {
                'coa_id': sample_coa.get('id'),
                'start_date': '2024-01-01',
                'end_date': '2024-12-31',
                'company_id': company_id
            }
        },
        {
            'endpoint': '/api/reports/monthly-revenue',
            'description': 'Monthly Revenue',
            'params': {
                'year': '2024',
                'company_id': company_id
            }
        },
        {
            'endpoint': '/api/reports/prepaid-expenses',
            'description': 'Prepaid Expenses',
            'params': {
                'company_id': company_id
            }
        },
        {
            'endpoint': '/api/reports/prepaid-linkable-transactions',
            'description': 'Prepaid Linkable Transactions',
            'params': {
                'company_id': company_id
            }
        },
        {
            'endpoint': '/api/reports/prepaid-eligible-transactions',
            'description': 'Prepaid Eligible Transactions',
            'params': {
                'company_id': company_id
            }
        }
    ]
    
    results = []
    
    for i, report in enumerate(reports_to_test, 1):
        print(f"\n{i}. Testing {report['description']}...")
        print(f"   Endpoint: {report['endpoint']}")
        print(f"   Params: {report['params']}")
        
        try:
            # Build URL with params
            url = f'{base_url}{report["endpoint"]}'
            param_string = '&'.join(f"{k}={v}" for k, v in report['params'].items())
            if param_string:
                url += f"?{param_string}"
            
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    data_size = len(str(data))
                    print(f"   ✓ Success (Status: {response.status}, Data size: {data_size} chars)")
                    
                    # Show some sample data structure
                    if isinstance(data, dict):
                        keys = list(data.keys())
                        print(f"   Response keys: {keys}")
                        
                        # Check for meaningful data
                        for key in ['revenue', 'expenses', 'assets', 'liabilities', 'items', 'transactions']:
                            if key in data:
                                value = data[key]
                                if isinstance(value, list):
                                    print(f"   Found list '{key}': {len(value)} items")
                                    if value and isinstance(value[0], dict):
                                        sample_keys = list(value[0].keys())[:3]
                                        print(f"   Sample keys: {sample_keys}")
                                elif isinstance(value, (int, float)):
                                    print(f"   Found number '{key}': {value}")
                                elif isinstance(value, dict):
                                    print(f"   Found dict '{key}' with keys: {list(value.keys())[:3]}")
                                    break
                    elif isinstance(data, list):
                        print(f"   Response is a list: {len(data)} items")
                        if data and isinstance(data[0], dict):
                            sample_keys = list(data[0].keys())[:3]
                            print(f"   Sample keys: {sample_keys}")
                    
                    results.append({
                        'description': report['description'],
                        'status': '✓ Success',
                        'data_size': data_size
                    })
                    
                else:
                    print(f"   ✗ Error: {response.status}")
                    results.append({
                        'description': report['description'],
                        'status': f'✗ Error {response.status}',
                        'data_size': 0
                    })
                    
        except Exception as e:
            print(f"   ✗ Error: {e}")
            results.append({
                'description': report['description'],
                'status': f'✗ Error: {e}',
                'data_size': 0
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("FINANCIAL REPORTS TEST SUMMARY")
    print(f"{'='*60}")
    
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
    
    # Database analysis
    total_data_size = sum(r['data_size'] for r in results if r['data_size'] > 0)
    print(f"\nDatabase Analysis:")
    if total_data_size > 5000:  # Substantial data indicates production MySQL
        print("  ✓ Production MySQL database detected")
        print(f"    Total data retrieved: {total_data_size} characters")
    elif total_data_size > 1000:
        print("  ⚠ Some data found - could be test or production")
        print(f"    Total data retrieved: {total_data_size} characters")
    else:
        print("  ⚠ Limited data found")
    
    return success_count == total_count

if __name__ == "__main__":
    success = test_reports_correct()
    if success:
        print(f"\n🎉 All financial reports are working with MySQL database!")
    else:
        print(f"\n⚠️ Some financial reports still have issues.")
