"""
Test script untuk memverifikasi logika Laba Ditahan dengan data simulasi
Sesuai dengan skenario user:
- 2023: Laba/Rugi Tahun Berjalan = (Rp 55.734.368)
- 2024: Laba Ditahan = (Rp 55.734.368), Laba/Rugi Tahun Berjalan = Rp 28.774.393
- 2025: Laba Ditahan = (Rp 55.734.368) + Rp 28.774.393 = (Rp 26.959.975)
"""

def hitung_laba_ditahan_tahun_sebelumnya(year, yearly_net_incomes):
    """
    Menghitung Laba Ditahan Tahun Sebelumnya untuk suatu tahun laporan.
    Laba Ditahan Tahun Sebelumnya = akumulasi net income dari semua tahun SEBELUM tahun laporan.
    """
    cumulative = 0.0
    for y in range(min(yearly_net_incomes.keys()), year):
        cumulative += yearly_net_incomes.get(y, 0.0)
    return cumulative

# Data simulasi sesuai deskripsi user
yearly_net_incomes = {
    2023: -55734368,  # (Rp 55.734.368) - rugi
    2024: 28774393,   # Rp 28.774.393 - laba
    2025: 0,          # Belum ada data
}

print("=" * 70)
print("SIMULASI PERHITUNGAN LABA DITAHAN TAHUN SEBELUMNYA")
print("=" * 70)

print("\n--- Net Income per Tahun ---")
for year, net_income in sorted(yearly_net_incomes.items()):
    print(f"  {year}: Rp {net_income:,.0f}")

print("\n--- Laba Ditahan Tahun Sebelumnya per Tahun Laporan ---")
for report_year in [2023, 2024, 2025, 2026]:
    retained_earnings = hitung_laba_ditahan_tahun_sebelumnya(report_year, yearly_net_incomes)
    
    print(f"\n  Laporan Tahun {report_year}-12-31:")
    print(f"    Laba Ditahan Tahun Sebelumnya: Rp {retained_earnings:,.0f}")
    
    # Tampilkan breakdown
    if report_year > 2023:
        breakdown = []
        for y in range(2023, report_year):
            income = yearly_net_incomes.get(y, 0)
            if income != 0:
                breakdown.append(f"{y}: Rp {income:,.0f}")
        if breakdown:
            print(f"    Breakdown: {' + '.join(breakdown)} = Rp {retained_earnings:,.0f}")
    
    # Laba/Rugi Tahun Berjalan
    current_year_income = yearly_net_incomes.get(report_year, 0)
    print(f"    Laba/Rugi Tahun Berjalan: Rp {current_year_income:,.0f}")

print("\n" + "=" * 70)
print("VERIFIKASI DENGAN SKENARIO USER")
print("=" * 70)

print("\n2023:")
print(f"  ✓ Laba/Rugi Tahun Berjalan: Rp {yearly_net_incomes[2023]:,.0f}")
print(f"  ✓ Laba Ditahan Tahun Sebelumnya: Rp {hitung_laba_ditahan_tahun_sebelumnya(2023, yearly_net_incomes):,.0f} (tahun pertama)")

print("\n2024:")
re_2024 = hitung_laba_ditahan_tahun_sebelumnya(2024, yearly_net_incomes)
print(f"  ✓ Laba Ditahan Tahun Sebelumnya: Rp {re_2024:,.0f} (dari 2023)")
print(f"  ✓ Laba/Rugi Tahun Berjalan: Rp {yearly_net_incomes[2024]:,.0f}")

print("\n2025:")
re_2025 = hitung_laba_ditahan_tahun_sebelumnya(2025, yearly_net_incomes)
print(f"  ✓ Laba Ditahan Tahun Sebelumnya: Rp {re_2025:,.0f}")
print(f"     = 2023 ({yearly_net_incomes[2023]:,.0f}) + 2024 ({yearly_net_incomes[2024]:,.0f})")
print(f"     = ({-55734368:,.0f}) + {28774393:,.0f} = {re_2025:,.0f}")

expected_2025 = -55734368 + 28774393
print(f"\n  Expected: Rp {expected_2025:,.0f}")
print(f"  Calculated: Rp {re_2025:,.0f}")
print(f"  Match: {'✓ PASS' if expected_2025 == re_2025 else '✗ FAIL'}")

print("\n" + "=" * 70)
