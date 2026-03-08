"""
Test konsistensi Balance Sheet dengan adjustment di 2023
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_balance_sheet_data, fetch_income_statement_data

engine = create_engine('mysql+pymysql://root:root@127.0.0.1:3306/bank_converter')

with engine.connect() as conn:
    company_id = '8ab69d4a-e591-4f05-909e-25ff12352efb'
    
    print("=" * 80)
    print("TEST KONSISTENSI BALANCE SHEET")
    print("=" * 80)
    
    # 1. Ambil data 2023
    print("\n=== 1. BALANCE SHEET 2023 (ORIGINAL) ===")
    bs_2023 = fetch_balance_sheet_data(conn, '2023-12-31', company_id, report_type='real')
    
    assets_2023 = bs_2023.get('assets', {})
    liabilities_2023 = bs_2023.get('liabilities', {})
    equity_2023 = bs_2023.get('equity', {})
    
    total_assets_2023 = assets_2023.get('total', 0)
    total_liabilities_2023 = liabilities_2023.get('total', 0)
    total_equity_2023 = equity_2023.get('total', 0)
    
    diff_2023 = total_assets_2023 - (total_liabilities_2023 + total_equity_2023)
    
    print(f"  Assets:     Rp {total_assets_2023:>15,.0f}")
    print(f"  Liabilities:Rp {total_liabilities_2023:>15,.0f}")
    print(f"  Equity:     Rp {total_equity_2023:>15,.0f}")
    print(f"  Diff:       Rp {diff_2023:>15,.0f}")
    
    # 2. Hitung adjustment yang dibutuhkan
    print("\n=== 2. HITUNG ADJUSTMENT 2023 ===")
    print(f"  Adjustment yang dibutuhkan: Rp {-diff_2023:>15,.0f}")
    print(f"  (ditambahkan ke Equity sebagai 'Modal Disesuaikan')")
    
    # 3. Hitung Equity 2024 dengan adjustment
    print("\n=== 3. PROYEKSI BALANCE SHEET 2024 ===")
    income_2024 = fetch_income_statement_data(conn, '2024-01-01', '2024-12-31', company_id, report_type='real', comparative=False)
    net_income_2024 = income_2024.get('net_income', 0.0)
    
    bs_2024 = fetch_balance_sheet_data(conn, '2024-12-31', company_id, report_type='real')
    assets_2024 = bs_2024.get('assets', {})
    liabilities_2024 = bs_2024.get('liabilities', {})
    equity_2024 = bs_2024.get('equity', {})
    
    total_assets_2024 = assets_2024.get('total', 0)
    total_liabilities_2024 = liabilities_2024.get('total', 0)
    total_equity_2024 = equity_2024.get('total', 0)
    
    # Equity 2024 dengan adjustment
    adjusted_equity_2024 = total_equity_2024 - diff_2023  # Kurangi diff 2023 (karena diff negatif = tambah equity)
    projected_diff_2024 = total_assets_2024 - (total_liabilities_2024 + adjusted_equity_2024)
    
    print(f"  Assets:              Rp {total_assets_2024:>15,.0f}")
    print(f"  Liabilities:         Rp {total_liabilities_2024:>15,.0f}")
    print(f"  Equity (original):   Rp {total_equity_2024:>15,.0f}")
    print(f"  Adjustment 2023:     Rp {-diff_2023:>15,.0f}")
    print(f"  Equity (adjusted):   Rp {adjusted_equity_2024:>15,.0f}")
    print(f"  Projected Diff 2024: Rp {projected_diff_2024:>15,.0f}")
    print(f"  Balance:             {'✓ YES' if abs(projected_diff_2024) < 1.0 else '✗ NO'}")
    
    # 4. Hitung Equity 2025 dengan adjustment
    print("\n=== 4. PROYEKSI BALANCE SHEET 2025 ===")
    income_2025 = fetch_income_statement_data(conn, '2025-01-01', '2025-12-31', company_id, report_type='real', comparative=False)
    net_income_2025 = income_2025.get('net_income', 0.0)
    
    bs_2025 = fetch_balance_sheet_data(conn, '2025-12-31', company_id, report_type='real')
    assets_2025 = bs_2025.get('assets', {})
    liabilities_2025 = bs_2025.get('liabilities', {})
    equity_2025 = bs_2025.get('equity', {})
    
    total_assets_2025 = assets_2025.get('total', 0)
    total_liabilities_2025 = liabilities_2025.get('total', 0)
    total_equity_2025 = equity_2025.get('total', 0)
    
    # Equity 2025 dengan adjustment
    adjusted_equity_2025 = total_equity_2025 - diff_2023
    projected_diff_2025 = total_assets_2025 - (total_liabilities_2025 + adjusted_equity_2025)
    
    print(f"  Assets:              Rp {total_assets_2025:>15,.0f}")
    print(f"  Liabilities:         Rp {total_liabilities_2025:>15,.0f}")
    print(f"  Equity (original):   Rp {total_equity_2025:>15,.0f}")
    print(f"  Adjustment 2023:     Rp {-diff_2023:>15,.0f}")
    print(f"  Equity (adjusted):   Rp {adjusted_equity_2025:>15,.0f}")
    print(f"  Projected Diff 2025: Rp {projected_diff_2025:>15,.0f}")
    print(f"  Balance:             {'✓ YES' if abs(projected_diff_2025) < 1.0 else '✗ NO'}")
    
    # 5. Kesimpulan
    print("\n=== 5. KESIMPULAN ===")
    if abs(projected_diff_2024) < 1.0 and abs(projected_diff_2025) < 1.0:
        print("  ✓ KONSISTEN! Setelah adjustment 2023, 2024 dan 2025 otomatis balance.")
        print(f"  Adjustment yang dibutuhkan di 2023: Rp {-diff_2023:,.0f}")
    else:
        print("  ✗ TIDAK KONSISTEN! Ada masalah dalam perhitungan.")
        print(f"  2024 Diff: Rp {projected_diff_2024:,.0f}")
        print(f"  2025 Diff: Rp {projected_diff_2025:,.0f}")
