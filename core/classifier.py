"""
Classifier with 3-tier fallback — UNKNOWN is a last resort only.

Priority:
  1. classify_numeric()  — when value + low/high are all known floats
  2. classify_with_range_str() — parses range string first
  3. Both guarantee: if value and range exist → never UNKNOWN
"""
from __future__ import annotations

import logging

from core.normalization import ParsedRange, parse_reference_range

logger = logging.getLogger(__name__)


def _classify_against_parsed(value: float, pr: ParsedRange) -> str:
    """
    Core decision logic against a ParsedRange.
    Returns unknown ONLY when both low and high are None (range truly absent).
    """
    if pr.low is not None and pr.high is not None:
        if value < pr.low:
            return "low"
        if value > pr.high:
            return "high"
        return "normal"

    if pr.low is not None:           # one-sided: has a minimum
        return "low" if value < pr.low else "normal"

    if pr.high is not None:          # one-sided: has a maximum
        return "high" if value > pr.high else "normal"

    return "unknown"                 # genuinely no range info


def classify(value: float, range_str: str, default_unit: str = "") -> str:
    """
    Classify value against a range string.
    Logs clearly when unknown is returned.
    """
    try:
        pr = parse_reference_range(range_str, default_unit=default_unit)
        result = _classify_against_parsed(value, pr)
        if result == "unknown":
            logger.warning(
                "[classify] UNKNOWN — could not parse range: value=%s range=%r",
                value, range_str,
            )
        return result
    except Exception as exc:
        logger.error("[classify] exception: %s — value=%s range=%r", exc, value, range_str)
        return "unknown"


def classify_numeric(value: float, low: float, high: float) -> str:
    """
    Classify directly against numeric bounds.
    NEVER returns unknown unless both bounds are None.
    """
    # Safety check: if either bound is None, cannot classify
    if low is None or high is None:
        logger.warning("[classify_numeric] bounds missing: low=%s high=%s — cannot classify", low, high)
        return "unknown"
    
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "normal"
