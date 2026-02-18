from sqlalchemy import create_engine, text
import json

DB_USER = 'root'
DB_PASS = 'root'
DB_HOST = '127.0.0.1'
DB_PORT = '3306'
DB_NAME = 'bank_converter'

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def main():
    engine = create_engine(DB_URL)
    try:
        with engine.connect() as conn:
            print("--- Mark Asset Mapping ---")
            marks = conn.execute(text("""
                SELECT 
                    m.id, m.personal_use, 
                    mam.asset_type, mam.useful_life_years, mam.amortization_rate, 
                    mam.asset_group_id, mam.is_deductible_50_percent,
                    ag.group_name, ag.group_number, ag.tarif_rate
                FROM marks m
                LEFT JOIN mark_asset_mapping mam ON m.id = mam.mark_id
                LEFT JOIN amortization_asset_groups ag ON mam.asset_group_id = ag.id
                WHERE m.is_asset = TRUE
                ORDER BY m.personal_use
            """)).fetchall()
            
            for m in marks:
                print(f"Mark: {m[1]}")
                print(f"  Asset Type: {m[2]}, Useful Life: {m[3]} years, Rate: {m[4]}")
                print(f"  Asset Group ID: {m[5]}, Is 50% Deductible: {m[6]}")
                if m[7]:
                    print(f"  Group: {m[7]} (Group {m[8]}, Rate: {m[9]}%)")
                print()
            
            print("\n--- Mark-Based Assets for 2025 ---")
            # Simulate get_mark_based_assets function
            company_id = '019aba4b-efca-70ee-a4ab-702dc8c246a8'  # Headquarters
            year = 2025
            
            query = text("""
                SELECT 
                    t.id, t.description, t.amount,
                    COALESCE(t.use_half_rate, mam.is_deductible_50_percent, FALSE) as use_half_rate,
                    COALESCE(ag_direct.group_number, ag_mapping.group_number, 2) as group_number,
                    COALESCE(ag_direct.group_name, ag_mapping.group_name, 'Kelompok 2') as group_name,
                    COALESCE(ag_direct.asset_type, ag_mapping.asset_type, mam.asset_type, 'Tangible') as asset_type,
                    COALESCE(ag_direct.useful_life_years, ag_mapping.useful_life_years, mam.useful_life_years, 5) as useful_life_years,
                    COALESCE(ag_direct.tarif_rate, ag_mapping.tarif_rate, 20.00) as tarif_rate,
                    COALESCE(ag_direct.tarif_half_rate, ag_mapping.tarif_half_rate, 10.00) as tarif_half_rate,
                    m.personal_use as mark_name,
                    t.amortization_asset_group_id,
                    mam.asset_group_id as mark_asset_group_id
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                LEFT JOIN mark_asset_mapping mam ON m.id = mam.mark_id AND mam.is_active = TRUE
                LEFT JOIN amortization_asset_groups ag_direct ON t.amortization_asset_group_id = ag_direct.id
                LEFT JOIN amortization_asset_groups ag_mapping ON (
                    mam.asset_group_id = ag_mapping.id
                    AND ag_mapping.is_active = TRUE
                )
                WHERE t.company_id = :company
                AND YEAR(t.txn_date) <= :year
                AND m.is_asset = TRUE
                AND (t.is_amortizable IS TRUE OR t.is_amortizable IS NULL)
                ORDER BY t.txn_date
            """)
            
            assets = conn.execute(query, {'company': company_id, 'year': year}).fetchall()
            
            print(f"Found {len(assets)} mark-based assets:\n")
            for a in assets:
                deductible = "50%" if a[3] else "100%"
                print(f"Transaction: {a[1]}")
                print(f"  Amount: {a[2]}, Deductible: {deductible}")
                print(f"  Group: {a[5]} (Group {a[4]})")
                print(f"  Asset Type: {a[6]}, Useful Life: {a[7]} years")
                print(f"  Tarif: {a[8]}% (full), {a[9]}% (half)")
                print(f"  Mark: {a[10]}")
                print(f"  Transaction Asset Group ID: {a[11]}")
                print(f"  Mark Asset Group ID: {a[12]}")
                print()
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
