import requests
import json

BASE_URL = "http://localhost:5000/api" # Assuming server is on 5000

def test_settings_endpoints():
    company_id = "8ab69d4a-e591-4f05-909e-25ff12352efb" # PT Asa Pangan Bangsa
    
    # 1. Test POST with new route
    print(f"Testing POST to /amortization/settings...")
    payload = {
        "company_id": company_id,
        "setting_name": "amortization_coa_mapping",
        "setting_value": json.dumps({"5314": {"name": "Amortisasi-Test", "type": "Tangible"}}),
        "setting_type": "json",
        "description": "Test mapping"
    }
    
    try:
        r = requests.post(f"{BASE_URL}/amortization/settings", json=payload)
        print(f"POST Status: {r.status_code}")
        print(f"POST Response: {r.json()}")
        
        # 2. Test GET with new route
        print(f"\nTesting GET from /amortization/settings...")
        r = requests.get(f"{BASE_URL}/amortization/settings", params={"company_id": company_id})
        print(f"GET Status: {r.status_code}")
        settings = r.json().get('settings', {})
        mapping = settings.get('amortization_coa_mapping')
        print(f"Mapping found: {mapping}")
        
        if mapping and mapping.get('type') == 'json':
            print("\nSUCCESS: setting_type preserved!")
        else:
            print("\nFAILURE: setting_type missing or incorrect.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_settings_endpoints()
