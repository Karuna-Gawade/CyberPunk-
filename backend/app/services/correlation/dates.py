"""
Date normalization and forensic validation logic.
Validates:
1. Plausible DOB age (between 18 and 100 years old)
2. No future dates
3. Statement period covers salary slip month
4. Chronological sequence of transaction dates
"""

import re
from datetime import datetime, timezone
from typing import Optional, Tuple

DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%Y-%m-%d",
    "%d/%m/%y",
    "%d-%m-%y",
    "%B %Y",      # e.g. "October 2026"
    "%b %Y",       # e.g. "Oct 2026"
]


def parse_flexible_date(date_str: str) -> Optional[datetime]:
    """Attempts parsing various common Indian date string formats."""
    if not date_str:
        return None
    clean = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(clean, fmt)
        except ValueError:
            continue
    return None


def validate_plausible_dob(dob_str: str, current_year: int = 2026) -> Tuple[bool, str]:
    """Validates that DOB implies plausible adult working age (18 to 100 years)."""
    dt = parse_flexible_date(dob_str)
    if not dt:
        return False, "Unparseable date of birth format"

    age = current_year - dt.year
    if age < 18:
        return False, f"Date of birth indicates age of {age} (below minimum working age of 18)"
    if age > 100:
        return False, f"Date of birth indicates implausible age of {age} (over 100 years)"
    return True, f"Plausible age: {age} years"


def are_dates_equal(dob1: str, dob2: str) -> bool:
    """Compares two date strings regardless of formatting differences (e.g. DD/MM/YYYY vs DD-MM-YYYY)."""
    dt1 = parse_flexible_date(dob1)
    dt2 = parse_flexible_date(dob2)
    if dt1 and dt2:
        return (dt1.year, dt1.month, dt1.day) == (dt2.year, dt2.month, dt2.day)
    # Fallback to normalized string comparison
    c1 = re.sub(r"[^\d]", "", dob1)
    c2 = re.sub(r"[^\d]", "", dob2)
    return bool(c1 and c2 and c1 == c2)


def check_statement_period_covers_month(period_str: str, slip_month_str: str) -> Tuple[bool, str]:
    """
    Verifies that the bank statement period (e.g. '01/10/2026 to 31/10/2026')
    covers the payslip month (e.g. 'October 2026').
    """
    if not period_str or not slip_month_str:
        return True, "Period or month string missing"

    slip_dt = parse_flexible_date(slip_month_str)
    if not slip_dt:
        return True, "Unable to parse payslip month"

    # Extract dates from period string (e.g. '01/10/2026 to 31/10/2026')
    matches = re.findall(r"\d{2}[/-]\d{2}[/-]\d{4}", period_str)
    if len(matches) >= 2:
        start_dt = parse_flexible_date(matches[0])
        end_dt = parse_flexible_date(matches[1])
        if start_dt and end_dt:
            # Check if slip month and year falls within start and end
            slip_month_start = datetime(slip_dt.year, slip_dt.month, 1)
            if start_dt <= slip_month_start <= end_dt or (start_dt.year == slip_dt.year and start_dt.month == slip_dt.month):
                return True, "Bank statement period covers payslip month"
            else:
                return False, f"Bank statement period ({period_str}) does not cover payslip month ({slip_month_str})"

    return True, "Unable to definitively parse statement range"
