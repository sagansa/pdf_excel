
MONTH_MAP = {
    'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
    'MAY': '05', 'MEI': '05', 'JUN': '06', 'JUL': '07', 
    'AUG': '08', 'AGT': '08', 'SEP': '09', 'OCT': '10', 
    'OKT': '10', 'NOV': '11', 'DEC': '12', 'DES': '12'
}

def _convert_cc_date(raw: str, last_month: int | None, current_year: int):
    print(f"DEBUG: Processing '{raw}'")
    if not raw:
        return '', last_month, current_year
    raw = raw.strip()
    
    day = None
    month_int = None
    
    if '-' in raw:
        parts = raw.split('-', 1)
        if len(parts) == 2:
            try:
                day = int(parts[0])
                month_str = parts[1].upper()
                month_val = MONTH_MAP.get(month_str)
                if month_val:
                    month_int = int(month_val)
            except ValueError:
                pass
    elif '/' in raw:
        parts = raw.split('/', 1)
        if len(parts) == 2:
            try:
                # COPY FROM bca_cc.py
                day = int(parts[0])
                month_int = int(parts[1])
                print(f"DEBUG: Parsed Day={day}, Month={month_int}")
            except ValueError:
                pass

    if day is not None and month_int is not None:
        try:
            if not (1 <= day <= 31 and 1 <= month_int <= 12):
                return '', last_month, current_year
                
            if last_month is not None and month_int < last_month:
                current_year += 1
            last_month = month_int
            date_iso = f"{current_year}-{str(month_int).zfill(2)}-{str(day).zfill(2)}"
            return f"{date_iso} 00:00:00", last_month, current_year
        except Exception:
            return '', last_month, current_year
            
    return '', last_month, current_year

# Test Case
print("Test 1: 07/01 (Jan 7)")
res1 = _convert_cc_date("07/01", None, 2025)
print(f"Result 1: {res1}")

print("\nTest 2: 01/07 (July 1)")
res2 = _convert_cc_date("01/07", None, 2025)
print(f"Result 2: {res2}")
