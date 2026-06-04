#!/usr/bin/env python3
"""Quick test of the production pipeline."""
import sys
sys.path.insert(0, '/home/dell/Desktop/test')

from core.pipeline import process_lab_report

test_text = """
WBC: 7.5 x10^3/uL
RBC: 4.2 million/uL
Hemoglobin: 12.5 g/dL
Platelets: 250k/uL
Glucose: 105 mg/dL
Creatinine: 0.9 mg/dL
"""

print("Testing pipeline with sample report...")
try:
    resolved, tracker = process_lab_report(test_text, gender="female", age=35)
    print(f"\n✓ Pipeline completed successfully!")
    print(f"  Tracker: {tracker.to_dict()}")
    print(f"  Output count: {len(resolved)} tests")
    print(f"\nResolved tests:")
    for test in resolved[:3]:
        print(f"  - {test.test_name}: {test.value} {test.unit} → {test.status} (conf={test.confidence})")
except Exception as exc:
    print(f"✗ Pipeline failed: {exc}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
