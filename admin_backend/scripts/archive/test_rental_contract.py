#!/usr/bin/env python3
"""
Test rental contract creation with prepaid expense automation
"""

import urllib.request
import urllib.parse
import json
import time

def test_rental_contract_creation():
    """Test creating a rental contract with linked transactions"""
    base_url = 'http://127.0.0.1:5001'
    
    print("Testing Rental Contract Creation with Prepaid Expense Automation")
    print("=" * 60)
    
    # Get real stores and locations data first
    print("1. Getting available stores and locations...")
    
    stores = []
    locations = []
    
    try:
        # Get stores
        req = urllib.request.Request(f'{base_url}/api/stores')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                stores = data.get('stores', [])
                print(f"   Found {len(stores)} stores")
                for store in stores:
                    print(f"   - {store.get('store_name')} (ID: {store.get('id')})")
        
        # Get locations  
        req = urllib.request.Request(f'{base_url}/api/rental-locations')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                locations = data.get('locations', [])
                print(f"   Found {len(locations)} locations")
                for location in locations:
                    print(f"   - {location.get('location_name')} (ID: {location.get('id')})")
                    
    except Exception as e:
        print(f"   Error getting stores/locations: {e}")
        return False
    
    # Get companies
    print("\n2. Getting available companies...")
    try:
        req = urllib.request.Request(f'{base_url}/api/companies')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                companies = data.get('companies', [])
                print(f"   Found {len(companies)} companies")
                for company in companies:
                    print(f"   - {company.get('name')} (ID: {company.get('id')})")
            else:
                print(f"   Error getting companies: {response.status}")
                return False
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Check transactions
    print("\n3. Checking available transactions...")
    try:
        req = urllib.request.Request(f'{base_url}/api/transactions')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                transactions = data.get('transactions', [])
                print(f"   Found {len(transactions)} transactions")
                
                # Show rental-related transactions
                rental_txns = [t for t in transactions if 'sewa' in str(t.get('description', '')).lower()]
                print(f"   Rental-related transactions: {len(rental_txns)}")
                
                if rental_txns:
                    for t in rental_txns[:2]:  # Show first 2
                        print(f"   - {t.get('description')} (ID: {t.get('id')}, Amount: {t.get('amount')})")
            else:
                print(f"   Error getting transactions: {response.status}")
                return False
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Check existing rental contracts
    print("\n4. Checking existing rental contracts...")
    try:
        req = urllib.request.Request(f'{base_url}/api/rental-contracts')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                contracts = data.get('contracts', [])
                print(f"   Found {len(contracts)} existing contracts")
                
                for c in contracts:
                    print(f"   - {c.get('store_name')} ({c.get('location_name')}) - Total: {c.get('total_amount')}")
            else:
                print(f"   Error getting contracts: {response.status}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Create a new rental contract with real data
    print("\n5. Creating new rental contract...")
    
    if not stores or not locations or not companies:
        print("   ✗ Cannot create contract - missing required data")
        return False
        
    # Use first available data
    contract_data = {
        'company_id': companies[0]['id'],  # Use real company ID
        'store_id': stores[0]['id'],      # Use real store ID
        'location_id': locations[0]['id'],  # Use real location ID
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
        'total_amount': 60000000,
        'status': 'active',
        'notes': 'Test rental contract with prepaid automation',
        'linked_transaction_ids': [t['id'] for t in rental_txns[:2] if rental_txns]  # Link to real rental transactions
    }
    
    try:
        # Convert to JSON and encode
        json_data = json.dumps(contract_data).encode('utf-8')
        
        # Create request
        req = urllib.request.Request(
            f'{base_url}/api/rental-contracts',
            data=json_data,
            headers={
                'Content-Type': 'application/json',
                'Content-Length': len(json_data)
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            response_data = response.read().decode()
            
            if response.status == 200 or response.status == 201:
                result = json.loads(response_data)
                print(f"   ✓ Contract created successfully!")
                print(f"   Contract ID: {result.get('id')}")
                print(f"   Message: {result.get('message')}")
                print(f"   Linked transactions: {result.get('linked_transactions_count', 0)}")
                
                if result.get('prepaid_auto_created'):
                    print(f"   ✓ PREPAID EXPENSE AUTO-CREATED!")
                    print(f"   Prepaid ID: {result.get('prepaid_expense_id')}")
                else:
                    print(f"   ⚠ Prepaid expense was not auto-created")
                
                return True
            else:
                print(f"   ✗ Error creating contract: {response.status}")
                print(f"   Response: {response_data}")
                return False
                
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Check if prepaid expense was created
    print("\n4. Verifying prepaid expense creation...")
    try:
        req = urllib.request.Request(f'{base_url}/api/reports/prepaid-expenses?company_id=demo-company')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                prepaid_items = data.get('prepaid_expenses', [])
                print(f"   Found {len(prepaid_items)} prepaid expenses")
                
                for p in prepaid_items:
                    print(f"   - {p.get('description')} (Amount: {p.get('amount_net')})")
            else:
                print(f"   Error getting prepaid expenses: {response.status}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    success = test_rental_contract_creation()
    if success:
        print("\n✓ Test completed successfully!")
    else:
        print("\n✗ Test failed!")
