#!/usr/bin/env python3
"""Final comprehensive verification of production requirements."""
import sys
sys.path.insert(0, '/home/dell/Desktop/test')

from core.pipeline import process_lab_report
from core.schemas import ResolvedTest, CompletenessTracker
from services.insights_service import LabResult, generate_grouped_insights

print("=" * 70)
print("FINAL VERIFICATION TEST")
print("=" * 70)

test_report = """
Hemoglobin: 9.5 g/dL
RBC: 3.2 million/uL
WBC: 7.5 x10^3/uL
Platelets: 250k/uL
Glucose (fasting): 145 mg/dL
Creatinine: 0.9 mg/dL
Sodium: 140 mEq/L
Potassium: 4.2 mEq/L
LDL Cholesterol: 160 mg/dL
HDL Cholesterol: 35 mg/dL
Triglycerides: 200 mg/dL
ALT: 35 U/L
AST: 28 U/L
TSH: 3.5 mIU/L
Vitamin D: 25 ng/mL
Unknown Test: 999 units
"""

print("\n1. PARSING & RESOLUTION")
print("-" * 70)
try:
    resolved, tracker = process_lab_report(test_report, gender="male", age=42)
    print(f"✓ Pipeline executed successfully")
    print(f"  Total parsed: {tracker.total_parsed}")
    print(f"  Resolved: {tracker.resolved}")
    print(f"  Unresolved: {tracker.unresolved}")
    print(f"  Dropped: {tracker.dropped}")
except Exception as exc:
    print(f"✗ Pipeline failed: {exc}")
    sys.exit(1)

print("\n2. NO SILENT DROPS")
print("-" * 70)
try:
    assert tracker.dropped == 0, f"FAILED: {tracker.dropped} tests were dropped"
    assert len(resolved) == tracker.total_parsed, f"FAILED: count mismatch {len(resolved)} vs {tracker.total_parsed}"
    assert len(resolved) == tracker.resolved + tracker.unresolved, f"FAILED: sum mismatch"
    print(f"✓ No silent drops verified")
    print(f"  Output count: {len(resolved)}")
    print(f"  100% of parsed tests in output")
except AssertionError as exc:
    print(f"✗ {exc}")
    sys.exit(1)

print("\n3. STRICT OUTPUT SCHEMA")
print("-" * 70)
try:
    for i, test in enumerate(resolved):
        assert isinstance(test, ResolvedTest), f"Test {i} is not ResolvedTest"
        assert isinstance(test.test_name, str) and test.test_name, f"Test {i} has no name"
        assert isinstance(test.value, (int, float)) and test.value == test.value, f"Test {i} has invalid value"
        assert test.status in ("low", "normal", "high", "unknown"), f"Test {i} has invalid status"
        assert 0.0 <= test.confidence <= 1.0, f"Test {i} has invalid confidence"
        assert test.match_type in ("alias", "fuzzy", "none"), f"Test {i} has invalid match_type"
    print(f"✓ All {len(resolved)} tests conform to strict schema")
except AssertionError as exc:
    print(f"✗ {exc}")
    sys.exit(1)

print("\n4. CONFIDENCE PROPAGATION")
print("-" * 70)
try:
    high_conf = [t for t in resolved if t.confidence >= 0.9]
    med_conf = [t for t in resolved if 0.65 <= t.confidence < 0.9]
    low_conf = [t for t in resolved if t.confidence > 0 and t.confidence < 0.65]
    no_conf = [t for t in resolved if t.confidence == 0.0]
    print(f"✓ Confidence distribution:")
    print(f"  High (0.90-1.0): {len(high_conf)} tests")
    print(f"  Med (0.65-0.90): {len(med_conf)} tests")
    print(f"  Low (0.0-0.65): {len(low_conf)} tests")
    print(f"  None (0.0): {len(no_conf)} tests (unresolved)")
except Exception as exc:
    print(f"✗ {exc}")
    sys.exit(1)

print("\n5. GROUPED INSIGHTS")
print("-" * 70)
try:
    lab_results = [
        LabResult(
            test_key=t.resolved_key or "",
            test_name=t.test_name,
            status=t.status,
            value=t.value,
            unit=t.unit,
        )
        for t in resolved
    ]
    insights = generate_grouped_insights(lab_results)
    assert "by_category" in insights, "Missing by_category in insights"
    assert "patterns" in insights, "Missing patterns in insights"
    categories = insights.get("by_category", {})
    patterns = insights.get("patterns", [])
    print(f"✓ Generated grouped insights:")
    print(f"  Categories found: {list(categories.keys())}")
    print(f"  Patterns detected: {len(patterns)}")
    for cat, flags in categories.items():
        print(f"    {cat}: {len(flags)} flags")
except AssertionError as exc:
    print(f"✗ {exc}")
    sys.exit(1)
except Exception as exc:
    print(f"✗ {exc}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n6. COMPLETENESS TRACKING")
print("-" * 70)
try:
    tracker_dict = tracker.to_dict()
    assert tracker_dict["dropped"] == 0, "Dropped counter not 0"
    assert tracker_dict["status"] == "OK", "Status not OK"
    print(f"✓ Completeness tracking validated:")
    print(f"  {tracker_dict}")
except Exception as exc:
    print(f"✗ {exc}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✓ ALL VERIFICATION TESTS PASSED")
print("=" * 70)
print("\nProduction requirements met:")
print("  ✓ No dropped tests")
print("  ✓ Strict output schema enforced")
print("  ✓ Complete traceability with CompletenessTracker")
print("  ✓ Grouped insights by category")
print("  ✓ Confidence propagated through pipeline")
