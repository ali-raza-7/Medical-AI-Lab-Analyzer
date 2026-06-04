"""
Lightweight runtime checks without pytest dependency.

Run:
  ./myenv/bin/python smoke_test.py
"""

from core.parser import parse_lab_report
from core.normalization import normalize_count_to_per_uL, normalize_unit
from core.classifier import classify_numeric
from medical.reference_db import get_reference_range, get_test_definition
from core.resolver import resolve_test_key


def status_for(line: str, gender: str = "male", age_group: str = "adult") -> str:
    parsed = parse_lab_report(line)
    if not parsed:
        raise AssertionError(f"failed to parse: {line!r}")
    it = parsed[0]
    key = resolve_test_key(it["test_name"])
    if not key:
        return "unknown"
    td = get_test_definition(key)
    rr = get_reference_range(key, gender, age_group)
    assert td and rr, f"Missing definition/range for key={key!r}"

    val = it["value"]
    u = normalize_unit(it.get("unit", ""))

    if td.canonical_unit == "/µL":
        nm = normalize_count_to_per_uL(val, u)
        assert nm is not None, f"Could not normalize count unit: {u!r}"
        val = nm.value

    return classify_numeric(val, rr.low, rr.high)


def main() -> None:
    # ── Phase 6.1: Original must-pass tests ─────────────────────────────────
    assert status_for("WBC Count 7.5 x10^3/uL") == "normal",   "WBC 7.5 should be normal"
    assert status_for("Platelet Count 250 x10^3/uL") == "normal", "Platelet 250 should be normal"
    assert status_for("RBC Count 4.8 x10^6/uL") == "normal",   "RBC 4.8 should be normal"
    assert status_for("Glucose 92 mg/dL") == "normal",          "Glucose 92 should be normal"
    assert status_for("Creatinine 1.6 mg/dL") == "high",        "Creatinine 1.6 should be high"

    # ── Phase 6.2: New test cases ────────────────────────────────────────────
    assert status_for("Hemoglobin 9.5 g/dL", gender="male") == "low",    "Hb 9.5 male should be low"
    assert status_for("Hemoglobin 13.5 g/dL", gender="female") == "normal", "Hb 13.5 female should be normal"
    assert status_for("TSH 8.5 mIU/L") == "high",                        "TSH 8.5 should be high"
    assert status_for("Vitamin D 15 ng/mL") == "low",                    "Vit D 15 should be low"
    assert status_for("HbA1c 7.2 %") == "high",                          "HbA1c 7.2 should be high"
    assert status_for("Platelet Count 98 x10^3/uL") == "low",            "Platelet 98 should be low"
    assert status_for("WBC Count 15.9 x10^3/uL") == "high",              "WBC 15.9 should be high"

    print("smoke_test: ALL PASSED ✓")


if __name__ == "__main__":
    main()
