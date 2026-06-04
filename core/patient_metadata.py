"""
Patient metadata extraction utilities.

Provides simple heuristics to extract age and gender from OCR'd lab report text.
"""
from __future__ import annotations

import re
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

    return None


def extract_patient_metadata(text: str) -> dict:
    return {
        "age": extract_age(text),
        "gender": extract_gender(text),
    }
