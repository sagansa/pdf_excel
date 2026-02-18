#!/usr/bin/env python3
"""
Test creating rental transaction first, then contract with prepaid automation
"""

import urllib.request
import urllib.parse
import json

def test_with_rental_transaction():
    """Test by creating a rental transaction first, then contract"""
    base_url = 'http://127.0.0.1:5001'
    
    print("Testing Rental Contract Creation with Prepaid Expense Automation")
    print("=" * 60)
    
    # Step 1: Get existing transactions and marks
    print("1. Getting existing marks...")
    try:
        req = urllib.request.Request(f'{base_url}/api/marks')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                marks = data.get('marks', [])
                print(f"   Found {len(marks)} marks")
                
                # Find or create a rental mark
                rental_mark = None
                for mark in marks:
                    if 'sewa' in str(mark.get('personal_use', '')).lower():
                        rental_mark = mark
                        print(f"   Found rental mark: {rental_mark}")
                        break
                
                if not rental_mark:
                    print("   No rental mark found, creating one...")
                    # Create rental mark
                    mark_data = {
                        'personal_use': 'sewa',
                        'internal_report': 'sewa', 
                        'tax_report': 'sewa'
                    }
                    
                    json_data = json.dumps(mark_data).encode('utf-8')
                    req = urllib.request.Request(
                        f'{base_url}/api/marks',
                        data=json_data,
                        headers={'Content-Type': 'application/json'},
                        method='POST'
                    )
                    
                    with urllib.request.urlopen(req, timeout=5) as response:
                        if response.status in [200, 201]:
                            rental_mark = json.loads(response.read().decode())
                            print(f"   ✓ Created rental mark: {rental_mark}")
            
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Step 2: Create a rental transaction manually
    print("\n2. Creating a rental transaction...")
    try:
        # Get first company and mark
        req = urllib.request.Request(f'{base_url}/api/companies')
        with urllib.request.urlopen(req, timeout=5) as response:
            companies = json.loads(response.read().decode()).get('companies', [])
            
        req = urllib.request.Request(f'{base_url}/api/marks')
        with urllib.request.urlopen(req, timeout=5) as response:
            marks = json.loads(response.read().decode()).get('marks', [])
        
        if not companies or not marks:
            print("   Missing companies or marks")
            return False
            
        txn_data = {
            'txn_date': '2024-01-15',
            'description': 'Pembayaran Sewa Toko Januari 2024',
            'amount': 10000000,
            'db_cr': 'CR',
            'bank_code': 'MANUAL',
            'source_file': 'manual_test',
            'file_hash': 'test_hash',
            'mark_id': rental_mark['id'] if rental_mark else marks[0]['id'],
            'company_id': companies[0]['id']
        }
        
        json_data = json.dumps(txn_data).encode('utf-8')
        req = urllib.request.Request(
            f'{base_url}/api/transactions',
            data=json_data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status in [200, 201]:
                result = json.loads(response.read().decode())
                print(f"   ✓ Created rental transaction: {result}")
                rental_txn_id = result.get('id')
            else:
                print(f"   ✗ Error creating transaction: {response.status}")
                return False
                
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Step 3: Get stores and locations
    print("\n3. Getting stores and locations...")
    try:
        req = urllib.request.Request(f'{base_url}/api/stores')
        with urllib.request.urlopen(req, timeout=5) as response:
            stores = json.loads(response.read().decode()).get('stores', [])
        
        req = urllib.request.Request(f'{base_url}/api/rental-locations')
        with urllib.request.urlopen(req, timeout=5) as response:
            locations = json.loads(response.read().decode()).get('locations', [])
        
        print(f"   Found {len(stores)} stores and {len(locations)} locations")
        
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Step 4: Create rental contract with the new transaction
    print("\n4. Creating rental contract with the rental transaction...")
    
    contract_data = {
        'company_id': companies[0]['id'],
        'store_id': stores[0]['id'],
        'location_id': locations[0]['id'],
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
        'total_amount': 120000000,  # 12 months * 10,000,000
        'status': 'active',
        'notes': 'Test rental contract with actual rental transaction',
        'linked_transaction_ids': [rental_txn_id]  # Link to our rental transaction
    }
    
    try:
        json_data = json.dumps(contract_data).encode('utf-8')
        req = urllib.request.Request(
            f'{base_url}/api/rental-contracts',
            data=json_data,
            headers={'Content-Type': 'application/json'},
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
    
    # Step 5: Verify prepaid expense
    print("\n5. Verifying prepaid expense...")
    try:
        req = urllib.request.Request(f'{base_url}/api/reports/prepaid-expenses?company_id={companies[0]["id"]}')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                prepaid_items = data.get('prepaid_expenses', [])
                print(f"   Found {len(prepaid_items)} prepaid expenses")
                
                for p in prepaid_items:
                    if contract_data['store_id'] in str(p) or contract_data['location_id'] in str(p):
                        print(f"   ✓ Found prepaid expense: {p.get('description')} (Amount: {p.get('amount_net')})")
                        break
            else:
                print(f"   Error getting prepaid expenses: {response.status}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    success = test_with_rental_transaction()
    if success:
        print("\n✓ Test completed successfully!")
    else:
        print("\n✗ Test failed!")
