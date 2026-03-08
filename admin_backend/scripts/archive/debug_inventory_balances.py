#!/usr/bin/env python3
"""
Debug inventory balances POST endpoint
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_inventory_balances_post():
    print("=== DEBUG INVENTORY BALANCES POST ===")
    
    try:
        import requests
        import json
        
        # Test the POST endpoint
        url = "http://127.0.0.1:5001/api/inventory-balances"
        
        # Sample payload (biasanya dari frontend)
        payload = {
            "year": 2023,
            "company_id": "8ab69d4a-e591-4f05-909e-25ff12352efb",
            "beginning_inventory_amount": 1000000.0,
            "beginning_inventory_qty": 100.0,
            "ending_inventory_amount": 1500000.0,
            "ending_inventory_qty": 150.0,
            "base_value": 1000000.0
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        print(f"Sending POST request to: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"Response Body: {json.dumps(response_json, indent=2)}")
        except:
            print(f"Response Body (raw): {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def test_inventory_balances_get():
    print("\\n=== DEBUG INVENTORY BALANCES GET ===")
    
    try:
        import requests
        
        # Test the GET endpoint
        url = "http://127.0.0.1:5001/api/inventory-balances?year=2023&company_id=8ab69d4a-e591-4f05-909e-25ff12352efb"
        
        print(f"Sending GET request to: {url}")
        
        response = requests.get(url, timeout=30)
        
        print(f"\\nResponse Status: {response.status_code}")
        
        try:
            response_json = response.json()
            print(f"Response Body: {response_json}")
        except:
            print(f"Response Body (raw): {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_inventory_balances_post()
    test_inventory_balances_get()
