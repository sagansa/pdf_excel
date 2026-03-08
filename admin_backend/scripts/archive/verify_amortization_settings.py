#!/usr/bin/env python3
import urllib.request
import json
import uuid

def verify_settings():
    base_url = 'http://127.0.0.1:5001'
    
    # 1. Get companies
    print("Fetching companies...")
    req = urllib.request.Request(f'{base_url}/api/companies')
    with urllib.request.urlopen(req) as res:
        companies = json.loads(res.read())['companies']
        if not companies:
            print("No companies found!")
            return
        company_id = companies[0]['id']
        print(f"Using company: {companies[0]['name']} ({company_id})")

    # 2. Test POST settings
    print("\nTesting POST /api/amortization-settings...")
    settings_data = {
        'company_id': company_id,
        'use_mark_based_amortization': True,
        'amortization_asset_marks': ['test-mark-id-123'],
        'default_asset_useful_life': 8,
        'default_amortization_rate': 12.5
    }
    
    req = urllib.request.Request(
        f'{base_url}/api/amortization-settings',
        data=json.dumps(settings_data).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as res:
        print(f"POST status: {res.status}")

    # 3. Test GET settings
    print("\nTesting GET /api/amortization-settings...")
    req = urllib.request.Request(f'{base_url}/api/amortization-settings?company_id={company_id}')
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read())
        print(f"GET response: {json.dumps(data, indent=2)}")
        
        # Verify values
        s = data['settings']
        assert s['use_mark_based_amortization'] == True
        assert 'test-mark-id-123' in s['amortization_asset_marks']
        assert s['default_asset_useful_life'] == 8
        assert s['default_amortization_rate'] == 12.5
        print("✓ Settings verification PASSED")

    # 4. Test Amortization Items with mark-based filtering
    print("\nTesting GET /api/amortization-items with mark filtering...")
    url = f'{base_url}/api/amortization-items?company_id={company_id}&year=2025'
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read())
        print(f"Found {len(data.get('items', []))} items")
        # Since 'test-mark-id-123' doesn't exist in transactions, this just verifies the API works.
        print("✓ Items API verification PASSED")

if __name__ == "__main__":
    try:
        verify_settings()
        print("\n🎉 All verifications successful!")
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
