import logging
import asyncio
from typing import List, Dict, Any, Optional

from medical.explainer import generate_explanation, gemini_available, groq_client, GEMINI_MODEL, GROQ_MODEL, gemini_client
from core.normalization import clean_unit, normalize_test_name, TEST_EXPECTED_UNITS

logger = logging.getLogger(__name__)


_ABBREV_MAP = {
    "wbc": "white blood cell",
    "white blood cell": "white blood cell",
    "white blood cell count": "white blood cell",
    "white blood cells": "white blood cell",
    "rbc": "red blood cell",
    "red blood cell": "red blood cell",
    "red blood cell count": "red blood cell",
    "red blood cells": "red blood cell",
    "hb": "hemoglobin",
    "hgb": "hemoglobin",
    "hemoglobin": "hemoglobin",
    "plt": "platelet",
    "platelet": "platelet",
    "platelets": "platelet",
    "platelet count": "platelet",
    "hct": "hematocrit",
    "hematocrit": "hematocrit",
}


def _normalize(name: str) -> str:
    """Normalize a test name for fuzzy matching between reports."""
    n = name.lower().strip()
    n = "".join(c for c in n if c.isalnum() or c.isspace())
    n = " ".join(n.split())
    return _ABBREV_MAP.get(n, n)


def _distance_from_normal(value: float, ref_low: Optional[float], ref_high: Optional[float]) -> float:
    """Return how far *value* is outside the reference range (0 = inside)."""
    if ref_low is not None and value < ref_low:
        return ref_low - value
    if ref_high is not None and value > ref_high:
        return value - ref_high
    return 0.0


def _is_abnormal(status: str) -> bool:
    return status in ("high", "low")


def normalize_value_to_standard(value: float, unit: str, test_key: str) -> tuple[float, str]:
    """Convert a (value, unit) pair to a standard unit for comparison"""
    if not unit:
        return value, unit

    u_lower = unit.lower().replace(" ", "")

    # lakhs/cumm → x10³/µL  (1 lakh = 100 x10³)
    if u_lower in ("lakhs/cumm", "lakh/cumm", "lakhs/mm3", "lakh/mm3"):
        return round(value * 100, 2), "x10^3/µL"

    # millions/cumm → x10⁶/µL
    if u_lower in ("millions/cumm", "million/cumm", "millions/mm3", "million/mm3", "million/cmm"):
        return value, "x10^6/µL"

    # Raw count /cumm → x10³/µL  (e.g. 8000 cumm → 8 x10³/µL)
    expected = TEST_EXPECTED_UNITS.get(test_key, "")
    if u_lower in ("cumm", "/cumm", "cells/cumm", "cells/mm3", "/mm3"):
        if expected == "x10^3/µL":
            return round(value / 1000, 2), "x10^3/µL"
        if expected == "x10^6/µL":
            return round(value / 1000000, 2), "x10^6/µL"
        return round(value / 1000, 2), "x10^3/µL"

    return value, unit


def _convert_to_expected_unit(value: float, unit: str, test_key: str) -> tuple[float, str]:
    """Convert (value, unit) to expected standard unit for test_key."""
    if not unit or not test_key:
        return value, unit

    expected = TEST_EXPECTED_UNITS.get(test_key, "")
    cleaned = clean_unit(unit, test_key)

    if cleaned == expected:
        return value, cleaned

    # Try Indian unit normalization first (works even when expected is unknown)
    normalized_val, normalized_unit = normalize_value_to_standard(value, unit, test_key)
    if normalized_unit != unit:
        return normalized_val, normalized_unit

    if not expected:
        return value, cleaned

    u_lower = unit.lower().replace(" ", "")

    # lakhs/cumm → expected (e.g. x10³/µL for WBC/Platelets)
    if "lakh" in u_lower:
        if "x10^6" in expected:
            return round(value * 0.1, 2), expected
        return round(value * 100, 2), expected

    # millions/cumm → expected (e.g. x10⁶/µL for RBC)
    if "million" in u_lower:
        if "x10^6" in expected:
            return value, expected
        if "x10^3" in expected:
            return round(value * 1000, 2), expected

    # Raw cell count in cells/cumm or /mm³ → expected (e.g. 8000 cumm → 8 x10³/µL)
    if u_lower in ("cumm", "/cumm", "cells/cumm", "cells/mm3", "/mm3"):
        if "x10^3" in expected:
            return round(value / 1000, 2), expected
        if "x10^6" in expected:
            return round(value / 1000000, 2), expected

    return value, cleaned


async def compare_analyses(analysis1: Dict[str, Any], analysis2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two analysis results using value-based logic.

    *analysis1* — older report
    *analysis2* — newer report
    """
    raw1 = analysis1.get("results", [])
    raw2 = analysis2.get("results", [])

    logger.info("[compare] Report 1 raw test names: %s", [r.get("test_name") for r in raw1])
    logger.info("[compare] Report 2 raw test names: %s", [r.get("test_name") for r in raw2])

    # Build dicts keyed by normalized name; store original test_name on each result
    results1: Dict[str, Any] = {}
    for r in raw1:
        key = _normalize(r.get("test_name", ""))
        r["_original_name"] = r.get("test_name", key)
        results1[key] = r

    results2: Dict[str, Any] = {}
    for r in raw2:
        key = _normalize(r.get("test_name", ""))
        r["_original_name"] = r.get("test_name", key)
        results2[key] = r

    logger.info("[compare] Normalized keys — Report 1: %s", list(results1.keys()))
    logger.info("[compare] Normalized keys — Report 2: %s", list(results2.keys()))

    improved: List[Dict[str, Any]] = []
    worsened: List[Dict[str, Any]] = []
    stable: List[Dict[str, Any]] = []

    all_tests = set(results1.keys()) & set(results2.keys())
    logger.info("[compare] Matched tests: %s", list(all_tests))

    for test_name in all_tests:
        r1 = results1[test_name]
        r2 = results2[test_name]

        prev_val = r1.get("value")
        curr_val = r2.get("value")
        if prev_val is None or curr_val is None:
            continue
        if not isinstance(prev_val, (int, float)) or not isinstance(curr_val, (int, float)):
            continue

        # BUG 3: Clean units before display
        raw_unit = r1.get("unit", "")
        unit = clean_unit(raw_unit, r1.get("test_name", ""))

        # BUG 1: Normalize both values to expected unit if they differ
        test_key_raw = r2.get("test_name", test_name)
        test_key = normalize_test_name(test_key_raw)
        prev_val, unit = _convert_to_expected_unit(prev_val, raw_unit, test_key)
        curr_val, _ = _convert_to_expected_unit(curr_val, r2.get("unit", ""), test_key)

        ref_low = r1.get("reference_low")
        ref_high = r1.get("reference_high")

        if prev_val == 0:
            change_pct = 0.0
        else:
            change_pct = round(((curr_val - prev_val) / prev_val) * 100, 1)

        display_name = r2.get("_original_name", test_name)

        item = {
            "test_name": display_name,
            "prev_value": prev_val,
            "curr_value": curr_val,
            "unit": unit,
            "change_pct": change_pct,
        }

        # BUG 2: Use 10% threshold for percentage tests, 5% for others
        threshold = 10 if unit == "%" else 5
        if abs(change_pct) < threshold:
            stable.append(item)
            continue

        prev_status = r1.get("status", "unknown")
        curr_status = r2.get("status", "unknown")

        prev_abnormal = _is_abnormal(prev_status)
        curr_abnormal = _is_abnormal(curr_status)

        prev_dist = _distance_from_normal(prev_val, ref_low, ref_high)
        curr_dist = _distance_from_normal(curr_val, ref_low, ref_high)

        if prev_abnormal and not curr_abnormal:
            # Was abnormal, now normal → improved
            improved.append(item)
        elif not prev_abnormal and curr_abnormal:
            # Was normal, now abnormal → worsened
            worsened.append(item)
        elif prev_abnormal and curr_abnormal:
            # Both abnormal: closer to normal = improved, further = worsened
            if curr_dist < prev_dist:
                improved.append(item)
            elif curr_dist > prev_dist:
                worsened.append(item)
            else:
                stable.append(item)
        else:
            stable.append(item)

    logger.info("[compare] Improved: %d, Worsened: %d, Stable: %d",
                len(improved), len(worsened), len(stable))

    # AI Summary
    summary = await generate_comparison_summary(analysis1, analysis2, improved, worsened, stable)

    return {
        "improved": improved,
        "worsened": worsened,
        "stable": stable,
        "summary": summary,
    }


def _format_test_list(tests: List[Dict[str, Any]], analysis_results: Dict[str, Any]) -> str:
    """Format a list of tests into a human-readable string with values."""
    parts = []
    for t in tests:
        name = t["test_name"]
        res = analysis_results.get(name, {})
        val = res.get("value", "?")
        unit = res.get("unit", "")
        parts.append(f"{name} {val} {unit}".strip())
    return ", ".join(parts) if parts else "None"


async def generate_comparison_summary(
    analysis1: Dict[str, Any],
    analysis2: Dict[str, Any],
    improved: List[Dict[str, Any]],
    worsened: List[Dict[str, Any]],
    stable: List[Dict[str, Any]],
) -> str:
    results1 = {_normalize(r["test_name"]): r for r in analysis1.get("results", [])}
    results2 = {_normalize(r["test_name"]): r for r in analysis2.get("results", [])}

    report1_lines = []
    for t in improved:
        r = results1.get(_normalize(t["test_name"]))
        if r:
            report1_lines.append(f"{t['test_name']} {r.get('value', '?')} {r.get('unit', '')}".strip())
    for t in worsened:
        r = results1.get(_normalize(t["test_name"]))
        if r:
            report1_lines.append(f"{t['test_name']} {r.get('value', '?')} {r.get('unit', '')}".strip())
    for t in stable:
        r = results1.get(_normalize(t["test_name"]))
        if r:
            report1_lines.append(f"{t['test_name']} {r.get('value', '?')} {r.get('unit', '')}".strip())

    report2_lines = []
    for t in improved:
        r = results2.get(_normalize(t["test_name"]))
        if r:
            report2_lines.append(f"{t['test_name']} {r.get('value', '?')} {r.get('unit', '')}".strip())
    for t in worsened:
        r = results2.get(_normalize(t["test_name"]))
        if r:
            report2_lines.append(f"{t['test_name']} {r.get('value', '?')} {r.get('unit', '')}".strip())
    for t in stable:
        r = results2.get(_normalize(t["test_name"]))
        if r:
            report2_lines.append(f"{t['test_name']} {r.get('value', '?')} {r.get('unit', '')}".strip())

    improved_detail = "; ".join(
        f"{t['test_name']} ({t['prev_value']} → {t['curr_value']} {t['unit']}, {t['change_pct']:+.1f}%)"
        for t in improved
    ) or "None"

    worsened_detail = "; ".join(
        f"{t['test_name']} ({t['prev_value']} → {t['curr_value']} {t['unit']}, {t['change_pct']:+.1f}%)"
        for t in worsened
    ) or "None"

    prompt = f"""You are a medical assistant comparing two lab reports for a patient.

Report 1 (older):
{chr(10).join(report1_lines) if report1_lines else 'No data'}

Report 2 (newer):
{chr(10).join(report2_lines) if report2_lines else 'No data'}

Changes detected:
- Improved: {improved_detail}
- Worsened: {worsened_detail}

TASK:
Write a 3-4 sentence human-friendly summary that:
- Mentions which specific tests improved with their values
- Mentions which specific tests worsened with their values
- Describes the overall health trend
- Gives one practical recommendation

Write in simple English a patient can understand.
Do NOT use medical jargon.
Do NOT give a generic response — use the actual numbers provided above.
End with: Please consult your doctor for a full clinical evaluation."""

    if gemini_available:
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: gemini_client.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.4,
                        "max_output_tokens": 600,
                    }
                )
            )
            if response.text:
                return response.text
        except Exception as exc:
            logger.error("[comparison] Gemini failed: %s", exc)

    if groq_client:
        try:
            response = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.4,
            )
            result_text = response.choices[0].message.content
            if result_text:
                return result_text
        except Exception as exc:
            logger.error("[comparison] Groq failed: %s", exc)

    return "Comparison summary unavailable. Please review the changes in biomarkers above and consult your doctor."
