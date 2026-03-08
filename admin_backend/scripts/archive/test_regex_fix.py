import re

def safe_iso_date(year: int, month: int, day: int, fallback: str) -> str:
    from datetime import datetime
    try:
        return datetime(year, month, day).strftime('%Y-%m-%d')
    except ValueError:
        return fallback

def coerce_iso_date_fixed(text):
    # Updated regex to handle datetime strings
    match_iso = re.match(r'^(\d{4})[-/](\d{2})[-/](\d{2})(?:\s+\d{2}:\d{2}:\d{2})?$', text)
    if match_iso:
        year, month, day = map(int, match_iso.groups())
        return safe_iso_date(year, month, day, fallback=text)
    return None

# Test cases
test_cases = [
    "2025-02-07 00:00:00",
    "2025-02-07",
    "2025-07-02 00:00:00",
]

for test in test_cases:
    result = coerce_iso_date_fixed(test)
    print(f"Input: {test:25} -> Output: {result}")
