import requests

url = "http://localhost:5000/api/inventory-balances"
payload = {
    "company_id": "test_company",
    "year": 2024,
    "beginning_inventory_amount": 1000,
    "beginning_inventory_qty": 10,
    "ending_inventory_amount": 2000,
    "ending_inventory_qty": 20
}
try:
    response = requests.post(url, json=payload)
    print("Status Code:", response.status_code)
    print("Response Context:", response.text)
except Exception as e:
    print("Error:", str(e))
