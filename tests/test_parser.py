"""
Unit tests for parsing + classification pipeline.

Run with pytest or directly:
  ./myenv/bin/python -m pytest test_parsing_and_classification.py -v
"""

from core.parser import parse_lab_report
from core.resolver import resolve_test_key
from medical.reference_db import get_reference_range, get_test_definition
from core.normalization import normalize_unit, normalize_count_to_per_uL, convert_value
from core.classifier import classify_numeric


def _status_for(line: str, gender: str = "male", age_group: str = "adult") -> str:
    """
    Parse a lab line, resolve to a canonical key, apply unit normalization,
    and classify against reference ranges.
    """
    parsed = parse_lab_report(line)
    assert parsed, f"failed to parse: {line!r}"
    it = parsed[0]

    key = resolve_test_key(it["test_name"])
    if not key:
        return "unknown"

    td = get_test_definition(key)
    rr = get_reference_range(key, gender, age_group)
    assert td and rr, f"No definition/range for key={key!r}"

    val = it["value"]
    u = normalize_unit(it.get("unit", ""))

    if td.canonical_unit == "/µL":
        nm = normalize_count_to_per_uL(val, u)
        assert nm is not None, f"Could not normalize count unit {u!r}"
        val = nm.value
    elif u and rr.unit and u != rr.unit:
        converted = convert_value(val, from_unit=u, to_unit=rr.unit)
        if converted is not None:
            val = converted

    return classify_numeric(val, rr.low, rr.high)


# ── CBC unit conversion tests ────────────────────────────────────────────────

def test_x10_3_units_normal():
    assert _status_for("WBC Count 7.5 x10^3/µL (4.0-11.0)") == "normal"
    assert _status_for("Platelet Count 250 x10^3/µL (150-450)") == "normal"


def test_x10_6_units_normal():
    assert _status_for("RBC Count 4.8 x10^6/µL (4.5-5.5)") == "normal"


def test_simple_units():
    assert _status_for("Glucose 92 mg/dL (70-100)") == "normal"
    assert _status_for("Creatinine 1.6 mg/dL (0.7-1.3)") == "high"


# ── Gender-specific tests ────────────────────────────────────────────────────

def test_hemoglobin_gender():
    # 9.5 g/dL is low for both male and female
    assert _status_for("Hemoglobin 9.5 g/dL", gender="male") == "low"
    # 13.5 g/dL is normal for female (12.0–15.5) but could be low for male (13.5–17.5 → edge)
    assert _status_for("Hemoglobin 13.5 g/dL", gender="female") == "normal"


# ── Thyroid tests ────────────────────────────────────────────────────────────

def test_tsh_high():
    assert _status_for("TSH 8.5 mIU/L") == "high"

def test_tsh_high_iu_per_ml():
    assert _status_for("TSH 8.9 µIU/mL") == "high"
    assert _status_for("TSH 3.2 uIU/mL") == "normal"


def test_rdw_cv_ocr_alias_pow_resolves():
    parsed = parse_lab_report("Pow   9   %   11.0-15.0")
    assert len(parsed) == 1
    assert parsed[0]["test_name"] == "Pow"
    assert parsed[0]["unit"] == "%"
    from core.resolver import resolve_test_key_with_confidence
    key, confidence = resolve_test_key_with_confidence(parsed[0]["test_name"])
    assert key == "rdw"
    assert confidence == 1.0


def test_parse_rdw_cv_decimal_fragment():
    parsed = parse_lab_report("PoW   12 . 2   %   11.0-15.0")
    assert len(parsed) == 1
    assert parsed[0]["value"] == 12.2
    assert parsed[0]["unit"] == "%"
    assert parsed[0]["reference_range"] == "11.0-15.0"


def test_hba1c_ignores_ocr_unit():
    assert _status_for("HbA1c 9.2 g/dL") == "high"

# ── Vitamin tests ────────────────────────────────────────────────────────────

def test_vitamin_d_low():
    assert _status_for("Vitamin D 15 ng/mL") == "low"


# ── Diabetes ─────────────────────────────────────────────────────────────────

def test_hba1c_high():
    assert _status_for("HbA1c 7.2 %") == "high"


# ── Platelet low / WBC high ──────────────────────────────────────────────────

def test_platelet_low():
    assert _status_for("Platelet Count 98 x10^3/µL") == "low"


def test_wbc_high():
    assert _status_for("WBC Count 15.9 x10^3/µL") == "high"
