#!/usr/bin/env python3
"""
Test location loading in rental contracts
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

import asyncio
import aiohttp

async def test_locations():
    """Test locations API"""
    base_url = "http://localhost:5001"
    company_id = "8ab69d4a-e591-4f05-909e-25ff12352efb"
    
    async with aiohttp.ClientSession() as session:
        # Test locations API
        print("Testing locations API...")
        async with session.get(f"{base_url}/api/rental-locations", 
                                   params={"company_id": company_id}) as resp:
            if resp.status == 200:
                data = await resp.json()
                locations = data.get('locations', [])
                print(f"✓ Found {len(locations)} locations")
                for loc in locations:
                    print(f"  - {loc.get('location_name')} (ID: {loc.get('id')})")
            else:
                print(f"✗ Error: {resp.status}")
                text = await resp.text()
                print(f"Response: {text}")
        
        # Test stores API
        print("\nTesting stores API...")
        async with session.get(f"{base_url}/api/stores") as resp:
            if resp.status == 200:
                data = await resp.json()
                stores = data.get('stores', [])
                print(f"✓ Found {len(stores)} stores")
                for store in stores:
                    print(f"  - {store.get('store_name')} (ID: {store.get('id')})")
            else:
                print(f"✗ Error: {resp.status}")
                text = await resp.text()
                print(f"Response: {text}")

if __name__ == "__main__":
    asyncio.run(test_locations())
