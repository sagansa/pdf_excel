"""
Script untuk analisa perlakuan Initial Capital vs Laba Ditahan
"""
from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_income_statement_data

# Koneksi ke MySQL
engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")

with engine.connect() as conn:
    company_id = "8ab69d4a-e591-4f05-909e-25ff12352efb"
    
    print("=" * 80)
    print("ANALISA INITIAL CAPITAL VS LABA DITAHAN")
    print("=" * 80)
    
    # 1. Cek Initial Capital
    print("\n=== 1. INITIAL CAPITAL ===")
    initial_capital = conn.execute(text("""
        SELECT amount, start_year, description
        FROM initial_capital_settings
        WHERE company_id = :company_id
    """), {'company_id': company_id}).fetchone()
    
    if initial_capital:
        print(f"  Amount: Rp {initial_capital.amount:,.0f}")
        print(f"  Start Year: {initial_capital.start_year}")
        print(f"  Description: {initial_capital.description}")
    else:
        print("  Tidak ada Initial Capital")
    
    # 2. Cek Net Income per tahun
    print("\n=== 2. NET INCOME PER TAHUN ===")
    yearly_net_incomes = {}
    for year in [2022, 2023, 2024, 2025]:
        income_data = fetch_income_statement_data(
            conn, f"{year}-01-01", f"{year}-12-31", company_id,
            report_type='real', comparative=False
        )
        net_income = income_data.get('net_income', 0.0)
        yearly_net_incomes[year] = net_income
        print(f"  {year}: Rp {net_income:>15,.0f}")
    
    # 3. Hitung Retained Earnings per tahun
    print("\n=== 3. RETAINED EARNINGS KUMULATIF ===")
    cumulative = 0
    for year in sorted(yearly_net_incomes.keys()):
        cumulative += yearly_net_incomes[year]
        print(f"  End of {year}: Rp {cumulative:>15,.0f} (cumulative)")
    
    # 4. Analisa masalah
    print("\n=== 4. ANALISA MASALAH ===")
    print(f"""
  Initial Capital Start Year: {initial_capital.start_year if initial_capital else 'N/A'}
  First Transaction Year: 2022
  
  Ada ketidaksesuaian antara:
  - Initial Capital dimulai tahun {initial_capital.start_year if initial_capital else 'N/A'}
  - Transaksi pertama tahun 2022
  
  Kemungkinan masalah:
  1. Initial Capital Rp {initial_capital.amount:,.0f} mungkin sudah termasuk laba tahun 2022
  2. Atau Initial Capital seharusnya mulai dari 2022, bukan {initial_capital.start_year}
  
  Untuk Balance Sheet 2024:
  - Assets: Rp 265,769,082
  - Liabilities: Rp 12,217,273
  - Equity saat ini:
    * Modal Awal: Rp {int(initial_capital.amount):,}
    * Laba Ditahan (2022+2023): Rp {int(yearly_net_incomes[2022] + yearly_net_incomes[2023]):,}
    * Laba 2024: Rp {int(yearly_net_incomes[2024]):,}
    * Total Equity: Rp {int(float(initial_capital.amount) + yearly_net_incomes[2022] + yearly_net_incomes[2023] + yearly_net_incomes[2024]):,}
  
  - Liab + Equity: Rp {int(12217273 + float(initial_capital.amount) + yearly_net_incomes[2022] + yearly_net_incomes[2023] + yearly_net_incomes[2024]):,}
  - Assets: Rp 265,769,082
  - Selisih: Rp {int(265769082 - (12217273 + float(initial_capital.amount) + yearly_net_incomes[2022] + yearly_net_incomes[2023] + yearly_net_incomes[2024])):,}
""")
    
    # 5. Cek apakah Modal Awal seharusnya sudah termasuk laba 2022
    print("\n=== 5. CEK KEMUNGKINAN MODAL AWAL SUDAH TERMASUK LABA 2022 ===")
    
    # Jika Modal Awal sudah termasuk laba 2022, maka:
    # Assets = Liabilities + (Modal Awal - Laba 2022) + Laba Ditahan (2022+2023) + Laba 2024
    # Atau dengan kata lain, Laba Ditahan seharusnya TIDAK termasuk 2022
    
    # Coba hitung tanpa 2022 di Laba Ditahan
    retained_without_2022 = yearly_net_incomes[2023]  # Hanya 2023
    
    total_equity_without_2022 = initial_capital.amount + retained_without_2022 + yearly_net_incomes[2024]
    liab_plus_equity_without_2022 = 12217273 + total_equity_without_2022
    
    print(f"""
  Jika Laba Ditahan TIDAK termasuk 2022 (karena sudah ada di Modal Awal):
  - Modal Awal: Rp {int(initial_capital.amount):,}
  - Laba Ditahan (hanya 2023): Rp {int(retained_without_2022):,}
  - Laba 2024: Rp {int(yearly_net_incomes[2024]):,}
  - Total Equity: Rp {int(float(initial_capital.amount) + retained_without_2022 + yearly_net_incomes[2024]):,}
  - Liab + Equity: Rp {int(12217273 + float(initial_capital.amount) + retained_without_2022 + yearly_net_incomes[2024]):,}
  - Assets: Rp 265,769,082
  - Selisih: Rp {int(265769082 - (12217273 + float(initial_capital.amount) + retained_without_2022 + yearly_net_incomes[2024])):,}
""")
    
    # 6. Cek transaksi 2022
    print("\n=== 6. TRANSAKSI 2022 ===")
    txn_2022 = conn.execute(text("""
        SELECT 
            m.personal_use,
            m.internal_report,
            COUNT(*) as count,
            SUM(t.amount) as total
        FROM transactions t
        JOIN marks m ON t.mark_id = m.id
        WHERE t.company_id = :company_id
        AND YEAR(t.txn_date) = 2022
        GROUP BY m.personal_use, m.internal_report
        ORDER BY total DESC
    """), {'company_id': company_id}).fetchall()
    
    for row in txn_2022:
        print(f"  {row.personal_use} / {row.internal_report}: {row.count} txn, Total: Rp {row.total:,.0f}")
