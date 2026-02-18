import pandas as pd
from datetime import date, datetime

def calculate_prepaid_amortization_details(item, target_date=None):
    if target_date is None:
        target_date = date.today()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date[:10], '%Y-%m-%d').date()
    
    start_date = item['start_date']
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date[:10], '%Y-%m-%d').date()
    
    duration = int(item['duration_months'])
    bruto = float(item['amount_bruto'])
    monthly_expense = bruto / duration if duration > 0 else bruto
    
    if target_date < start_date:
        months_active = 0
    else:
        diff_years = target_date.year - start_date.year
        diff_months = target_date.month - start_date.month
        months_active = (diff_years * 12) + diff_months + 1
        months_active = min(months_active, duration)
    
    accumulated = round(monthly_expense * months_active, 2)
    book_value = round(bruto - accumulated, 2)
    
    return {
        'accumulated_amortization': accumulated,
        'book_value': book_value,
        'months_active': months_active,
        'monthly_expense': round(monthly_expense, 2)
    }

# Test Case: 90m Net, 24 months, starting 2025-08-01, Gross-Up 10%
net = 90_000_000
tax_rate = 10
duration = 24
bruto = net / (1 - (tax_rate / 100))
start_date = "2025-08-01"

item = {
    'amount_bruto': bruto,
    'duration_months': duration,
    'start_date': start_date
}

print(f"Bruto Calculation: {bruto:,.2f}")
print("-" * 30)

# Position as of 31 Dec 2025
res_dec = calculate_prepaid_amortization_details(item, "2025-12-31")
print(f"As of 2025-12-31:")
print(f"  Months Active: {res_dec['months_active']}") # Should be 5 (Aug, Sep, Oct, Nov, Dec)
print(f"  Accumulated: {res_dec['accumulated_amortization']:,.2f}")
print(f"  Book Value: {res_dec['book_value']:,.2f}")

# Monthly Expense Check
print(f"  Monthly Expense: {res_dec['monthly_expense']:,.2f}")

# Target values from user:
# Bruto should be 100m
# Accum after 5 months should be (100m / 24) * 5 = 20.833.333,33
# BV should be 100m - 20.83m = 79.166.666,67

expected_bruto = 100_000_000
expected_accum = round((expected_bruto / 24) * 5, 2)
expected_bv = round(expected_bruto - expected_accum, 2)

print("-" * 30)
print(f"Validation:")
print(f"  Bruto correct? {abs(bruto - expected_bruto) < 0.01}")
print(f"  Accum correct? {abs(res_dec['accumulated_amortization'] - expected_accum) < 0.01}")
print(f"  BV correct? {abs(res_dec['book_value'] - expected_bv) < 0.01}")
