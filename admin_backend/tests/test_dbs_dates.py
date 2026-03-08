import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bank_parsers.dbs import _extract_statement_date, _convert_dbs_date

def test_extract_statement_date():
    print("Testing _extract_statement_date...")
    
    text1 = "Statement Date : 05 Jan 2025"
    assert _extract_statement_date(text1) == (5, 1, 2025)
    
    text2 = "Statement Date : 31 Dec 2024"
    assert _extract_statement_date(text2) == (31, 12, 2024)
    
    text3 = "Random text with year 2023"
    assert _extract_statement_date(text3) == (None, None, 2023)

    # New numeric format
    text4 = "01/19/2025 02/04/2025 Rp. 11,704,461"
    assert _extract_statement_date(text4) == (19, 1, 2025)
    
    print("  _extract_statement_date: PASS")

def simulate_parse_logic(transactions, st_month, st_year, target_year=None):
    """
    Simulates the year assignment logic in parse_statement
    """
    extracted_year = target_year or st_year or 2025
    current_year = extracted_year
    results = []
    last_month = None
    first_transaction = True
    
    for raw_date in transactions:
        month_num = int(raw_date.split('/')[0])
        
        if first_transaction:
            if st_month is not None:
                if month_num > st_month:
                    current_year -= 1
            else:
                if target_year is None and month_num >= 10:
                    current_year -= 1
            first_transaction = False
            
        if last_month is not None:
            if month_num <= 3 and last_month >= 10:
                current_year += 1
            elif month_num >= 10 and last_month <= 3:
                current_year -= 1
        
        last_month = month_num
        results.append(_convert_dbs_date(raw_date, current_year))
    
    return results

def test_year_assignment_scenarios():
    print("Testing year assignment scenarios...")
    
    # Case 1: Dec transaction in a Jan statement (2025)
    # Target: 12/20 -> 2024, 01/05 -> 2025
    txns = ["12/20", "01/05"]
    results = simulate_parse_logic(txns, st_month=1, st_year=2025)
    assert "2024-12-20" in results[0]
    assert "2025-01-05" in results[1]
    print("  Case 1 (Dec txn in Jan statement): PASS")
    
    # Case 2: Nov/Dec transactions in a Dec statement (2025)
    # Target: 11/19 -> 2025, 12/06 -> 2025
    txns = ["11/19", "12/06"]
    results = simulate_parse_logic(txns, st_month=12, st_year=2025)
    assert "2025-11-19" in results[0]
    assert "2025-12-06" in results[1]
    print("  Case 2 (Nov/Dec txn in Dec statement): PASS")

    # Case 3: Descending Transactions rollover (Statement Feb 2025)
    # 01/20 -> 2025, 12/20 -> 2024
    txns = ["01/20", "12/20"]
    results = simulate_parse_logic(txns, st_month=2, st_year=2025)
    assert "2025-01-20" in results[0]
    assert "2024-12-20" in results[1]
    print("  Case 3 (Descending rollover): PASS")

    # Case 4: No statement month (fallback), target year 2025
    # Nov/Dec should NOT subtract if target_year is provided (or if we trust extracted year)
    # Wait, in the code: if target_year is None and month_num >= 10: current_year -= 1
    # So if target_year=2025 is provided, it should NOT subtract.
    txns = ["11/19"]
    results = simulate_parse_logic(txns, st_month=None, st_year=2025, target_year=2025)
    assert "2025-11-19" in results[0]
    print("  Case 4 (No statement month, target 2025): PASS")

if __name__ == "__main__":
    test_extract_statement_date()
    test_year_assignment_scenarios()
    print("\nALL TESTS PASSED")
