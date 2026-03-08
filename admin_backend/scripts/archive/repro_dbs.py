
from datetime import datetime
import re

MONTH_MAP_DBS = {
    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'MEI': 5,
    'JUN': 6, 'JUL': 7, 'AUG': 8, 'AGT': 8, 'SEP': 9, 'OCT': 10, 'OKT': 10,
    'NOV': 11, 'DEC': 12, 'DES': 12
}

def _convert_dbs_date(raw: str, year: int) -> str:
    if not raw: return ''
    try:
        # Expected format MM/DD from extraction (DBS uses US format)
        if '/' in raw and len(raw) == 5:
            month = int(raw[:2])
            day = int(raw[3:])
            return f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)} 00:00:00"
    except:
        pass
    return ''

def reproduce_issue(transactions, extracted_year):
    current_year = extracted_year
    last_month = None
    first_transaction = True
    results = []
    
    for raw_date in transactions:
        month_num = None
        if raw_date and '/' in raw_date:
            try:
                month_num = int(raw_date.split('/')[0])  # MM/DD format
            except:
                pass
        
        # Adjust starting year (Current logic: only if first transaction is Oct-Dec)
        if first_transaction and month_num is not None:
            if month_num >= 10:  # Oct, Nov, Dec
                current_year -= 1
            first_transaction = False
        
        # Year rollover detection (FIXED logic)
        if last_month is not None and month_num is not None:
            # 1. Going forward (Ascending)
            if month_num <= 3 and last_month >= 10:
                current_year += 1
            # 2. Going backward (Descending)
            elif month_num >= 10 and last_month <= 3:
                current_year -= 1
        
        if month_num is not None:
            last_month = month_num
        
        txn_iso = _convert_dbs_date(raw_date, current_year)
        results.append(txn_iso)
    
    return results

# Scenario 1: Extracted 2025, Transactions Dec (2024) -> Jan (2025)
# User chooses 2025 (target_year=2025). 
txns_ascending = ["12/28", "12/30", "01/02", "01/05"]
extracted_year_2025 = 2025
results_2025_asc = reproduce_issue(txns_ascending, extracted_year_2025)

print(f"Scenario 1 (Target 2025, Ascending):")
for raw, res in zip(txns_ascending, results_2025_asc):
    print(f"  {raw} -> {res}")

# Scenario 2: Extracted 2025, Transactions Jan (2025) -> Dec (2024)
# (Descending order)
txns_descending = ["01/05", "01/02", "12/30", "12/28"]
results_2025_desc = reproduce_issue(txns_descending, extracted_year_2025)

print(f"\nScenario 2 (Target 2025, Descending):")
for raw, res in zip(txns_descending, results_2025_desc):
    print(f"  {raw} -> {res}")

# Scenario 3: Dec 2025 Statement containing Nov-Dec 2025
# User chooses 2025.
txns_late_2025 = ["11/25", "12/05", "12/20"]
results_late_2025 = reproduce_issue(txns_late_2025, 2025)

print(f"\nScenario 3 (Target 2025, Nov-Dec 2025 - FAULTY LOGIC CHECK):")
for raw, res in zip(txns_late_2025, results_late_2025):
    print(f"  {raw} -> {res}")
