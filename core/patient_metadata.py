"""
Patient metadata extraction utilities.

Provides simple heuristics to extract age and gender from OCR'd lab report text.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional


_GENDER_ALIASES = {
    "m": "male",
    "mr": "male",
    "mele": "male",
    "maie": "male",
    "msle": "male",
    "f": "female",
    "mrs": "female",
    "ms": "female",
    "miss": "female",
    "femaie": "female",
    "femele": "female",
    "femalc": "female",
}


def extract_gender(text: str) -> Optional[str]:
    if not text:
        return None

    normalized = text.lower()
    normalized = normalized.replace("\n", " ")

    patterns = [
        r"gender\s*[:\-]\s*([a-z]+)\b",
        r"sex\s*[:\-]\s*([a-z]+)\b",
        r"age/sex\s*[:\-]\s*\d{1,3}\s*[/:,]?\s*([a-z]+)\b",
        r"\b\d{1,3}\s*[yY]?\s*[/:\\]\s*(m|f)\b",
        r"patient\s*[:\-]\s*(mr|mrs|ms|miss)\b",
        r"\b(male|female)\b",
    ]

    for pat in patterns:
        match = re.search(pat, normalized, flags=re.I)
        if match:
            value = match.group(1).lower()
            if value in _GENDER_ALIASES:
                return _GENDER_ALIASES[value]
            if value in ("male", "female"):
                return value

    # M / F checkbox detection: count which letter appears more often
    # in checkbox-like contexts (e.g. "[M]" "(F)" "M / F" etc.)
    m_count = len(re.findall(r"(?:\[|\(|\b)\s*[mM]\s*(?:\]|\)|/)", text))
    f_count = len(re.findall(r"(?:\[|\(|\b)\s*[fF]\s*(?:\]|\)|/)", text))

    if m_count > f_count:
        return "male"
    if f_count > m_count:
        return "female"

    return None


def _parse_date(text: str) -> Optional[date]:
    """Try various date formats and return a date object."""
    date_patterns = [
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
        r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
        r"(\d{1,2})\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(\d{4})",
    ]
    for pat in date_patterns:
        match = re.search(pat, text, flags=re.I)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                try:
                    if int(groups[0]) > 31:
                        return date(int(groups[0]), int(groups[1]), int(groups[2]))
                    elif int(groups[2]) > 31:
                        return date(int(groups[0]), int(groups[1]), int(groups[2]))
                    else:
                        return date(int(groups[2]), int(groups[1]), int(groups[0]))
                except (ValueError, IndexError):
                    continue
    return None


def extract_age(text: str) -> Optional[int]:
    if not text:
        return None

    normalized = text.lower()
    normalized = normalized.replace("\n", " ")

    patterns = [
        r"age\s*[:\-]\s*(\d{1,3})\b",
        r"age/sex\s*[:\-]\s*(\d{1,3})\s*[/:,]?\s*(?:m|f|male|female)\b",
        r"\b(\d{1,3})\s*(?:years|yrs|year|y)\b",
        r"\b(\d{1,3})\s*yrs?\b",
        r"\b(\d{1,3})\s*[yY]\s*[/\\]\s*(?:m|f)\b",
    ]

    for pat in patterns:
        match = re.search(pat, normalized, flags=re.I)
        if match:
            try:
                age_value = int(match.group(1))
                if 0 <= age_value <= 120:
                    return age_value
            except ValueError:
                continue

    # D.O.B detection → calculate age
    dob_patterns = [
        r"(?:dob|d\.o\.b|date\s*of\s*birth)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        r"(?:dob|d\.o\.b|date\s*of\s*birth)\s*[:\-]?\s*(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
        r"(?:dob|d\.o\.b|date\s*of\s*birth)\s*[:\-]?\s*(\d{1,2}\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{4})",
    ]
    for pat in dob_patterns:
        match = re.search(pat, normalized, flags=re.I)
        if match:
            dob = _parse_date(match.group(1))
            if dob:
                today = date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                if 0 <= age <= 120:
                    return age

    return None


def extract_patient_metadata(text: str) -> dict:
    return {
        "age": extract_age(text),
        "gender": extract_gender(text),
    }
