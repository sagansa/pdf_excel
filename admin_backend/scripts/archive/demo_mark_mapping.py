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
    
    with engine.begin() as conn:
        print("--- Step 1: View Available Asset Groups ---")
        groups = conn.execute(text("""
            SELECT id, group_number, group_name, asset_type, useful_life_years, tarif_rate, tarif_half_rate
            FROM amortization_asset_groups
            WHERE is_active = TRUE
            ORDER BY asset_type, group_number
        """)).fetchall()
        
        for g in groups:
            print(f"ID: {g[0]}, Group {g[1]} - {g[2]} ({g[3]})")
            print(f"  Useful Life: {g[4]} years, Rate: {g[5]}% (full), {g[6]}% (half)")
            print()
        
        print("\n--- Step 2: View Marks with is_asset = TRUE ---")
        marks = conn.execute(text("""
            SELECT id, personal_use
            FROM marks
            WHERE is_asset = TRUE
            ORDER BY personal_use
        """)).fetchall()
        
        for m in marks:
            print(f"ID: {m[0]}, Name: {m[1]}")
        
        print("\n--- Step 3: Configure Mark to Asset Group Mapping ---")
        
        # Example: Configure "Laptop" mark to Kelompok 2 (Tangible, 5 years)
        laptop_mark_id = None
        laptop_group_id = None
        
        for m in marks:
            if 'Laptop' in m[1]:
                laptop_mark_id = m[0]
        
        for g in groups:
            if g[1] == 2 and g[3] == 'Tangible':  # Group 2, Tangible
                laptop_group_id = g[0]
        
        if laptop_mark_id and laptop_group_id:
            print(f"\nConfiguring '{m[1]}' (ID: {laptop_mark_id}) to Group {g[1]} (ID: {laptop_group_id})...")
            
            # Check if mapping already exists
            existing = conn.execute(
                text("SELECT id FROM mark_asset_mapping WHERE mark_id = :mark_id"),
                {'mark_id': laptop_mark_id}
            ).fetchone()
            
            if existing:
                conn.execute(
                    text("""
                        UPDATE mark_asset_mapping
                        SET asset_type = 'Tangible',
                            useful_life_years = 5,
                            amortization_rate = 20.00,
                            asset_group_id = :asset_group_id,
                            is_deductible_50_percent = FALSE,
                            updated_at = NOW()
                        WHERE mark_id = :mark_id
                    """),
                    {'mark_id': laptop_mark_id, 'asset_group_id': laptop_group_id}
                )
                print(f"  Updated existing mapping")
            else:
                import uuid
                mapping_id = str(uuid.uuid4())
                conn.execute(
                    text("""
                        INSERT INTO mark_asset_mapping
                        (id, mark_id, asset_type, useful_life_years, amortization_rate, asset_group_id, is_deductible_50_percent)
                        VALUES (:id, :mark_id, :asset_type, :useful_life, :rate, :asset_group_id, :is_deductible_50_percent)
                    """),
                    {
                        'id': mapping_id,
                        'mark_id': laptop_mark_id,
                        'asset_type': 'Tangible',
                        'useful_life': 5,
                        'rate': 20.00,
                        'asset_group_id': laptop_group_id,
                        'is_deductible_50_percent': False
                    }
                )
                print(f"  Created new mapping")
            
            print(f"  Asset Type: Tangible")
            print(f"  Useful Life: 5 years")
            print(f"  Amortization Rate: 20.00%")
            print(f"  Asset Group ID: {laptop_group_id}")
            print(f"  Is 50% Deductible: False (100% Deductible)")
        
        print("\n--- Step 4: View Updated Mapping ---")
        marks_with_mapping = conn.execute(text("""
            SELECT 
                m.personal_use,
                mam.asset_type, mam.useful_life_years, mam.amortization_rate,
                mam.asset_group_id, mam.is_deductible_50_percent,
                ag.group_name, ag.group_number, ag.tarif_rate, ag.tarif_half_rate
            FROM marks m
            LEFT JOIN mark_asset_mapping mam ON m.id = mam.mark_id
            LEFT JOIN amortization_asset_groups ag ON mam.asset_group_id = ag.id
            WHERE m.is_asset = TRUE
            ORDER BY m.personal_use
        """)).fetchall()
        
        for m in marks_with_mapping:
            print(f"\nMark: {m[0]}")
            if m[1]:
                deductible = "50%" if m[5] else "100%"
                print(f"  Asset Type: {m[1]}, Useful Life: {m[2]} years")
                print(f"  Amortization Rate: {m[3]}%, Deductible: {deductible}")
                print(f"  Asset Group: {m[6]} (Group {m[7]}, Rate: {m[8]}% / {m[9]}%)")
            else:
                print(f"  No mapping configured (will use defaults: Tangible, 5 years, 20%, 100% deductible)")
        
        print("\n--- Step 5: View Transactions with Updated Mapping ---")
        company_id = '019aba4b-efca-70ee-a4ab-702dc8c246a8'
        year = 2025
        
        transactions = conn.execute(text("""
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
        """), {'company': company_id, 'year': year}).fetchall()
        
        print(f"\nFound {len(transactions)} mark-based asset transactions:\n")
        for t in transactions:
            deductible = "50%" if t[3] else "100%"
            print(f"Transaction: {t[1]} (Amount: {t[2]}, Deductible: {deductible})")
            print(f"  Group: {t[5]} (Group {t[4]})")
            print(f"  Asset Type: {t[6]}, Useful Life: {t[7]} years")
            print(f"  Tarif: {t[8]}% (full), {t[9]}% (half)")
            print(f"  Mark: {t[10]}")
            if t[11]:
                print(f"  Transaction Asset Group ID: {t[11]} (override from transaction level)")
            elif t[12]:
                print(f"  Mark Asset Group ID: {t[12]} (from mark mapping)")
            else:
                print(f"  No group ID configured (using defaults)")
            print()

if __name__ == "__main__":
    main()
