"""Unified lab report pipeline — orchestrates parser → resolver → classifier"""
from __future__ import annotations

import logging
import re
from typing import Optional, Dict

from core.parser import parse_lab_report
from core.resolver import resolve_test_key_with_confidence
from core.classifier import classify_numeric
from core.normalization import (
    normalize_unit,
    normalize_test_name,
    repair_ocr_text,
    sanity_check_value,
    fix_ocr_value_errors,
    normalize_count_to_per_uL,
    convert_value,
    DEFAULT_RANGES,
    parse_reference_range,
)
from core.schemas import ParsedTest, ResolvedTest, ReferenceRange, CompletenessTracker
from medical.reference_db import get_reference_range, get_test_definition
# RAG LAYER: retrieve patterns and categories
from medical.clinical_kb import (
    get_patterns_for_test,
    TEST_KEY_TO_CATEGORY,
)

logger = logging.getLogger(__name__)

# Medical markers that indicate text is a lab report
_MEDICAL_MARKERS: list[str] = [
# CBC markers
    "cbc", "complete blood count", "hemogram", "blood count",
    "hemoglobin", "haemoglobin", "hb", "hgb",
    "wbc", "white blood cell", "leukocyte", "leucocyte",
    "rbc", "red blood cell", "erythrocyte",
    "platelet", "plt", "platelets",
    "mcv", "mch", "mchc",
    "hematocrit", "haematocrit", "hct",
    "rdw", "red cell distribution width",
    "mpv", "mean platelet volume",
    "neutrophils", "lymphocytes", "monocytes", "eosinophil", "basophil",
# Common section headers
    "hematology", "haematology",
# Metabolic
    "glucose", "creatinine", "urea", "bun",
    "alt", "ast", "alp", "bilirubin",
    "cholesterol", "triglycerides",
    "tsh", "t3", "t4",
    "hba1c", "a1c",
    "esr", "crp",
]

def is_medical_report(text: str) -> bool:
    """Check if text contains medical lab report markers."""
    t = text.lower()
    for marker in _MEDICAL_MARKERS:
        if re.search(r'\b' + re.escape(marker) + r's?\b', t):
            return True
    return False


def _age_group(age: int) -> str:
    if age < 13:
        return "child"
    if age < 18:
        return "teen"
    if age < 60:
        return "adult"
    return "elderly"


def _is_garbage_metadata(text: str) -> bool:
    """Detect if a string is likely OCR metadata/garbage rather than a test name."""
    t = text.lower().strip()
    if len(t) < 2 or len(t) > 60: return True

# Metadata markers and OCR garbage blacklist
    markers = [
        r"\bpathology\b", r"\bclinic\b", r"\blab\b", r"\bdr\.\b", r"\bdoctor\b",
        r"\bregistration\b", r"\bpatient\b", r"\bdate\b", r"\buhid\b", r"\bref\b",
        r"\breport\b", r"\bsample\b", r"\bcollection\b", r"\bprinted\b",
        r"\bauthorized\b", r"\bspecimen\b", r"\bphone\b", r"\bmobile\b",
        r"\bnagar\b", r"\broad\b", r"\bstreet\b", r"\bcolony\b", r"\bhospital\b",
        r"\bdiagnostics?\b", r"\bcentre\b", r"\bcenter\b", r"\bbarcode\b",
        r"\binvestigation\b", r"\bhistory\b",
# Explicit blacklist
        r"^anne$", r"^name$", r"^age$", r"^sex$", r"^date$", r"^report$", r"^test$", r"^lab$", r"^sample$",
        r"^page$", r"^result$", r"^range$", r"^unit$", r"^panel$",
    ]
    for m in markers:
        if re.search(m, t):
            logger.info("[pipeline] garbage_metadata marker match: %r matched %r", text, m)
            return True

# If it contains too many non-alphanumeric chars (besides common ones like % / . -)
    garbage_chars = re.sub(r"[a-z0-9%/\.\-\s\(\)]", "", t)
    if len(garbage_chars) > len(t) * 0.2: return True

    return False


def _get_unit_multiplier(unit: str) -> float:
    u = normalize_unit(unit)
    m = re.search(r"x10\^(\d+)", u)
    return 10 ** int(m.group(1)) if m else 1.0


def _normalize_count_units(value: float, value_unit: str, ref_unit: str) -> float:
    vu = normalize_unit(value_unit)
    ru = normalize_unit(ref_unit)
    if not vu or not ru or vu == ru:
        return value
    if "/L" not in vu and "/µL" not in vu:
        return value
    if "/L" not in ru and "/µL" not in ru:
        return value
    vm = _get_unit_multiplier(vu)
    rm = _get_unit_multiplier(ru)
    if vm == rm:
        return value
    return value * (vm / rm)


def _classify_against_parsed_range(value: float, parsed_range) -> str:
    if parsed_range.low is not None and parsed_range.high is not None:
        return classify_numeric(value, parsed_range.low, parsed_range.high)
    if parsed_range.low is not None:
        return "low" if value < parsed_range.low else "normal"
    if parsed_range.high is not None:
        return "high" if value > parsed_range.high else "normal"
    return "unknown"


def process_lab_report(
    raw_text: str,
    gender: str = "male",
    age: int = 30,
) -> tuple[list[ResolvedTest], CompletenessTracker]:
    """Complete pipeline: raw text → ResolvedTest list"""
    tracker = CompletenessTracker()

    if not raw_text or not raw_text.strip():
        logger.warning("[pipeline] empty input text")
        return [], tracker

# OCR repair pass
    raw_text = repair_ocr_text(raw_text)

# Medical document validation
    if not is_medical_report(raw_text):
        logger.warning("[pipeline] REJECT non-medical text (no medical markers found)")
        tracker.total_parsed = 0
        return [], tracker

# STAGE 1: PARSE
    parsed_dicts = parse_lab_report(raw_text)
    tracker.total_parsed = len(parsed_dicts)
    logger.info("[pipeline] PARSE: extracted %d tests", tracker.total_parsed)

    if tracker.total_parsed == 0:
        return [], tracker

# Convert to ParsedTest objects (validates schema)
    parsed_tests: list[ParsedTest] = []
    for item in parsed_dicts:
        try:
            pt = ParsedTest(
                test_name=item.get("test_name", "").strip(),
                value=float(item.get("value", 0.0)),
                unit=item.get("unit", ""),
                raw_unit=item.get("raw_unit", ""),
                reference_range=item.get("reference_range", ""),
            )
            parsed_tests.append(pt)
        except ValueError as exc:
            logger.error("[pipeline] PARSE validation failed: %s (item=%s)", exc, item)
            tracker.dropped += 1
            continue

    for test in parsed_tests:
        logger.info(
            "[PARSED] name=%s value=%s unit=%s range=%s",
            test.test_name, test.value, test.unit, test.reference_range,
        )

# STAGE 2–5: RESOLVE + CLASSIFY + BUILD OUTPUT
    ag = _age_group(age)

# De-duplication map: (test_key, normalized_unit) -> ResolvedTest
    dedup_results: Dict[tuple, ResolvedTest] = {}
    unknown_range_cache: Dict[str, ReferenceRange] = {}

# Audit tracking — every parsed test must end in exactly one category
    dropped_with_reason: list[dict] = []
    outcome_per_test: list[dict] = []  # tracks (name, outcome) for every parsed test

    for parsed in parsed_tests:
        raw_name = parsed.test_name
        normalized_name = normalize_test_name(raw_name) or raw_name.strip().lower()
        reported_unit = parsed.unit
        raw_unit = parsed.raw_unit
        value_reported = parsed.value
        confidence = 1.0
        match_type: str = "none"
        test_key: Optional[str] = None
        status = "unknown"
        reference_range: Optional[ReferenceRange] = None

        logger.info("[pipeline] NORMALIZED: %r -> %r (value=%s)", raw_name, normalized_name, value_reported)

# STAGE 2: RESOLVE
        test_key, resolve_confidence = resolve_test_key_with_confidence(raw_name)
        confidence = resolve_confidence

        if confidence >= 0.82:
            match_type = "alias"
        elif confidence >= 0.65:
            match_type = "fuzzy"
        else:
            match_type = "none"
            test_key = None
            confidence = 0.0

# RDW Unit-Aware Switch: If resolved as RDW but unit is fL, switch to RDW-SD
        if test_key == "rdw" and normalize_unit(reported_unit) == "fL":
            logger.info("[pipeline] RDW UNIT-AWARE: switching rdw -> rdw_sd based on fL unit")
            test_key = "rdw_sd"
            confidence = max(confidence, 0.85)

# FILTER: Discard entries with confidence < 0.30 only when a partial match was found
# (match_type != "none" means the resolver tried and got a low score — probably noise)
        if confidence < 0.30 and match_type != "none":
             logger.info("[pipeline] DROPPED: %r (low confidence %.2f)", raw_name, confidence)
             dropped_with_reason.append({"name": raw_name, "reason": f"low confidence ({confidence:.2f})"})
             tracker.dropped += 1
             outcome_per_test.append({"name": raw_name, "outcome": "dropped", "reason": "low confidence"})
             continue

# FILTER: If unresolved, check if it's metadata garbage — if so, skip entirely.
# Otherwise: KEEP the test in the output as status=unknown instead of dropping it.
        if not test_key:
            if _is_garbage_metadata(raw_name):
                logger.info("[pipeline] FILTERED garbage: %r", raw_name)
                tracker.garbage_filtered += 1
                outcome_per_test.append({"name": raw_name, "outcome": "garbage_filtered"})
                continue

# PRESERVE unresolved tests
# Do NOT drop — include in output with status=unknown so the user
# can see all parsed results. This was the primary cause of missing results.
            logger.info("[pipeline] UNRESOLVED (keeping as unknown): %r", raw_name)
            outcome_per_test.append({"name": raw_name, "outcome": "resolved"})
            res_obj = ResolvedTest(
                test_name=raw_name,
                resolved_key=None,
                value=value_reported,
                unit=reported_unit,
                status="unknown",
                reference_range=None,
                confidence=0.0,
                match_type="none",
                explanation="Test name could not be resolved to a known lab test.",
                clinical_insight=None,
                test_category="",
                applicable_patterns=[],
            )
# Use raw name as dedup key so each unresolved test appears once
            dedup_key = (raw_name.lower(), normalize_unit(reported_unit))
            if dedup_key not in dedup_results:
                dedup_results[dedup_key] = res_obj
            continue

        logger.info("[pipeline] RESOLVED: %r -> %s (conf=%.2f)", raw_name, test_key, confidence)
        outcome_per_test.append({"name": raw_name, "outcome": "resolved"})

# STAGE 2b: UNIT-BASED DISAMBIGUATION
# If resolved test name conflicts with reported unit, reject and re-resolve.
        if test_key and reported_unit:
            td_check = get_test_definition(test_key)
            if td_check:
                canonical = normalize_unit(td_check.canonical_unit)
                reported = normalize_unit(reported_unit)
                if canonical and reported and canonical != reported:
# For "hb"/"hemoglobin" with "%" → re-route to hba1c
# For "hba1c" with "g/dL" → re-route to hemoglobin
                    if test_key == "hemoglobin" and reported == "%":
                        alt_key = "hba1c"
                        alt_td = get_test_definition(alt_key)
                        if alt_td and normalize_unit(alt_td.canonical_unit) == reported:
                            logger.info("[pipeline] UNIT-DISAMBIG: %r → switching hemoglobin→hba1c (unit=%s)", raw_name, reported)
                            test_key = alt_key
                            confidence = max(confidence, 0.85)
                    elif test_key == "hba1c" and reported in ("g/dL", "mg/dL"):
                        alt_key = "hemoglobin"
                        alt_td = get_test_definition(alt_key)
                        if alt_td and normalize_unit(alt_td.canonical_unit) == reported:
                            logger.info("[pipeline] UNIT-DISAMBIG: %r → switching hba1c→hemoglobin (unit=%s)", raw_name, reported)
                            test_key = alt_key
                            confidence = max(confidence, 0.85)
# General pct/abs disambiguation
                    elif test_key.endswith("_pct") and reported != "%":
                        alt_key = test_key.removesuffix("_pct") + "_abs"
                        alt_td = get_test_definition(alt_key)
                        if alt_td and normalize_unit(alt_td.canonical_unit) == reported:
                            logger.info("[pipeline] UNIT-DISAMBIG: %r → switching %s→%s (unit=%s)", raw_name, test_key, alt_key, reported)
                            test_key = alt_key
                            confidence = max(confidence, 0.85)
                    elif test_key.endswith("_abs") and reported == "%":
                        alt_key = test_key.removesuffix("_abs") + "_pct"
                        alt_td = get_test_definition(alt_key)
                        if alt_td and normalize_unit(alt_td.canonical_unit) == reported:
                            logger.info("[pipeline] UNIT-DISAMBIG: %r → switching %s→%s (unit=%s)", raw_name, test_key, alt_key, reported)
                            test_key = alt_key
                            confidence = max(confidence, 0.85)

# STAGE 3: LOOKUP REFERENCE
        td = get_test_definition(test_key)
        rr = get_reference_range(test_key, gender, ag)

# Try to use any explicit reference range from the parsed OCR row.
        if not rr and parsed.reference_range:
            parsed_range = parse_reference_range(parsed.reference_range, default_unit=td.canonical_unit if td else "")
            if parsed_range.low is not None or parsed_range.high is not None:
                rr = ReferenceRange(
                    low=parsed_range.low,
                    high=parsed_range.high,
                    unit=parsed_range.unit or (td.canonical_unit if td else ""),
                )
                logger.debug(
                    "[pipeline] used parsed reference range for %s: %s",
                    test_key,
                    parsed.reference_range,
                )

# Fallback to defaults if no range found
        if test_key and not rr and test_key in DEFAULT_RANGES:
            fb_lo, fb_hi, fb_unit = DEFAULT_RANGES[test_key]
            rr_obj = type('RR', (), {
                'low': fb_lo,
                'high': fb_hi,
                'unit': fb_unit,
                'description': 'Fallback default'
            })()
            rr = rr_obj
            confidence = min(confidence, 0.80)

        if not rr:
            category = TEST_KEY_TO_CATEGORY.get(test_key, "")
            patterns = get_patterns_for_test(test_key)
            res_obj = ResolvedTest(
                test_name=td.display_name if td else raw_name,
                resolved_key=test_key,
                value=value_reported,
                unit=reported_unit,
                status="unknown",
                reference_range=None,
                confidence=confidence,
                match_type=match_type,
                explanation="Test recognized but no reference range available.",
                clinical_insight=None,
                test_category=category,
                applicable_patterns=patterns,
            )
            dedup_results[(test_key, normalize_unit(reported_unit))] = res_obj
            continue

# STAGE 3b: OCR VALUE ERROR CORRECTION
        fixed_value, fixed_unit, was_corrected = fix_ocr_value_errors(
            value_reported, reported_unit, test_key,
            ref_low=rr.low if rr else None,
            ref_high=rr.high if rr else None,
        )
        if was_corrected:
            logger.warning(
                "[pipeline] OCR corrected: %r %r → %s %s",
                raw_name, reported_unit, fixed_value, fixed_unit,
            )
            value_reported = fixed_value
            reported_unit = fixed_unit

# STAGE 4: NORMALIZE + SANITY CHECK
        original_value = value_reported
        value_for_classification = value_reported

# Unit conversion and fallback
        final_unit = reported_unit

# Note: corrupt units are already repaired by normalize_unit();
# applying an additional penalty here would double-punish repaired values.
# No extra penalty for OCR-mangled units that have been corrected.

        if not final_unit and rr and rr.unit:
            final_unit = rr.unit
            confidence = max(0.0, confidence - 0.15) # Penalty for missing unit
            logger.debug("[pipeline] missing unit, assuming canonical: %r", final_unit)

        if final_unit and rr and rr.unit and final_unit != rr.unit:
            converted = convert_value(
                value_for_classification,
                from_unit=final_unit,
                to_unit=rr.unit,
                test_key=test_key
            )
            if converted is not None:
                value_for_classification = converted
                value_reported = converted
                final_unit = rr.unit
                logger.debug("[pipeline] CONVERTED: to %s %r (test=%s)", value_reported, final_unit, test_key)

# Universal count-unit normalization: belt-and-suspenders for /µL ↔ x10^N/µL
        if rr and rr.unit:
            normalized_val = _normalize_count_units(value_for_classification, final_unit, rr.unit)
            if normalized_val != value_for_classification:
                value_for_classification = normalized_val
                value_reported = normalized_val
                final_unit = rr.unit
                logger.debug("[pipeline] COUNT-NORM: %s %r → %s %r", value_for_classification, final_unit, normalized_val, rr.unit)

        value_norm = value_for_classification

# Sanity check should happen AFTER unit conversion so it uses canonical scale
        sr = sanity_check_value(
            value_for_classification,
            test_key,
            final_unit,
            ref_low=rr.low if rr else None,
            ref_high=rr.high if rr else None,
        )

# sr.repaired is always False now per P0 safety fix
# but we still apply confidence penalty if value is suspicious
        confidence = max(0.0, confidence - sr.confidence_penalty)
        if sr.confidence_penalty > 0:
            logger.warning("[pipeline] suspicious value detected: %s", sr.warning)

# STAGE 5: CLASSIFY
        status = "unknown"  # default if we can't classify
        try:
# Ensure we have valid bounds before calling classify_numeric
            if rr and rr.low is not None and rr.high is not None:
                status = classify_numeric(value_for_classification, rr.low, rr.high)
            elif rr and (rr.low is not None or rr.high is not None):
# One-sided range (only low or only high)
                if rr.low is not None:
                    status = "low" if value_for_classification < rr.low else "normal"
                elif rr.high is not None:
                    status = "high" if value_for_classification > rr.high else "normal"
            else:
# No range available at all
                logger.debug("[pipeline] no reference range for %s — status=unknown", test_key)
                status = "unknown"
        except Exception as exc:
            logger.error("[pipeline] CLASSIFY failed: %s", exc)
            status = "unknown"
            confidence = max(0.0, confidence - 0.2)

# Medical Safety: downgrade status if confidence is truly garbage-level
# Graded approach: only block when confidence is very low.
# If classification succeeded (not unknown), allow slightly lower confidence
# since the numeric result is still clinically valid.
        if status != "unknown":
            if confidence < 0.15:
                status = "REVIEW_REQUIRED"
                logger.warning("[pipeline] extremely low confidence (%.2f) for %r, status=REVIEW_REQUIRED", confidence, test_key)
        else:
            if confidence < 0.30:
                status = "REVIEW_REQUIRED"
                logger.warning("[pipeline] low confidence (%.2f) with unknown status for %r, status=REVIEW_REQUIRED", confidence, test_key)

        reference_range = ReferenceRange(low=rr.low, high=rr.high, unit=rr.unit)
        category = TEST_KEY_TO_CATEGORY.get(test_key, "")
        patterns = get_patterns_for_test(test_key)

        res_obj = ResolvedTest(
            test_name=td.display_name if td else raw_name, # ALWAYS use canonical display name
            resolved_key=test_key,
            value=value_reported,
            unit=final_unit,
            status=status,
            reference_range=reference_range,
            confidence=round(confidence, 2),
            match_type=match_type,
            explanation=None,
            clinical_insight=None,
            test_category=category,
            applicable_patterns=patterns,
        )

# Deduplication — use (key, normalized_unit) as composite key
# so pct (% NEUT) and abs (#NEUT) resolve to separate entries
        dedup_key = (test_key, normalize_unit(final_unit))
        if dedup_key in dedup_results:
            existing = dedup_results[dedup_key]
            if confidence > existing.confidence:
                dedup_results[dedup_key] = res_obj
        else:
            dedup_results[dedup_key] = res_obj

# FINALIZATION
    resolved_tests = list(dedup_results.values())

# Count outcomes directly from parsed tests, not from dedup map
# (dedup may silently drop duplicate keys — we track those below)
    outcome_resolved = sum(1 for o in outcome_per_test if o["outcome"] == "resolved")
    outcome_garbage = sum(1 for o in outcome_per_test if o["outcome"] == "garbage_filtered")
    outcome_dropped = sum(1 for o in outcome_per_test if o["outcome"] == "dropped")

# Set tracker counters based on tracked outcomes
    tracker.resolved = len(resolved_tests)
    tracker.unresolved = 0
    tracker.review_required = 0

# Count dedup losses (tests that resolved to the same key — these are not lost,
# they were merged. But for the count invariant we need to account for them.)
    dedup_surplus = outcome_resolved - len(resolved_tests)
    if dedup_surplus > 0:
        logger.info("[pipeline] %d parsed tests merged via deduplication", dedup_surplus)

    logger.info("[pipeline] FINAL_OUTPUT: %d tests delivered", len(resolved_tests))
    for t in resolved_tests:
        logger.info("  - %s (key=%s, status=%s, confidence=%.2f)", t.test_name, t.resolved_key, t.status, t.confidence)

# Summary log for auditing — invariant: parsed = resolved + garbage + dropped
# (dedup_surplus is part of resolved count in the tracker)
    logger.info(
        "[pipeline] SUMMARY: %d PARSED, %d RESOLVED, %d GARBAGE_FILTERED, %d DROPPED, %d FINAL_OUTPUT (dedup_merged=%d)",
        tracker.total_parsed, outcome_resolved, outcome_garbage, outcome_dropped,
        len(resolved_tests), dedup_surplus,
    )

# Verify count invariant
    actual_sum = outcome_resolved + outcome_garbage + outcome_dropped
    if actual_sum != tracker.total_parsed:
        logger.error(
            "[pipeline] COUNT MISMATCH: sum=%d (resolved=%d + garbage=%d + dropped=%d), expected=%d",
            actual_sum, outcome_resolved, outcome_garbage, outcome_dropped, tracker.total_parsed,
        )
# Log exactly which tests were lost
        accounted = {o["name"] for o in outcome_per_test}
        for item in parsed_tests:
            if item.test_name not in accounted:
                logger.error("[pipeline] UNACCOUNTED test: %r", item.test_name)

    if outcome_dropped > 0:
        logger.info("[pipeline] processing complete: %d tests dropped based on filtering rules", outcome_dropped)
        for d in dropped_with_reason:
            logger.debug("  - %s: %s", d['name'], d['reason'])
        logger.info("[completeness] dropped tests: %s", [d['name'] for d in dropped_with_reason])

    return resolved_tests, tracker
