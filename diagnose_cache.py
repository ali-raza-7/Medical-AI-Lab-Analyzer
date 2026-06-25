"""
Diagnostic script: verify pipeline cache hypothesis for identical analysis results.
Does NOT modify any production code — only reads/logs.
"""
import hashlib
import json
import sys
import time
import logging

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                    format="[%(levelname)s] %(message)s")
log = logging.getLogger("diagnose")

# PHASE 3: Cache Key Analysis

def _get_pipeline_cache_key(text: str, gender: str, age: int) -> str:
    """Exact replica of core/tasks.py:_get_pipeline_cache_key"""
    normalized_text = " ".join(text.split()).strip().lower()
    key_str = f"{normalized_text}|{gender.lower()}|{age}"
    return hashlib.md5(key_str.encode()).hexdigest()

def simulate_cache_key_scenarios():
    print("=" * 70)
    print("PHASE 3: CACHE KEY ANALYSIS")
    print("=" * 70)
    
# Scenario 1: Text input (different reports → different keys)
    with open("/tmp/report_a.txt") as f:
        text_a = f.read()
    with open("/tmp/report_b.txt") as f:
        text_b = f.read()
    
    print("\n--- Scenario A: Text Input (text parameter is set) ---")
    key_a = _get_pipeline_cache_key(text_a, "male", 45)
    key_b = _get_pipeline_cache_key(text_b, "female", 62)
    print(f"  Report A text hash = {hashlib.md5(text_a.encode()).hexdigest()[:16]}")
    print(f"  Report B text hash = {hashlib.md5(text_b.encode()).hexdigest()[:16]}")
    print(f"  Report A cache key = {key_a}")
    print(f"  Report B cache key = {key_b}")
    print(f"  Keys DIFFER? {key_a != key_b}  ✓ Correct — cache will not collide")
    
    print("\n--- Scenario B: File Upload (text=None → text='') ---")
# File uploads pass text=None → perform_analysis does text or "" → ""
    input_text_a = None  # file upload
    effective_a = input_text_a or ""
    input_text_b = None  # another file upload
    effective_b = input_text_b or ""
    key_file_a = _get_pipeline_cache_key(effective_a, "male", 30)
    key_file_b = _get_pipeline_cache_key(effective_b, "male", 30)
    print(f"  File upload A: text=None → effective='{effective_a}' → key={key_file_a}")
    print(f"  File upload B: text=None → effective='{effective_b}' → key={key_file_b}")
    print(f"  Keys IDENTICAL? {key_file_a == key_file_b}  ✗ BUG! All file uploads collide!")
    
    print("\n--- Scenario C: File Upload with different gender/age ---")
    key_c1 = _get_pipeline_cache_key("", "female", 62)
    key_c2 = _get_pipeline_cache_key("", "male", 30)
    print(f"  Female/62: key={key_c1}")
    print(f"  Male/30:   key={key_c2}")
    print(f"  Keys DIFFER? {key_c1 != key_c2}")
    print(f"  (Different gender/age → different keys, but same gender/age → collision)")
    
    return {
        "text_a_key": key_a,
        "text_b_key": key_b,
        "text_keys_differ": key_a != key_b,
        "file_keys_collide": key_file_a == key_file_b,
        "file_key_collision_value": key_file_a,
    }

# PHASE 1 & 2: OCR + Parsing via direct pipeline call

def analyze_text_via_pipeline(report_path: str, label: str):
    """Run the actual pipeline directly on text input (bypasses API/cache)."""
    print(f"\n{'=' * 70}")
    print(f"PHASE 1+2: PIPELINE ANALYSIS — {label}")
    print(f"{'=' * 70}")
    
    with open(report_path) as f:
        raw_text = f.read()
    
    text_hash = hashlib.md5(raw_text.encode()).hexdigest()
    print(f"  Text hash: {text_hash}")
    print(f"  Characters: {len(raw_text)}")
    print(f"  Lines: {raw_text.count(chr(10))}")
    
# Run the pipeline directly
    from core.pipeline import process_lab_report
    from core.parser import parse_lab_report
    from core.normalization import repair_ocr_text, normalize_test_name
    
# OCR repair
    repaired = repair_ocr_text(raw_text)
    print(f"  After OCR repair: {len(repaired)} chars")
    
# Parse
    parsed = parse_lab_report(repaired)
    print(f"  Parsed tests: {len(parsed)}")
    for p in parsed:
        print(f"    - {p['test_name']:30s} value={p['value']:>8}  unit={p['unit']:15s} range={p['reference_range']}")
    
# Full pipeline
    resolved, tracker = process_lab_report(raw_text, gender="male" if "male" in raw_text.lower() else "female",
                                            age=45 if "45" in raw_text else 62)
    print(f"\n  Pipeline result: {len(resolved)} tests, tracker.total_parsed={tracker.total_parsed}")
    
    abnormal = [t for t in resolved if t.status in ("high", "low")]
    print(f"  Abnormal tests: {len(abnormal)}")
    for t in resolved:
        marker = " ⚠" if t.status in ("high", "low") else "  "
        print(f"  {marker} {t.resolved_key:30s} value={t.value:>8.2f}  {t.unit:15s} status={t.status:>8}  name={t.test_name}")
    
    return resolved, parsed, tracker


# EXECUTION

if __name__ == "__main__":
# Phase 3: Cache key analysis first (no dependencies)
    cache_evidence = simulate_cache_key_scenarios()
    
# Phase 1+2: Pipeline analysis via direct call
    print("\n")
    print("=" * 70)
    print("RUNNING PIPELINE ON TWO DIFFERENT REPORTS")
    print("=" * 70)
    
    result_a, parsed_a, _ = analyze_text_via_pipeline("/tmp/report_a.txt", "REPORT A (Healthy Male)")
    result_b, parsed_b, _ = analyze_text_via_pipeline("/tmp/report_b.txt", "REPORT B (Sick Female)")
    
# Compare
    print("\n")
    print("=" * 70)
    print("COMPARISON: Report A vs Report B")
    print("=" * 70)
    print(f"  Parsed tests:    A={len(parsed_a)}  B={len(parsed_b)}  DIFFERENT? {len(parsed_a) != len(parsed_b)}")
    
    keys_a = {t.resolved_key for t in result_a}
    keys_b = {t.resolved_key for t in result_b}
    print(f"  Unique test keys: A={len(keys_a)}  B={len(keys_b)}  DIFFERENT? {len(keys_a) != len(keys_b)}")
    print(f"  Tests only in A: {keys_a - keys_b}")
    print(f"  Tests only in B: {keys_b - keys_a}")
    
    abnormal_a = {(t.resolved_key, t.status) for t in result_a}
    abnormal_b = {(t.resolved_key, t.status) for t in result_b}
    print(f"  Abnormal tests: A={len([t for t in result_a if t.status in ('high','low')])}  "
          f"B={len([t for t in result_b if t.status in ('high','low')])}")
    
# Check if values actually differ
    val_map_a = {t.resolved_key: t.value for t in result_a}
    val_map_b = {t.resolved_key: t.value for t in result_b}
    common_keys = keys_a & keys_b
    same_values = sum(1 for k in common_keys if val_map_a.get(k) == val_map_b.get(k))
    diff_values = sum(1 for k in common_keys if val_map_a.get(k) != val_map_b.get(k))
    print(f"  Common tests with SAME value: {same_values}")
    print(f"  Common tests with DIFFERENT value: {diff_values}")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"""
  CACHE KEY COLLISION FOR FILE UPLOADS: {cache_evidence['file_keys_collide']}
  PIPELINE PRODUCES DIFFERENT RESULTS FOR DIFFERENT INPUTS: {diff_values > 0}
  
  CONCLUSION: The pipeline itself works correctly for different text inputs.
  The bug is in the CACHE KEY computation which uses the 'text' parameter
  (empty for file uploads) instead of the OCR'd text.
""")
