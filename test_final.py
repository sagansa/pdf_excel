#!/usr/bin/env python3
"""
Final test: Use existing rental transaction to create contract with prepaid automation
"""

import urllib.request
import json

def final_test():
    """Final test using existing data"""
    base_url = 'http://127.0.0.1:5001'
    
    print("Final Test: Rental Contract with Prepaid Expense Automation")
    print("=" * 60)
    
    # Get all data
    try:
        # Get companies
        req = urllib.request.Request(f'{base_url}/api/companies')
        with urllib.request.urlopen(req, timeout=5) as response:
            companies = json.loads(response.read().decode()).get('companies', [])
        
        # Get transactions
        req = urllib.request.Request(f'{base_url}/api/transactions')
        with urllib.request.urlopen(req, timeout=5) as response:
            transactions = json.loads(response.read().decode()).get('transactions', [])
        
        # Find rental-related transactions (those with 'sewa' in mark description)
        rental_txns = []
        for t in transactions:
            mark = t.get('mark', {})
            if any('sewa' in str(mark.get(k, '')).lower() for k in ['personal_use', 'internal_report', 'tax_report']):
                rental_txns.append(t)
        
        print(f"Found {len(rental_txns)} rental-related transactions")
        if rental_txns:
            for i, t in enumerate(rental_txns[:3]):
                mark = t.get('mark', {})
                print(f"  {i+1}. {t.get('description')} (Amount: {t.get('amount')})")
                print(f"     Mark: {mark.get('personal_use', '')} / {mark.get('internal_report', '')}")
        
        # Get stores
        req = urllib.request.Request(f'{base_url}/api/stores')
        with urllib.request.urlopen(req, timeout=5) as response:
            stores = json.loads(response.read().decode()).get('stores', [])
        
        # Get locations
        req = urllib.request.Request(f'{base_url}/api/rental-locations')
        with urllib.request.urlopen(req, timeout=5) as response:
            locations = json.loads(response.read().decode()).get('locations', [])
        
        print(f"\\nAvailable: {len(companies)} companies, {len(stores)} stores, {len(locations)} locations")
        
        if not rental_txns or not stores or not locations or not companies:
            print("\\n⚠ Cannot create contract - missing required data")
            return False
        
        # Create contract using first available data and rental transactions
        print("\\nCreating rental contract...")
        
        contract_data = {
            'company_id': companies[0]['id'],
            'store_id': stores[0]['id'],
            'location_id': locations[0]['id'],
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'total_amount': sum(float(t.get('amount', 0)) for t in rental_txns[:2]),
            'status': 'active',
            'notes': 'Test rental contract with existing rental transactions',
            'linked_transaction_ids': [t['id'] for t in rental_txns[:2]]
        }
        
        print(f"Contract data:")
        print(f"  Company: {companies[0]['name']}")
        print(f"  Store: {stores[0]['store_name']}")
        print(f"  Location: {locations[0]['location_name']}")
        print(f"  Amount: {contract_data['total_amount']}")
        print(f"  Linked transactions: {len(contract_data['linked_transaction_ids'])}")
        
        # Send request
        json_data = json.dumps(contract_data).encode('utf-8')
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
                print(f"\\n✓ Contract created successfully!")
                print(f"  Contract ID: {result.get('id')}")
                print(f"  Message: {result.get('message')}")
                print(f"  Linked transactions: {result.get('linked_transactions_count', 0)}")
                
                if result.get('prepaid_auto_created'):
                    print(f"  ✓ PREPAID EXPENSE AUTO-CREATED!")
                    print(f"  Prepaid ID: {result.get('prepaid_expense_id')}")
                    
                    # Check prepaid expense details
                    try:
                        req = urllib.request.Request(f'{base_url}/api/reports/prepaid-expenses?company_id={companies[0]["id"]}')
                        with urllib.request.urlopen(req, timeout=5) as response:
                            if response.status == 200:
                                data = json.loads(response.read().decode())
                                prepaid_items = data.get('prepaid_expenses', [])
                                for p in prepaid_items:
                                    if result.get('prepaid_expense_id') == p.get('id'):
                                        print(f"  ✓ Prepaid Details:")
                                        print(f"    Description: {p.get('description')}")
                                        print(f"    Amount Net: {p.get('amount_net')}")
                                        print(f"    Amount Bruto: {p.get('amount_bruto')}")
                                        print(f"    Monthly Amortization: {p.get('monthly_amortization')}")
                                        print(f"    Duration: {p.get('duration_months')} months")
                                        break
                    except Exception as e:
                        print(f"  Error getting prepaid details: {e}")
                        
                    return True
                else:
                    print(f"  ⚠ Prepaid expense was not auto-created")
                    print(f"  Response: {result}")
                    return False
            else:
                print(f"\\n✗ Error creating contract: {response.status}")
                print(f"Response: {response_data}")
                return False
                
    except Exception as e:
        print(f"\\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = final_test()
    if success:
        print("\\n🎉 SUCCESS: Rental contract creation with prepaid expense automation is working!")
    else:
        print("\\n❌ FAILED: There are still issues to resolve.")
