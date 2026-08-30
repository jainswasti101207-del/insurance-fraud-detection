"""Best-effort accident-date / claim-date extraction from narrative text.

Roughly half of Accident_Reports.docx narratives state an exact calendar date
("On Friday, August 1, 1995, ...") while the other half use a vague
week-of-month template ("On a Friday in the fourth week of January 1994, ...")
that carries no day-level precision. Exact filing-delay-in-days is therefore
only recoverable for a subset of the 100 historical claims; this module
returns None when it can't be computed rather than guessing. New claims
entered live through the app instead collect exact accident/claim dates
directly (see app/pages/1_New_Claim.py), so this limitation only affects
replay of the 100 historical claims, not the live system going forward.
"""
from __future__ import annotations

import re
from datetime import date

ACCIDENT_DATE_RE = re.compile(r"On (\w+), (\w+) (\d{1,2}), (\d{4})")
CLAIM_DATE_RE = re.compile(r"(?:filed|reported|processed)[^.]*?on (\w+), (\w+) (\d{1,2})", re.IGNORECASE)

MAX_PLAUSIBLE_DELAY_DAYS = 120


def _parse_month_day(month_name: str, day: str, year: int) -> date | None:
    try:
        return date(year, list(_MONTHS).index(month_name) + 1, int(day))
    except (ValueError, IndexError):
        return None


_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def extract_accident_date(narrative_text: str) -> date | None:
    match = ACCIDENT_DATE_RE.search(narrative_text)
    if not match:
        return None
    _, month_name, day, year = match.groups()
    return _parse_month_day(month_name, day, int(year))


def extract_filing_delay_days(narrative_text: str) -> int | None:
    """Return (claim_date - accident_date).days if both are exactly parseable, else None."""
    accident_date = extract_accident_date(narrative_text)
    if accident_date is None:
        return None

    claim_section = narrative_text[narrative_text.find("Claim Evaluation"):]
    claim_match = CLAIM_DATE_RE.search(claim_section)
    if not claim_match:
        return None
    _, month_name, day = claim_match.groups()
    if month_name not in _MONTHS:
        return None

    for year_candidate in (accident_date.year, accident_date.year + 1):
        claim_date = _parse_month_day(month_name, day, year_candidate)
        if claim_date is None:
            continue
        delta = (claim_date - accident_date).days
        if 0 <= delta <= MAX_PLAUSIBLE_DELAY_DAYS:
            return delta
    return None
