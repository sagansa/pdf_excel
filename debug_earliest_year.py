"""
Debug logika earliest_year di implementasi Laba Ditahan
"""
from sqlalchemy import create_engine, text
from datetime import datetime

engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")

with engine.connect() as conn:
    company_id = "40e70c5f-43ef-49aa-b73e-7f83d326b301"
    as_of_date = "2025-12-31"
    as_of_date_obj = datetime.strptime(as_of_date, '%Y-%m-%d').date()
    
    report_year = as_of_date_obj.year  # 2025
    company_start_year = report_year - 1  # Default: 2024
    
    print("=" * 80)
    print("DEBUG LOGIKA EARLIEST_YEAR")
    print("=" * 80)
    
    print(f"\nReport Year: {report_year}")
    print(f"Default company_start_year: {company_start_year}")
    
    # Cek initial capital settings
    try:
        initial_capital_query = text("""
            SELECT MIN(start_year) as min_start_year
            FROM initial_capital_settings
            WHERE company_id = :company_id
        """)
        start_year_result = conn.execute(initial_capital_query, {'company_id': company_id}).fetchone()
        
        if start_year_result and start_year_result.min_start_year:
            company_start_year = int(start_year_result.min_start_year)
            print(f"Initial Capital found: company_start_year = {company_start_year}")
        else:
            print(f"No Initial Capital settings found")
    except Exception as e:
        print(f"Error querying initial_capital_settings: {e}")
    
    # Calculate earliest_year
    earliest_year = min(company_start_year, report_year - 1)
    
    print(f"\nCalculation:")
    print(f"  company_start_year = {company_start_year}")
    print(f"  report_year - 1 = {report_year - 1}")
    print(f"  earliest_year = min({company_start_year}, {report_year - 1}) = {earliest_year}")
    
    print(f"\nLoop range: range({earliest_year}, {report_year})")
    print(f"Years to iterate: {list(range(earliest_year, report_year))}")
    
    # Test dengan logika yang benar
    print("\n" + "=" * 80)
    print("TEST DENGAN LOGIKA YANG DIPERBAIKI")
    print("=" * 80)
    
    # Jika tidak ada initial capital, kita harus mulai dari tahun pertama ada transaksi
    print("\nMencari tahun pertama ada transaksi...")
    first_txn = conn.execute(text("""
        SELECT MIN(YEAR(txn_date)) as first_year
        FROM transactions
        WHERE company_id = :company_id
    """), {'company_id': company_id}).fetchone()
    
    if first_txn and first_txn.first_year:
        actual_start_year = first_txn.first_year
        print(f"Tahun transaksi pertama: {actual_start_year}")
        
        # Gunakan tahun pertama transaksi sebagai start_year
        corrected_earliest_year = min(actual_start_year, report_year - 1)
        print(f"Corrected earliest_year: {corrected_earliest_year}")
        print(f"Loop range: range({corrected_earliest_year}, {report_year})")
        print(f"Years to iterate: {list(range(corrected_earliest_year, report_year))}")
    else:
        print("Tidak ada transaksi ditemukan")
