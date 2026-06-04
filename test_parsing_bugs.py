#!/usr/bin/env python3
"""Test parsing bugs on real multi-column blood test reports."""
import sys
sys.path.insert(0, '/home/dell/Desktop/test')

from core.parser import parse_lab_report

# Real multi-column blood test report format
REAL_REPORT = """
BLOOD CHEMISTRY REPORT

Patient: John Doe
Age: 45 years, Male
Date: 22-05-2026

TEST NAME                      RESULT    UNITS              REFERENCE RANGE
===================================================================
Hemoglobin                     13.2      g/dL               13.5 - 17.5
Total Leukocyte Count          5.8       x10^3/µL           4.5 - 11.0
RBC Count                      4.1       x10^6/µL           4.5 - 5.5
Hematocrit                     39.2      %                  40 - 54
Packed Cell Volume             39.2      aid                40 - 54
MCV                            87.7      fL                 83 - 101
MCH                            32.1      pg                 27 - 33
MCHC                           33.5      g/dL               32 - 36
Platelets                      245       x10^3/µL           150 - 450
Neutrophils                    56        %                  40 - 75
Absolute Neutrophil Count      3.41      x10^3/µL           2.0 - 7.5
Lymphocytes                    32        %                  20 - 40
Absolute Lymphocyte Count      1.85      x10^3/µL           1.0 - 4.8
Monocytes                      8         %                  2 - 8
Eosinophils                    3         %                  1 - 4
Basophils                      1         %                  0 - 1
RDW-CV                         13.2      %                  11.5 - 14.5
Glucose (Fasting)              98        mg/dL              70 - 100
Urea                           32        mg/dL              15 - 45
Creatinine                     0.95      mg/dL              0.7 - 1.3
Sodium                         138       mmol/L             136 - 145
Potassium                      4.2       mmol/L             3.5 - 5.0
Chloride                       102       mmol/L             98 - 107
CO2 (Bicarbonate)              24        mmol/L             22 - 29
Total Protein                  7.2       g/dL               6.0 - 8.3
Albumin                        4.1       g/dL               3.5 - 5.0
Globulin                       3.1       g/dL               2.3 - 3.5
A/G Ratio                      1.3       ratio              1.0 - 2.5
Total Bilirubin                0.8       mg/dL              0.1 - 1.2
Direct Bilirubin               0.2       mg/dL              0.0 - 0.3
Indirect Bilirubin             0.6       mg/dL              0.1 - 0.9
AST (SGOT)                     28        U/L                10 - 40
ALT (SGPT)                     32        U/L                10 - 40
ALP (Alkaline Phosphatase)     72        U/L                40 - 130
GGT                            25        U/L                10 - 50
Total Cholesterol              185       mg/dL              < 200
HDL Cholesterol                45        mg/dL              > 40
LDL Cholesterol                120       mg/dL              < 130
Triglycerides                  145       mg/dL              < 150
Calcium                        9.2       mg/dL              8.5 - 10.5
Phosphorus                     3.5       mg/dL              2.5 - 4.5
Magnesium                      2.1       mg/dL              1.7 - 2.2
TSH                            2.5       mIU/L              0.4 - 4.0
Free T4                        1.1       ng/dL              0.8 - 1.8
Vitamin B12                    450       pg/mL              200 - 900
Folate                         8.5       ng/mL              5.4 - 16.0
Iron                           85        µg/dL              60 - 170
Total Iron Binding Capacity    320       µg/dL              250 - 400
Ferritin                       150       ng/mL              30 - 300

eT ss ecomt oa jaocoue
garbage noise line with no real words

Total Tests: 45
Abnormal: 1 (Hemoglobin low)
"""

def test_parsing():
    print("=" * 80)
    print("TESTING REAL MULTI-COLUMN BLOOD TEST REPORT PARSING")
    print("=" * 80)
    
    results = parse_lab_report(REAL_REPORT)
    
    print(f"\n✓ Parsed {len(results)} tests\n")
    
    # Expected tests (from the report)
    expected = {
        "Hemoglobin": (13.2, "g/dL", "13.5 - 17.5"),
        "Total Leukocyte Count": (5.8, "x10^3/µL", "4.5 - 11.0"),
        "RBC Count": (4.1, "x10^6/µL", "4.5 - 5.5"),
        "Hematocrit": (39.2, "%", "40 - 54"),
        "Packed Cell Volume": (39.2, "g/dL", "40 - 54"),  # "aid" should be converted to "g/dL"
        "MCV": (87.7, "fL", "83 - 101"),
        "Absolute Neutrophil Count": (3.41, "x10^3/µL", "2.0 - 7.5"),
        "Monocytes": (8, "%", "2 - 8"),
        "Eosinophils": (3, "%", "1 - 4"),
        "RDW-CV": (13.2, "%", "11.5 - 14.5"),
    }
    
    # Check for parsing issues
    print("PARSING ISSUES FOUND:\n")
    
    # 1. Check for garbage lines parsed as tests
    garbage_found = False
    for result in results:
        if "eT ss ecomt" in result.get("test_name", ""):
            print(f"  ✗ GARBAGE LINE PARSED: {result['test_name']}")
            garbage_found = True
    
    if not garbage_found:
        print("  ✓ No garbage lines parsed (GOOD)")
    
    print()
    
    # 2. Check for missing tests
    parsed_names = {r["test_name"] for r in results}
    missing = set(expected.keys()) - parsed_names
    if missing:
        print(f"  ✗ MISSING TESTS ({len(missing)}):")
        for name in sorted(missing):
            print(f"     - {name}")
    else:
        print(f"  ✓ All expected tests found")
    
    print()
    
    # 3. Check for value/range confusion
    print("  DETAILED CHECKS:")
    for result in results:
        name = result["test_name"]
        value = result["value"]
        unit = result["unit"]
        ref = result["reference_range"]
        
        if name in expected:
            exp_val, exp_unit, exp_ref = expected[name]
            
            # Check if value looks like a range (X-Y pattern)
            if isinstance(value, (int, float)) and "-" in str(value):
                print(f"    ✗ {name}: Value looks like range: {value}")
            
            # Check unit corruption
            if unit != exp_unit and name == "Packed Cell Volume":
                if unit == "aid":
                    print(f"    ✗ {name}: Unit not corrected: 'aid' should be 'g/dL'")
                elif unit == "g/dL":
                    print(f"    ✓ {name}: Unit corrected from 'aid' to 'g/dL'")
            
            # Check row alignment (Absolute Neutrophil Count should be 3.41, not 56)
            if name == "Absolute Neutrophil Count":
                if abs(value - 56) < 0.01:
                    print(f"    ✗ {name}: ROW MISALIGNED - got 56 (Neutrophils %), expected {exp_val}")
                elif abs(value - exp_val) < 0.01:
                    print(f"    ✓ {name}: Correct value {value}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Tests parsed: {len(results)}")
    print(f"Tests expected: {len(expected)}")
    print(f"Missing: {len(missing)}")
    
    # Print all parsed results for visual inspection
    print("\nFull parsed results:")
    for i, result in enumerate(results, 1):
        print(f"{i:2d}. {result['test_name']:30s} = {result['value']:10.2f} {result.get('unit', ''):15s} ({result.get('reference_range', '')})")

if __name__ == "__main__":
    test_parsing()
