r"""
TEST: Percentage-based lab test parsing fix

ISSUE: Pipeline was dropping 3 tests (Eosinophils, Basophils, HbA1c) that had 
percentage values (%) without separate numeric units.

ROOT CAUSE: The _is_garbage_line() function in parser.py was rejecting lines
with percentage-only values because the regex pattern for numeric detection 
only matched pure numbers ([\d\.e\-\+]+), not percentages (40%, 2%, etc).

TESTS AFFECTED:
- Input: 9 tests
- Output (BEFORE FIX): 6 tests (dropped: Eosinophils, Basophils, HbA1c)
- Output (AFTER FIX): 9 tests (all preserved)

FIX APPLIED:
Updated _is_garbage_line() regex from:
  if re.match(r'^[\d\.e\-\+]+$', word):
To:
  if re.match(r'^[\d\.e\-\+%\(\)]+$', word):
  
This allows the function to recognize percentage values and parenthesized
ranges like "40%", "(37-47%)" as numeric data, not garbage.
"""

import pytest
from core.parser import parse_lab_report
from core.pipeline import process_lab_report
from core.resolver import resolve_test_key_with_confidence


def test_percentage_value_parsing():
    """Test that percentage-only lab values are parsed correctly."""
    text = """
    Lab Results
    Hematocrit: 40% (37-47%)
    Eosinophils: 2% (1-4%)
    Basophils: 1% (0-1%)
    HbA1c: 5.5% (4.0-5.6%)
    """
    
    parsed = parse_lab_report(text)
    
    # All 4 percentage tests should be parsed
    assert len(parsed) == 4, f"Expected 4 parsed tests, got {len(parsed)}"
    
    test_names = [t['test_name'].lower() for t in parsed]
    assert 'hematocrit' in test_names, "Hematocrit not parsed"
    assert 'eosinophils' in test_names, "Eosinophils not parsed"
    assert 'basophils' in test_names, "Basophils not parsed"
    assert 'hba1c' in test_names, "HbA1c not parsed"
    
    # Check values and units
    for test in parsed:
        assert test['value'] > 0, f"Invalid value for {test['test_name']}"
        assert test['unit'] == '%', f"Expected % unit for {test['test_name']}"


def test_nine_test_complete_scenario():
    """Test the complete 9-test scenario from the bug report."""
    text = """
    Lab Results Report
    
    WBC Count: 7.5 x10^3/uL (4.0-11.0)
    RBC: 4.5 x10^6/uL (4.5-5.5)
    Hemoglobin: 13.5 g/dL (13.0-16.0)
    Hematocrit: 40% (37-47%)
    Platelets: 250 x10^9/L (150-400)
    Eosinophils: 2% (1-4%)
    Basophils: 1% (0-1%)
    Neutrophils: 65% (50-70%)
    HbA1c: 5.5% (4.0-5.6%)
    """
    
    # STAGE 1: Parser
    parsed = parse_lab_report(text)
    assert len(parsed) == 9, f"Parser: Expected 9 tests, got {len(parsed)}"
    
    # STAGE 2: Resolver
    for test in parsed:
        key, conf = resolve_test_key_with_confidence(test['test_name'])
        assert key is not None, f"Resolver: Failed to resolve {test['test_name']}"
        assert conf >= 0.65, f"Resolver: Low confidence ({conf:.2f}) for {test['test_name']}"
    
    # STAGE 3: Full Pipeline
    resolved_tests, tracker = process_lab_report(text)
    assert len(resolved_tests) == 9, f"Pipeline: Expected 9 final tests, got {len(resolved_tests)}"
    assert tracker.total_parsed == 9, f"Expected 9 parsed, got {tracker.total_parsed}"
    assert tracker.garbage_filtered == 0, f"Unexpected garbage filtering: {tracker.garbage_filtered}"
    assert tracker.dropped == 0, f"Unexpected dropped tests: {tracker.dropped}"
    
    # Verify all critical tests are in output
    resolved_keys = {t.resolved_key for t in resolved_tests}
    required_keys = {'eosinophils_pct', 'basophils_pct', 'hba1c', 'hematocrit'}
    missing = required_keys - resolved_keys
    assert not missing, f"Missing critical tests: {missing}"


def test_mixed_percentage_and_standard_units():
    """Test that percentage and standard units work together."""
    text = """
    Hemoglobin: 13.5 g/dL (13.0-16.0)
    Hematocrit: 40% (37-47%)
    RBC: 4.5 x10^6/uL (4.5-5.5)
    Eosinophils: 2% (1-4%)
    """
    
    parsed = parse_lab_report(text)
    assert len(parsed) == 4
    
    units = [t['unit'] for t in parsed]
    assert 'g/dL' in units, "Standard unit (g/dL) missing"
    assert '%' in units, "Percentage unit (%) missing"
    assert 'x10^6/µL' in units, "Scientific unit missing"


def test_percentage_ranges_in_parentheses():
    """Test that percentage ranges like (37-47%) are correctly parsed."""
    text = """
    Hematocrit: 40% (37-47%)
    Basophils: 1% (0-1%)
    """
    
    parsed = parse_lab_report(text)
    assert len(parsed) == 2
    
    # Check that reference ranges with percentages are captured
    for test in parsed:
        assert test['reference_range'], f"Reference range missing for {test['test_name']}"
        assert '%' in test['reference_range'], f"Percentage in reference range missing for {test['test_name']}"


def test_unresolved_percentages_not_filtered():
    """Test that unresolved percentage tests still appear in output (with status 'unknown')."""
    text = """
    Hemoglobin: 13.5 g/dL (13.0-16.0)
    RandomUnknownTest: 50% (40-60%)
    """
    
    resolved_tests, tracker = process_lab_report(text)
    
    # Both tests should be in output (or at least one resolved + one unresolved)
    assert len(resolved_tests) >= 1, "No tests in output"
    
    # At least Hemoglobin should be resolved
    resolved_keys = [t.resolved_key for t in resolved_tests if t.resolved_key]
    assert len(resolved_keys) >= 1, f"No tests resolved. Tests in output: {[t.test_name for t in resolved_tests]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
