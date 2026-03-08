#!/usr/bin/env python3
"""
Debug rental locations API endpoint manually
"""

import os
from sqlalchemy import create_engine, text

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Force SQLite
os.environ['USE_SQLITE'] = 'true'

# Import server functions
import sys
sys.path.append(os.path.dirname(__file__))
from server import get_db_engine

def debug_rental_locations():
    """Debug rental locations endpoint"""
    engine, error_msg = get_db_engine()
    if engine is None:
        print(f"Database engine error: {error_msg}")
        return
    
    try:
        company_id = 'demo-company'
        print(f"Testing with company_id: {company_id}")
        
        with engine.connect() as conn:
            query = text("""
                SELECT id, company_id, location_name, address, city, province, 
                       postal_code, latitude, longitude, area_sqm, notes,
                       created_at, updated_at
                FROM rental_locations
                WHERE (:company_id IS NULL OR company_id = :company_id)
                ORDER BY location_name
            """)
            print("Executing query...")
            result = conn.execute(query, {'company_id': company_id})
            print("Query executed successfully")
            
            locations = []
            for row in result:
                locations.append({
                    'id': row.id,
                    'company_id': row.company_id,
                    'location_name': row.location_name,
                    'address': row.address
                })
            
            print(f"Found {len(locations)} locations")
            return {'locations': locations}
            
    except Exception as e:
        import traceback
        print(f"Exception occurred: {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = debug_rental_locations()
    if result:
        print("Success!")
    else:
        print("Failed!")
