"""Regression tests for parser bug fixes (BUG-01 through BUG-08)."""

import pytest
from core.parser import (
    parse_lab_report,
    _is_ref_range_token,
    _extract_numeric,
    _clean_line,
)
from core.pipeline import process_lab_report, is_medical_report


def test_medical_validation_rejects_non_medical():
    """Non-medical text should be rejected by medical validation."""
    resolved, tracker = process_lab_report("This is not a lab report 123")
    assert len(resolved) == 0
    assert tracker.total_parsed == 0


def test_medical_validation_accepts_cbc():
    """Text containing CBC markers should pass medical validation."""
    assert is_medical_report("Complete Blood Count (CBC)")
    assert is_medical_report("Hemoglobin 13.2")
    assert is_medical_report("WBC 5.8 x10^3/µL")
    assert is_medical_report("Platelets 250")
    assert not is_medical_report("Buy one get one free")


def test_multi_column_preserved():
    """BUG-01: Multi-column data must be parsed with correct values."""
    text = "Hemoglobin  13.2  g/dL  13.5-17.5"
    result = parse_lab_report(text)
    assert len(result) == 1
    assert result[0]["test_name"] == "Hemoglobin"
    assert result[0]["value"] == 13.2
    assert result[0]["unit"] == "g/dL"
    assert result[0]["reference_range"] == "13.5-17.5"


def test_split_ref_range_extraction():
    """BUG-02: 3-token ranges like '40 - 80' must extract correctly."""
    result = parse_lab_report("Neutrophils 79 % 40 - 80")
    assert len(result) == 1
    assert result[0]["value"] == 79.0
    assert result[0]["reference_range"] == "40-80"


def test_mcv_mch_with_split_ranges():
    """BUG-04/BUG-05: MCV/MCH must not be dropped with split ranges."""
    text = "MCV 87.7 fL 83 - 101"
    result = parse_lab_report(text)
    assert len(result) == 1
    assert result[0]["test_name"] == "MCV"
    assert abs(result[0]["value"] - 87.7) < 0.1


def test_percentage_suffixed_range():
    """BUG-06: %-suffixed ranges must be recognized."""
    assert _is_ref_range_token("0-2%")
    assert _is_ref_range_token("1-4%")


def test_percentage_value_token_extraction():
    """BUG-05: _extract_numeric must handle %-suffixed tokens."""
    assert _extract_numeric("40%") == 40.0
    assert _extract_numeric("2%") == 2.0
    assert _extract_numeric("5.5%") == 5.5


def test_percentage_parens_format():
    """BUG-07/BUG-08: 'X% (Y-Z%)' format must parse."""
    text = "Eosinophils: 2% (1-4%)"
    result = parse_lab_report(text)
    assert len(result) == 1
    assert result[0]["test_name"] == "Eosinophils"
    assert result[0]["value"] == 2.0
    assert result[0]["unit"] == "%"
    assert "1-4" in result[0]["reference_range"]


def test_colon_separated_format():
    """Colon-separated format like 'WBC: 7.5 x10^3/uL (4.0-11.0)'."""
    text = "WBC: 7.5 x10^3/uL (4.0-11.0)"
    result = parse_lab_report(text)
    assert len(result) == 1
    assert abs(result[0]["value"] - 7.5) < 0.1
    assert result[0]["unit"]


def test_threshold_with_percent():
    """Threshold patterns with % suffix."""
    assert _is_ref_range_token("<5%")
    assert _is_ref_range_token(">10%")


def test_short_name_three_alpha():
    """Short 3-alpha names like RBC, MCV, MCH must parse."""
    text = "RBC 4.5 x10^6/µL 4.5-5.5"
    result = parse_lab_report(text)
    assert len(result) >= 1


def test_double_space_not_destroyed():
    """_clean_line must preserve double-space column separators."""
    cleaned = _clean_line("Hemoglobin  13.2  g/dL  13.5-17.5")
    assert "  " in cleaned


def test_full_cbc_with_split_ranges():
    """Multiple tests with split ranges in a single report."""
    text = """
    Hemoglobin 13.2 g/dL 13.5 - 17.5
    MCV 87.7 fL 83 - 101
    MCH 32.1 pg 27 - 33
    Platelet Count 245 x10^3/µL 150 - 450
    """
    result = parse_lab_report(text)
    names = [t["test_name"] for t in result]
    assert "MCV" in names
    assert "MCH" in names
    assert "Hemoglobin" in names
    for t in result:
        assert t["value"] > 0
    hemoglobin = next(t for t in result if t["test_name"] == "Hemoglobin")
    assert abs(hemoglobin["value"] - 13.2) < 0.1


def test_mixed_percentage_and_standard_units_full():
    """Mixed standard and percentage units in same report."""
    text = """
    Hemoglobin: 13.5 g/dL (13.0-16.0)
    Hematocrit: 40% (37-47%)
    RBC: 4.5 x10^6/uL (4.5-5.5)
    Eosinophils: 2% (1-4%)
    """
    result = parse_lab_report(text)
    assert len(result) == 4
    names = {t["test_name"].lower(): t for t in result}
    assert "eosinophils" in names
    assert names["eosinophils"]["value"] == 2.0
    assert names["eosinophils"]["unit"] == "%"


def test_nine_test_complete_pipeline():
    """Full 9-test report through entire pipeline."""
    text = """
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
    resolved, tracker = process_lab_report(text)
    assert len(resolved) == 9, f"Expected 9, got {len(resolved)}"
    assert tracker.total_parsed == 9
