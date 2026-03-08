
import pandas as pd
date_str = "2025-02-07 00:00:00"
dt = pd.to_datetime(date_str, dayfirst=True)
print(f"Input: {date_str}")
print(f"Parsed: {dt}")
print(f"Month: {dt.month}, Day: {dt.day}")
