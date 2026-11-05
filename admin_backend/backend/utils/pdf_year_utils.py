import os
import re
import pypdf
from typing import Dict, Optional

def infer_year_from_pdf(pdf_path: str) -> Optional[int]:
    """Extract a plausible statement year by scanning the first pages of the PDF."""
    try:
        with open(pdf_path, 'rb') as fh:
            reader = pypdf.PdfReader(fh)
            text_content = []
            for page in reader.pages[:2]:
                try:
                    text_content.append(page.extract_text() or '')
                except Exception:
                    continue
            text = '\n'.join(text_content)
    except Exception:
        return None

    year_counts: Dict[int, int] = {}

    for _, _, year in re.findall(r'(\d{2})/(\d{2})/(\d{4})', text):
        year_int = int(year)
        year_counts[year_int] = year_counts.get(year_int, 0) + 1

    for year in re.findall(r'((?:19|20)\d{2})', text):
        year_int = int(year)
        year_counts[year_int] = year_counts.get(year_int, 0) + 1

    if year_counts:
        return max(year_counts, key=year_counts.get)

    return None

def infer_year_from_filename(path: str) -> Optional[int]:
    """Extract a year from the supplied filename."""
    basename = os.path.basename(path)
    matches = re.findall(r'(?:19|20)\d{2}', basename)
    if not matches:
        return None
    # Prefer the last occurrence in case of ranges like 2023-2024
    return int(matches[-1])
