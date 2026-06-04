#!/usr/bin/env python3
"""Test the grouped insights function."""
import sys
sys.path.insert(0, '/home/dell/Desktop/test')

from services.insights_service import LabResult, generate_grouped_insights

results = [
    LabResult(test_key="hemoglobin", test_name="Hemoglobin", status="low", value=9.5, unit="g/dL"),
    LabResult(test_key="rbc", test_name="RBC", status="low", value=3.2, unit="/µL"),
    LabResult(test_key="mcv", test_name="MCV", status="low", value=72, unit="fL"),
    LabResult(test_key="glucose_fasting", test_name="Glucose", status="high", value=145, unit="mg/dL"),
    LabResult(test_key="ldl", test_name="LDL", status="high", value=160, unit="mg/dL"),
    LabResult(test_key="wbc", test_name="WBC", status="normal", value=7.5, unit="/µL"),
]

print("Testing generate_grouped_insights...")
try:
    insights = generate_grouped_insights(results)
    print(f"✓ Generated insights successfully!")
    print(f"\nGrouped by category:")
    for category, flags in insights.get("by_category", {}).items():
        print(f"  {category}:")
        for flag in flags:
            print(f"    - {flag}")
    print(f"\nPatterns detected: {len(insights.get('patterns', []))}")
except Exception as exc:
    print(f"✗ Failed: {exc}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
