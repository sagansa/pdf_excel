#!/usr/bin/env python3
"""
Test API endpoints to verify they're working
"""

import urllib.request
import urllib.error
import json

def test_endpoint(endpoint, description):
    """Test a single API endpoint"""
    try:
        req = urllib.request.Request(f'http://127.0.0.1:5001{endpoint}')
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                print(f"✓ {description}: {response.status}")
                try:
                    data = json.loads(response.read().decode())
                    if isinstance(data, list):
                        print(f"  Returned {len(data)} items")
                    elif isinstance(data, dict) and 'data' in data:
                        print(f"  Returned {len(data['data'])} items")
                    elif isinstance(data, dict):
                        print(f"  Returned dict with keys: {list(data.keys())}")
                except:
                    print(f"  Response: {response.read()[:100].decode()}...")
            else:
                print(f"✗ {description}: {response.status}")
                print(f"  Error: {response.read()[:200].decode()}")
    except Exception as e:
        print(f"✗ {description}: Connection failed - {e}")

def main():
    """Test all important API endpoints"""
    print("Testing API endpoints...\n")
    
    endpoints = [
        ('/api/companies', 'Companies'),
        ('/api/transactions', 'Transactions'),
        ('/api/marks', 'Marks'),
        ('/api/coa', 'Chart of Accounts'),
        ('/api/filters/history', 'History Filters'),
        ('/api/filters/reports', 'Reports Filters'),
        ('/api/rental-locations', 'Rental Locations'),
        ('/api/stores', 'Rental Stores'),
        ('/api/rental-contracts', 'Rental Contracts'),
    ]
    
    for endpoint, description in endpoints:
        test_endpoint(endpoint, description)
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()
