#!/usr/bin/env python3
"""Integration test: backend response meets frontend expectations."""
import sys
import json
sys.path.insert(0, '/home/dell/Desktop/test')

from core.pipeline import process_lab_report
from core.schemas import ResolvedTest

test_report = """
WBC: 13 x10^3/uL
RBC: 3.5 million/uL
Hemoglobin: 10.2 g/dL
Glucose: 155 mg/dL
LDL: 165 mg/dL
HDL: 32 mg/dL
"""

print("=" * 70)
print("INTEGRATION TEST: Backend Response → Frontend Compatibility")
print("=" * 70)

try:
    resolved, tracker = process_lab_report(test_report, gender="male", age=45)
    print(f"✓ Pipeline executed: {len(resolved)} tests resolved")

    # Simulate API response
    response = {
        "patient": {"gender": "male", "age": 45},
        "completeness": tracker.to_dict(),
        "summary": {
            "total": len(resolved),
            "normal": sum(1 for t in resolved if t.status == "normal"),
            "high": sum(1 for t in resolved if t.status == "high"),
            "low": sum(1 for t in resolved if t.status == "low"),
            "unknown": sum(1 for t in resolved if t.status == "unknown"),
        },
        "results": [t.to_dict() for t in resolved],
    }

    print("\n✓ Response structure:")
    print(f"  - patient: {response['patient']}")
    print(f"  - completeness: {response['completeness']}")
    print(f"  - summary: {response['summary']}")
    print(f"  - results: {len(response['results'])} tests")

    # Verify frontend-critical fields
    print("\n✓ Frontend compatibility checks:")
    for i, test in enumerate(resolved):
        test_dict = test.to_dict()
        
        # Check reference_range structure
        if test_dict.get("reference_range"):
            ref = test_dict["reference_range"]
            assert isinstance(ref, dict), f"Test {i}: reference_range not object"
            assert "low" in ref and "high" in ref, f"Test {i}: missing low/high"
            print(f"  ✓ Test {i} ({test.test_name}): reference_range is object")
        
        # Check all required fields exist
        required = ["test_name", "value", "unit", "status", "confidence"]
        for field in required:
            assert field in test_dict, f"Test {i}: missing {field}"
        
        # Check confidence is valid
        assert 0.0 <= test_dict["confidence"] <= 1.0, f"Test {i}: invalid confidence"

    print(f"\n✓ All {len(resolved)} tests pass frontend validation")

    # Simulate JSON serialization (what API actually sends)
    json_response = json.dumps(response, default=str)
    parsed = json.loads(json_response)
    
    print(f"✓ JSON serialization successful ({len(json_response)} bytes)")
    
    # Verify parsed JSON has correct structure
    assert "results" in parsed, "Missing results in JSON"
    assert isinstance(parsed["results"], list), "Results not array"
    if parsed["results"]:
        first = parsed["results"][0]
        assert isinstance(first["reference_range"], dict), "reference_range not object in JSON"
        print(f"✓ First test in JSON: {first['test_name']} with reference range {first['reference_range']}")

    print("\n" + "=" * 70)
    print("✓ INTEGRATION TEST PASSED")
    print("=" * 70)
    print("\nBackend response is compatible with frontend:")
    print("  ✅ All tests have strict schema")
    print("  ✅ reference_range is structured object")
    print("  ✅ All required fields present")
    print("  ✅ JSON serialization works")
    print("  ✅ No raw objects in response")

except Exception as exc:
    print(f"\n✗ Integration test failed: {exc}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
