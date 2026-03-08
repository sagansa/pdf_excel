import re
import pandas as pd
from datetime import datetime
from typing import List, Optional

def safe_iso_date(year: int, month: int, day: int, fallback: str) -> str:
    try:
        return datetime(year, month, day).strftime('%Y-%m-%d')
    except ValueError:
        return fallback

def coerce_iso_date(value, default_year: Optional[int] = None) -> Optional[str]:
    """Best-effort conversion of assorted date representations to ISO format."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    if isinstance(value, (datetime, pd.Timestamp)):
        return value.strftime('%Y-%m-%d')

    text = str(value).strip()
    if not text:
        return None

    # Already in ISO format (with optional time component)
    match_iso = re.match(r'^(\d{4})[-/](\d{2})[-/](\d{2})(?:\s+\d{2}:\d{2}:\d{2})?$', text)
    if match_iso:
        year, month, day = map(int, match_iso.groups())
        return safe_iso_date(year, month, day, fallback=text)

    # DD/MM[/YYYY]
    match_ddmm = re.match(r'^(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?$', text)
    if match_ddmm:
        day = int(match_ddmm.group(1))
        month = int(match_ddmm.group(2))
        year_part = match_ddmm.group(3)

        if year_part:
            year = int(year_part)
            if year < 100:
                year += 2000 if year < 50 else 1900
        else:
            year = default_year or datetime.now().year

        return safe_iso_date(year, month, day, fallback=text)

    # Fallback to pandas parsing (still assuming day-first)
    try:
        parsed = pd.to_datetime(text, dayfirst=True, errors='raise')
        return parsed.strftime('%Y-%m-%d')
    except Exception:
        return text

def normalize_date_columns(df: pd.DataFrame, default_year: Optional[int] = None) -> pd.DataFrame:
    """Convert date-like columns to ISO strings (YYYY-MM-DD)."""
    if df is None or df.empty:
        return df

    date_like_columns = [
        col for col in df.columns
        if any(keyword in col.lower() for keyword in ('tanggal', 'date'))
    ]

    for col in date_like_columns:
        df[col] = df[col].apply(lambda value: coerce_iso_date(value, default_year))

    return df

def standardize_statement_dates(df: pd.DataFrame, date_col: str, format_type: str = 'dd/mm', base_year: Optional[int] = None) -> pd.DataFrame:
    """Convert statement dates (DD/MM or MM/DD) into ISO format with year rollover detection."""
    if df is None or df.empty or date_col not in df.columns:
        return df

    current_year = base_year or datetime.now().year
    last_month = None
    iso_dates: List[str] = []

    for raw_value in df[date_col]:
        val_str = str(raw_value).strip()
        if not val_str or val_str.lower() == 'nan':
            iso_dates.append(raw_value)
            continue

        # Match DD/MM or MM/DD
        match = re.match(r'^([0-1]?\d)[/]([0-3]?\d)$', val_str)
        if not match:
            # Try to see if it's already ISO or something else
            iso_dates.append(raw_value)
            continue

        if format_type.lower() == 'mm/dd':
            month = int(match.group(1))
            day = int(match.group(2))
        else: # Default dd/mm
            day = int(match.group(1))
            month = int(match.group(2))

        if not (1 <= day <= 31 and 1 <= month <= 12):
            iso_dates.append(raw_value)
            continue

        # Year Rollover Detection (Dec -> Jan jump)
        if last_month is not None and month < last_month:
            # Month decreased, assume new year (e.g. 12 -> 01)
            current_year += 1
        last_month = month

        try:
            iso_dates.append(datetime(current_year, month, day).strftime('%Y-%m-%d'))
        except ValueError:
            iso_dates.append(raw_value)

    df = df.copy()
    df[date_col] = iso_dates
    return df
