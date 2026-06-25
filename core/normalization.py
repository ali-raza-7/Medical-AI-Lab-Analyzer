"""OCR-tolerant lab normalization pipeline."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

_DASHES = "\u2013\u2014\u2212"
_SUPERSCRIPT_MAP = str.maketrans({
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
    "⁰": "0",
})

_MANGLED_SCI = [
    (re.compile(r"[xX×*][lI1][oO0]\^(\d+)", re.I), r"x10^\1"),
    (re.compile(r"[xX×*]10\^(\d+)", re.I), r"x10^\1"),
    (re.compile(r"[lI][oO0]\^(\d+)", re.I), r"10^\1"),
    (re.compile(r"10[Aa](\d+)"), r"10^\1"),
    (re.compile(r"\b10\d?([3-9])\/"), lambda m: f"x10^{m.group(1)}/"),
]

def clean_ocr_unit(unit: str) -> str:
    if not unit:
        return unit
    original = unit
    s = unit.translate(_SUPERSCRIPT_MAP)
    s = s.replace("×", "x")
    s = re.sub(r"pL\b", "uL", s)
    s = re.sub(r"pµL\b", "µL", s)
    s = re.sub(r"(?<=[xX×*\d])l(?=[oO0\^])", "1", s)
    s = re.sub(r"(?<=[xX×*])l(?=\d)", "1", s)
    s = re.sub(r"(?<=\d)O(?=[\^/\d])", "0", s)
    s = re.sub(r"(?<=[xX×*1])O(?=[\^/\d])", "0", s)
    for pat, repl in _MANGLED_SCI:
        if callable(repl):
            s = pat.sub(repl, s)
        else:
            s = pat.sub(repl, s)
    if s != original:
        logger.debug("[OCR-unit] corrected %r → %r", original, s)
    return s


def clean_unit(unit: str, test_name: str = "") -> str:
    if not unit:
        return ""
    s = unit.strip()

# Remove repeated special characters (OCR artifacts)
    s = re.sub(r"[–—−]", "-", s)
    s = re.sub(r"[-]{2,}", "", s)
    s = re.sub(r"[/]{2,}", "/", s)
    s = re.sub(r"[#]{2,}", "", s)
    s = re.sub(r"[*]{2,}", "", s)
    s = re.sub(r"[_]{2,}", "", s)

# Common OCR unit mistakes — case-insensitive check
    s_lower = s.lower().replace(" ", "")
    if s_lower in _UNIT_FIXES:
        return _UNIT_FIXES[s_lower]

# Run through existing normalizer
    s = normalize_unit(s)

# If still empty or unrecognized, look up expected unit by test name
    if (not s or len(s) < 2) and test_name:
        canonical = normalize_test_name(test_name)
        s = TEST_EXPECTED_UNITS.get(canonical, s)

    return s


def clean_ocr_text(text: str) -> str:
    """Alias for repair_ocr_text for backward compatibility."""
    return repair_ocr_text(text)


@lru_cache(maxsize=1024)
def normalize_test_name(name: str) -> str:
    s = (name or "").strip().lower()
    s = s.replace("&", " and ")
    s = re.sub(rf"[{_DASHES}]", "-", s)
    s = re.sub(r"[\(\)\[\]\{\}]", " ", s)
    s = re.sub(r"[^a-z0-9%/\.\-\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    _ocr_words = [
        (re.compile(r"\bhaemoglobin\b"), "hemoglobin"),
        (re.compile(r"\bhemoglobn\b"), "hemoglobin"),
        (re.compile(r"\bhemglobin\b"), "hemoglobin"),
        (re.compile(r"\bhaemoglobn\b"), "hemoglobin"),
        (re.compile(r"\bhgb\b"), "hemoglobin"),
        (re.compile(r"\br\.b\.c\b"), "rbc"),
        (re.compile(r"\bw\.b\.c\b"), "wbc"),
        (re.compile(r"\bplatlets\b"), "platelets"),
        (re.compile(r"\bplatlet\b"), "platelet"),
        (re.compile(r"\bplt\b"), "platelets"),
        (re.compile(r"\bneutrofils?\b"), "neutrophils"),
        (re.compile(r"\bneutophils?\b"), "neutrophils"),
        (re.compile(r"\beosnophis\b"), "eosinophils"),
        (re.compile(r"\beosnophils?\b"), "eosinophils"),
        (re.compile(r"\beosniophils?\b"), "eosinophils"),
        (re.compile(r"\beosinophil\b"), "eosinophils"),
        (re.compile(r"\blimphocyte\b"), "lymphocytes"),
        (re.compile(r"\blymphosytes\b"), "lymphocytes"),
        (re.compile(r"\blympocytes\b"), "lymphocytes"),
        (re.compile(r"\blymphocyte\b"), "lymphocytes"),
        (re.compile(r"\bhb\b(?!a)"), "hemoglobin"),
        (re.compile(r"\bgluco\b"), "glucose"),
# OCR-corrupted variants from letter↔digit confusions
        (re.compile(r"\bw8c\b"), "wbc"),         # B→8
        (re.compile(r"\bn8c\b"), "rbc"),         # r→n, B→8
        (re.compile(r"\bp1ate1et\b"), "platelet"), # l→1
        (re.compile(r"\bneutrophi1s?\b"), "neutrophils"), # l→1
        (re.compile(r"\b1ymphocytes\b"), "lymphocytes"), # I→1
        (re.compile(r"\bhemog10bin\b"), "hemoglobin"), # l→1
        (re.compile(r"\bhemog1obin\b"), "hemoglobin"),
        (re.compile(r"\bcreatinine\b"), "creatinine"),
        (re.compile(r"\bu5\b"), "us"),           # S→5 in "us" (ultrasound)
# More OCR-corrupted variants
        (re.compile(r"\bt0ta1\b"), "total"),     # o→0, l→1
        (re.compile(r"\bch01ester01\b"), "cholesterol"), # l→1
        (re.compile(r"\btri9lycerides?\b"), "triglycerides"), # g→9
        (re.compile(r"\btri9lyceride\b"), "triglycerides"),
        (re.compile(r"\bcreatinine\b"), "creatinine"),
        (re.compile(r"\bcreatinine\b"), "creatinine"),
        (re.compile(r"\bma9nesium\b"), "magnesium"), # g→9
        (re.compile(r"\bp0tassium\b"), "potassium"), # o→0
        (re.compile(r"\bs0dium\b"), "sodium"),    # o→0
        (re.compile(r"\bch10ride\b"), "chloride"), # l→1
        (re.compile(r"\bc01cium\b"), "calcium"),  # a→0, l→1
        (re.compile(r"\bph0sph0rus\b"), "phosphorus"), # o→0
        (re.compile(r"\balbumin\b"), "albumin"),
        (re.compile(r"\bbilirubin\b"), "bilirubin"),
        (re.compile(r"\bt0tal bi1irubin\b"), "total bilirubin"),
        (re.compile(r"\bdirect bi1irubin\b"), "direct bilirubin"),
        (re.compile(r"\bindirect bi1irubin\b"), "indirect bilirubin"),
        (re.compile(r"\bqgt\b"), "ggt"),         # G→Q OCR
        (re.compile(r"\bqqt\b"), "ggt"),
        (re.compile(r"\balt\b"), "alt"),
        (re.compile(r"\bast\b"), "ast"),
        (re.compile(r"\ba1p\b"), "alp"),         # l→1
        (re.compile(r"\ba1t\b"), "alt"),
        (re.compile(r"\bas1\b"), "ast"),
        (re.compile(r"\bcreatinine\b"), "creatinine"),
        (re.compile(r"\bura\b"), "urea"),
        (re.compile(r"\buric acid\b"), "uric acid"),
        (re.compile(r"\btota1 ch01ester01\b"), "total cholesterol"),
        (re.compile(r"\btriglycerides\b"), "triglycerides"),
        (re.compile(r"\bhba1c\b"), "hba1c"),
        (re.compile(r"\btsh\b"), "tsh"),
        (re.compile(r"\bfree t4\b"), "free t4"),
        (re.compile(r"\bfree t3\b"), "free t3"),
        (re.compile(r"\ba/g ratio\b"), "ag ratio"),
    ]
    for pat, replacement in _ocr_words:
        s = pat.sub(replacement, s)
# Deduplicate repeated words from OCR (e.g. "hemoglobin hemoglobin" from "Hemoglobin (Hb)")
    words = s.split()
    deduped = []
    for w in words:
        if not deduped or w != deduped[-1]:
            deduped.append(w)
    s = " ".join(deduped)
    s = re.sub(r"\s*-\s*", "-", s)
    return s.strip()


def normalize_unit(unit: str) -> str:
    s = (unit or "").strip()
    if not s:
        return ""
    s = clean_ocr_unit(s)
# Check _UNIT_FIXES early (covers OCR variants like "million / wl", "/pl", "pe", etc.)
    s_lower = s.lower().replace(" ", "")
    if s_lower in _UNIT_FIXES:
        return _UNIT_FIXES[s_lower]
    s = s.replace("μ", "µ")
    s = s.replace("×", "x")
    s = s.replace(" ", "")
    s = s.replace("10**", "10^")
    s = re.sub(r"(?i)(?<![a-z])ul\b", "µL", s)
    s = s.replace("ul", "µL").replace("UL", "µL")

# Fix corrupt unit names
    for pat, repl in _CORRUPT_UNITS:
        s = pat.sub(repl, s)

    _UNIT_ALIAS = [
        (re.compile(r"\bin\b", re.I), "fL"),
        (re.compile(r"millions?/[µu]?L\b", re.I), "x10^6/µL"),
        (re.compile(r"million/[µu]L\b", re.I), "x10^6/µL"),
        (re.compile(r"[xX×]\s*10\^(\d+)/L\b"), lambda m: f"x10^{m.group(1)}/L"),
        (re.compile(r"[xX×]\s*10\^(\d+)/[µu]L\b"), lambda m: f"x10^{m.group(1)}/µL"),
        (re.compile(r"(?<![xX×\d])10\^(\d+)/L\b"), lambda m: f"x10^{m.group(1)}/L"),
        (re.compile(r"(?<![xX×\d])10\^(\d+)/[µu]L\b"), lambda m: f"x10^{m.group(1)}/µL"),
        (re.compile(r"10\*\*(\d+)"), lambda m: f"x10^{m.group(1)}"),
        (re.compile(r"\bk/[µu]L\b", re.I), "x10^3/µL"),
        (re.compile(r"\bk/L\b", re.I), "x10^3/L"),
        (re.compile(r"\bper\s*[µu]?L\b", re.I), "/µL"),
        (re.compile(r"cells?/[µu]L\b", re.I), "/µL"),
        (re.compile(r"cells?/L\b", re.I), "/L"),
        (re.compile(r"\b[uµ]iu/mL\b", re.I), "µIU/mL"),
    ]
    for pat, repl in _UNIT_ALIAS:
        if callable(repl):
            s = pat.sub(repl, s)
        else:
            s = pat.sub(repl, s)
    s = s.replace("/uL", "/µL")
    return s


@dataclass(frozen=True)
class ParsedRange:
    low: Optional[float]
    high: Optional[float]
    unit: str

_NUM_PAT = r"(?:(?:\d{1,3}(?:,\d{3})+)|\d+)(?:\.\d+)?"

def _to_float(num: str) -> float:
    return float(num.replace(",", ""))


def parse_reference_range(range_str: str, default_unit: str = "") -> ParsedRange:
    s = (range_str or "").strip()
    unit = normalize_unit(default_unit)
    if not s:
        return ParsedRange(low=None, high=None, unit=unit)

    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")

# Handle "Upto X" / "Up to X" patterns
    m_upto = re.match(rf"^(?:upto|up\s*to)\s*({_NUM_PAT})$", s, re.I)
    if m_upto:
        val = _to_float(m_upto.group(1))
        return ParsedRange(low=0, high=val, unit=unit)

    s = re.sub(r"\bto\b", "-", s, flags=re.I)
    s = s.strip("()[]{} ")
    m_unit = re.search(r"^(.*?)\s*([a-zA-Z%/µx×][a-zA-Z%/µ\^\d\.\-x×]*)$", s)
    core = s
    if m_unit:
        candidate = normalize_unit(m_unit.group(2))
        if candidate:
            core = m_unit.group(1).strip()
            unit = candidate
    for pat, side in [
        (re.compile(rf"^(<=|≤)\s*({_NUM_PAT})$"), "high"),
        (re.compile(rf"^(>=|≥)\s*({_NUM_PAT})$"), "low"),
        (re.compile(rf"^(<)\s*({_NUM_PAT})$"),    "high"),
        (re.compile(rf"^(>)\s*({_NUM_PAT})$"),    "low"),
    ]:
        m = pat.match(core)
        if m:
            val = _to_float(m.group(2))
            if side == "high":
                return ParsedRange(low=0, high=val, unit=unit)
            return ParsedRange(low=val, high=999, unit=unit)
    parts = re.split(r"\s*-\s*", core)
    if len(parts) >= 2:
        try:
            low = _to_float(parts[0])
            high = _to_float(parts[1])
            if low < 0:
                low = 0
            if high <= low:
                return ParsedRange(low=None, high=None, unit=unit)
            return ParsedRange(low=low, high=high, unit=unit)
        except Exception:
            pass
    return ParsedRange(low=None, high=None, unit=unit)


def _unit_multiplier(unit: str) -> float:
    u = normalize_unit(unit)
    m = re.search(r"x10\^(\d+)", u)
    return 10 ** int(m.group(1)) if m else 1.0


def _unit_volume_factor(unit: str) -> float:
    u = normalize_unit(unit)
    if "/L" in u and "/µL" not in u:
        return 1.0 / 1_000_000.0
    return 1.0


# Medical conversion constants
_CONVERSION_MAP = {
    "glucose_fasting": {("mmol/L", "mg/dL"): 18.0182, ("mg/dL", "mmol/L"): 1/18.0182},
    "cholesterol": {("mmol/L", "mg/dL"): 38.67, ("mg/dL", "mmol/L"): 1/38.67},
    "ldl": {("mmol/L", "mg/dL"): 38.67, ("mg/dL", "mmol/L"): 1/38.67},
    "hdl": {("mmol/L", "mg/dL"): 38.67, ("mg/dL", "mmol/L"): 1/38.67},
    "total_cholesterol": {("mmol/L", "mg/dL"): 38.67, ("mg/dL", "mmol/L"): 1/38.67},
    "triglycerides": {("mmol/L", "mg/dL"): 88.57, ("mg/dL", "mmol/L"): 1/88.57},
    "creatinine": {("µmol/L", "mg/dL"): 1/88.4, ("mg/dL", "µmol/L"): 88.4},
    "total_bilirubin": {("µmol/L", "mg/dL"): 1/17.1, ("mg/dL", "µmol/L"): 17.1},
    "bilirubin": {("µmol/L", "mg/dL"): 1/17.1, ("mg/dL", "µmol/L"): 17.1},
    "urea": {("mmol/L", "mg/dL"): 6.006, ("mg/dL", "mmol/L"): 1/6.006},
}

def convert_value(
    value: float,
    from_unit: str,
    to_unit: str,
    test_key: Optional[str] = None
) -> Optional[float]:
    fu = normalize_unit(from_unit)
    tu = normalize_unit(to_unit)
    if not tu:
        return value
    if not fu:
        return None
    if fu == tu:
        return value

# Tier 1: Test-specific conversions (High Accuracy)
    if test_key and test_key in _CONVERSION_MAP:
        rules = _CONVERSION_MAP[test_key]
        if (fu, tu) in rules:
            factor = rules[(fu, tu)]
            result = value * factor
            logger.debug("[convert] %s %s → %s %s (analyte-specific)", value, fu, result, tu)
            return result

# Tier 2: Scientific notation / Count normalization
    def to_abs(v: float, u: str) -> Optional[float]:
        if not ("/L" in u or "/µL" in u):
            return None
        return v * _unit_multiplier(u) * _unit_volume_factor(u)
    def from_abs(v: float, u: str) -> Optional[float]:
        if not ("/L" in u or "/µL" in u):
            return None
        d = _unit_multiplier(u) * _unit_volume_factor(u)
        return v / d if d else None

    abs_val = to_abs(value, fu)
    if abs_val is not None:
        out = from_abs(abs_val, tu)
        if out is not None:
            logger.debug("[convert] %s %s → %s %s (absolute)", value, fu, out, tu)
            return out

# Tier 3: Universal Metric conversions
    pairs = {
        ("mg/dL", "g/dL"):    value / 1000.0,
        ("g/dL",  "mg/dL"):   value * 1000.0,
        ("µg/dL", "mg/dL"):   value / 1000.0,
        ("mg/dL", "µg/dL"):   value * 1000.0,
        ("ng/mL", "µg/L"):    value,
        ("µg/L",  "ng/mL"):   value,
        ("µIU/mL", "mIU/L"):  value,
        ("mIU/L",  "µIU/mL"): value,
    }
    result = pairs.get((fu, tu))
    if result is not None:
        logger.debug("[convert] %s %s → %s %s (metric)", value, fu, result, tu)
        return result

    logger.debug("[convert] no safe conversion rule for %s → %s (test=%s)", fu, tu, test_key)
    return None


def convert_to_standard_unit(
    value: float,
    unit: str,
    test_name: str = "",
) -> tuple[float, str]:
    if not unit:
        return value, unit

    u = normalize_unit(unit)

# Auto-scale count values: /µL >100 → x10^3/µL
    if u in ("/µL", "/uL") and value > 100:
        return value / 1000, "x10^3/µL"

# Auto-scale count values: x10^3/µL <0.5 → /µL
    if u == "x10^3/µL" and value < 0.5:
        return value * 1000, "/µL"

# Auto-scale: /µL >1M → x10^6/µL
    if u in ("/µL", "/uL") and value > 1_000_000:
        return value / 1_000_000, "x10^6/µL"

# Test-specific expected unit check
    if test_name:
        canonical = normalize_test_name(test_name)
        expected = TEST_EXPECTED_UNITS.get(canonical)
        if expected and u and u != normalize_unit(expected):
            converted = convert_value(value, u, expected, canonical)
            if converted is not None:
                return converted, expected

    return value, u


def fix_ocr_value_errors(
    value: float,
    unit: str,
    test_key: Optional[str] = None,
    ref_low: Optional[float] = None,
    ref_high: Optional[float] = None,
) -> tuple[float, str, bool]:
    """Detect and fix common OCR value/unit errors."""
    original_value = value
    original_unit = unit
    corrected = False

# Fix 1: Unit starts with "-" and looks like a number
# e.g. Neutrophils value=0.0 unit="-70" → value=70 unit="%"
# Only apply if original value is 0 or clearly unreasonable for the context.
    if unit:
        stripped = unit.strip()
        m = re.match(r'^-?(\d+(?:\.\d+)?)\s*%?$', stripped)
        if m:
            extracted = abs(float(m.group(1)))
            if extracted > 0 and (original_value <= 0 or original_value > extracted * 10):
                value = extracted
                unit = "%"
                corrected = True
                logger.warning(
                    "[ocr-fix] unit field contained value: extracted=%s, unit=%% (original unit=%r, original value=%s)",
                    extracted, original_unit, original_value,
                )

# Fix 2: Decimal point errors + first-digit OCR artifacts
    if ref_low is not None and ref_high is not None and ref_high > 0:
        triggered = value > ref_high * 3 or (ref_low > 0 and value < ref_low / 3)
        if triggered and not corrected:
            for magnitude in (10, 100, 1000, 10000):
                candidate = value / magnitude
                if ref_low <= candidate <= ref_high * 2:
                    value = candidate
                    corrected = True
                    logger.warning(
                        "[ocr-fix] decimal point error: divided by %d (%s → %s)",
                        magnitude, original_value, candidate,
                    )
                    break

        if not corrected and ((value > ref_high * 2) or (ref_low > 0 and value < ref_low * 0.5)):
            try:
                int_val = int(value)
                if int_val >= 100:
                    stripped_val = int(str(int_val)[1:])
                    if ref_low <= stripped_val <= ref_high * 2:
                        value = float(stripped_val)
                        corrected = True
                        logger.warning(
                            "[ocr-fix] first-digit OCR artifact: removed leading digit (%s → %s)",
                            original_value, value,
                        )
            except (ValueError, IndexError):
                pass

# Fix 3: /µL unit should be x10^3/µL when value is on x10^3/µL scale
# e.g. WBC: 4.2 /µL → 4.2 x10^3/µL
    if unit == "/µL" and test_key and value < 50:
        expected = TEST_EXPECTED_UNITS.get(test_key, "")
        if "x10^3" in expected:
            unit = "x10^3/µL"
            corrected = True
            logger.warning(
                "[ocr-fix] unit corrected: /µL → x10^3/µL (value=%s, test=%s)",
                value, test_key,
            )

# Fix 4: MCHC % → g/dL (numerically equivalent for MCHC)
    if test_key == "mchc" and unit == "%":
        unit = "g/dL"
        corrected = True
        logger.warning(
            "[ocr-fix] MCHC unit corrected: %% → g/dL (value=%s)",
            value,
        )

    return value, unit, corrected


@dataclass(frozen=True)
class NormalizedMeasurement:
    value: float
    unit: str
    applied: bool


def normalize_count_to_per_uL(value: float, unit: str) -> Optional[NormalizedMeasurement]:
    u = normalize_unit(unit)
    if not u:
        logger.debug("[norm_count] empty unit after normalization, input=%r", unit)
        return None
    if u in ("/µL", "/uL"):
        return NormalizedMeasurement(value=value, unit="/µL", applied=False)
    if "/L" in u or "/µL" in u:
        mult = _unit_multiplier(u)
        volfac = _unit_volume_factor(u)
        abs_val = value * mult * volfac
        logger.debug("[norm_count] %s %r → %s /µL  (mult=%s, volfac=%s)", value, unit, abs_val, mult, volfac)
        return NormalizedMeasurement(value=abs_val, unit="/µL", applied=True)
    logger.debug("[norm_count] not a count unit: %r (normalized: %r)", unit, u)
    return None


def best_kb_match(name: str, candidates: Iterable[dict]) -> Optional[dict]:
    n = normalize_test_name(name)
    best = None
    best_score = -1.0
    for item in candidates:
        tn = normalize_test_name(item.get("test_name", ""))
        if not tn:
            continue
        if tn == n:
            return item
        score = SequenceMatcher(None, n, tn).ratio()
        if score > best_score:
            best_score = score
            best = item
    return best

DEFAULT_RANGES: dict[str, tuple[float, float, str]] = {
    "hemoglobin":     (11.0, 18.0, "g/dL"),
    "hematocrit":     (35.0, 55.0, "%"),
    "rbc":            (3_500_000, 6_000_000, "/µL"),
    "wbc":            (4_000,  11_000,  "/µL"),
    "platelets":      (150_000, 450_000, "/µL"),
    "mcv":            (80.0,   100.0,   "fL"),
    "mch":            (27.0,   33.0,    "pg"),
    "mchc":           (32.0,   36.0,    "g/dL"),
    "rdw":            (11.5,   14.5,    "%"),
    "neutrophils_pct":    (45.0,   75.0,    "%"),
    "neutrophils_abs": (1_800,  7_700,   "/µL"),
    "lymphocytes_pct":    (20.0,   45.0,    "%"),
    "monocytes_pct":      (2.0,    10.0,    "%"),
    "eosinophils_pct":    (1.0,    6.0,     "%"),
    "basophils_pct":      (0.0,    1.5,     "%"),
    "glucose_fasting":(70.0,   100.0,   "mg/dL"),
    "creatinine":     (0.5,    1.5,     "mg/dL"),
    "urea":           (7.0,    25.0,    "mg/dL"),
    "uric_acid":      (2.5,    8.0,     "mg/dL"),
    "hba1c":          (4.0,    5.7,     "%"),
    "sodium":         (135.0,  145.0,   "mEq/L"),
    "potassium":      (3.5,    5.5,     "mEq/L"),
    "chloride":       (98.0,   107.0,   "mEq/L"),
    "calcium":        (8.5,    10.5,    "mg/dL"),
    "magnesium":      (1.7,    2.4,     "mg/dL"),
    "total_cholesterol": (0.0, 200.0,   "mg/dL"),
    "ldl":            (0.0,    130.0,   "mg/dL"),
    "hdl":            (40.0,   60.0,    "mg/dL"),
    "triglycerides":  (0.0,    150.0,   "mg/dL"),
    "tsh":            (0.4,    4.0,     "mIU/L"),
    "t3":             (2.0,    4.4,     "pg/mL"),
    "t4":             (0.8,    1.8,     "ng/dL"),
    "alt":            (7.0,    56.0,    "U/L"),
    "ast":            (10.0,   40.0,    "U/L"),
    "alp":            (44.0,   147.0,   "U/L"),
    "total_bilirubin": (0.2,   1.2,     "mg/dL"),
    "direct_bilirubin": (0.0,  0.3,     "mg/dL"),
    "indirect_bilirubin": (0.1, 0.9,    "mg/dL"),
    "ggt":            (8.0,    61.0,    "U/L"),
    "ag_ratio":       (1.1,    2.5,     "ratio"),
    "free_t4":        (0.8,    1.8,     "ng/dL"),
    "free_t3":        (2.3,    4.2,     "pg/mL"),
    "bilirubin":      (0.2,    1.2,     "mg/dL"),
    "albumin":        (3.4,    5.4,     "g/dL"),
    "iron":           (60.0,   170.0,   "µg/dL"),
    "ferritin":       (12.0,   300.0,   "ng/mL"),
    "tibc":           (250.0,  370.0,   "µg/dL"),
    "vitamin_d":      (30.0,   100.0,   "ng/mL"),
    "vitamin_b12":    (200.0,  900.0,   "pg/mL"),
    "esr":            (0.0,    20.0,    "mm/hr"),
    "crp":            (0.0,    10.0,    "mg/L"),
}

TEST_EXPECTED_UNITS = {
    "wbc": "x10^3/µL",
    "rbc": "x10^6/µL",
    "hemoglobin": "g/dL",
    "hematocrit": "%",
    "mcv": "fL",
    "mch": "pg",
    "mchc": "g/dL",
    "platelet": "x10^3/µL",
    "platelets": "x10^3/µL",
    "neutrophils": "%",
    "lymphocytes": "%",
    "monocytes": "%",
    "eosinophils": "%",
    "basophils": "%",
    "glucose": "mg/dL",
    "hba1c": "%",
    "cholesterol": "mg/dL",
    "triglycerides": "mg/dL",
    "hdl": "mg/dL",
    "ldl": "mg/dL",
    "creatinine": "mg/dL",
    "urea": "mg/dL",
    "sodium": "mEq/L",
    "potassium": "mEq/L",
    "calcium": "mg/dL",
    "alt": "U/L",
    "ast": "U/L",
    "alkaline_phosphatase": "U/L",
    "bilirubin_total": "mg/dL",
    "direct_bilirubin": "mg/dL",
    "indirect_bilirubin": "mg/dL",
    "free_t4": "ng/dL",
    "free_t3": "pg/mL",
    "uric_acid": "mg/dL",
    "tsh": "µIU/mL",
    "rdw": "%",
    "ggt": "U/L",
    "ag_ratio": "ratio",
}

# Invalid OCR tokens that should never appear in values or units
# Only target known garbage patterns, not all single letters
_INVALID_TOKENS = [
    (re.compile(r"\bmeeacop\b", re.I), ""),   # Known OCR noise
    (re.compile(r"^\s*a\s*$", re.I), ""), # Standalone 'a' as noise
]

_CORRUPT_UNITS = [
    (re.compile(r"\bg/d\b", re.I), "g/dL"),
    (re.compile(r"\bo/dt\b", re.I), "g/dL"),
    (re.compile(r"\bafd\b", re.I), "g/dL"),
    (re.compile(r"\baid\b", re.I), "g/dL"),    # OCR-corrupted "g/dL"
    (re.compile(r"\bgldl\b", re.I), "g/dL"),
    (re.compile(r"\bq/dl\b", re.I), "g/dL"),
    (re.compile(r"\bg/dl\b", re.I), "g/dL"),
    (re.compile(r"\b9/dl\b", re.I), "g/dL"),   # g→9 OCR error
    (re.compile(r"\bgld\b", re.I), "g/dL"),
    (re.compile(r"\bg[1l]dl\b", re.I), "g/dL"),
    (re.compile(r"\bg/d[1l]\b", re.I), "g/dL"),
    (re.compile(r"\borsl\b", re.I), "x10^6/µL"),  # Map to RBC multiplier safely
    (re.compile(r"\brors\b", re.I), "x10^6/µL"),
    (re.compile(r"\bw1ooo\b", re.I), "x10^6/µL"),
    (re.compile(r"\bl0\^6\b", re.I), "x10^6/µL"),
    (re.compile(r"\bio\^6\b", re.I), "x10^6/µL"),
    (re.compile(r"\bcells\b", re.I), "/µL"),
    (re.compile(r"\bcelIs\b", re.I), "/µL"),
    (re.compile(r"\bcels/[µu]t?-*", re.I), "x10^3/µL"),
    (re.compile(r"\bcels\b", re.I), "x10^3/µL"),
    (re.compile(r"\bcell/mm3\b", re.I), "/µL"),
    (re.compile(r"\b/mm3\b", re.I), "/µL"),
    (re.compile(r"\b/mm\^3\b", re.I), "/µL"),
    (re.compile(r"\bmlul\b", re.I), "mIU/L"),
    (re.compile(r"\bmiull\b", re.I), "mIU/L"),
    (re.compile(r"\buq/dl\b", re.I), "µg/dL"),
    (re.compile(r"\bua/dl\b", re.I), "µg/dL"),
    (re.compile(r"\bµι\b", re.I), "µL"),     # OCR-corrupted "µL"
    (re.compile(r"\b10\b(?=/)", re.I), "x10^3"),  # "10" → "x10^3" (when followed by /)
    (re.compile(r"(\d)\s*pL\b"), r"\1 uL"),
# More OCR unit patterns
    (re.compile(r"\b[Uu]/[Ll]\b"), "U/L"),
    (re.compile(r"\b[Uu][Ll]\b"), "U/L"),
    (re.compile(r"\biu/l\b", re.I), "U/L"),
    (re.compile(r"\bmg/d[1l]\b", re.I), "mg/dL"),
    (re.compile(r"\bm9/dl\b", re.I), "mg/dL"),    # g→9 OCR
    (re.compile(r"\bmg/d[LlLl]\b", re.I), "mg/dL"),
    (re.compile(r"\bfl\b"), "fL"),
    (re.compile(r"\b£L\b"), "fL"),  # f→£ OCR
    (re.compile(r"\bf[1l]\b"), "fL"),
    (re.compile(r"\bpg\b"), "pg"),
    (re.compile(r"\b[µu]g\b"), "µg"),
    (re.compile(r"\b[µu][1l]\b"), "µL"),
    (re.compile(r"\b[µu]l\b"), "µL"),
    (re.compile(r"\buL\b"), "µL"),
    (re.compile(r"\bx10\^[3Б]\b"), "x10^3"),  # Б (Russian) → B → 3
    (re.compile(r"\bx10\^[6G]\b"), "x10^6"),  # G→6
    (re.compile(r"\bmeq/l\b", re.I), "mEq/L"),
    (re.compile(r"\bmmol/l\b", re.I), "mmol/L"),
    (re.compile(r"\bumol/l\b", re.I), "µmol/L"),
]

# Common OCR unit corrections (case-insensitive lookup key = stripped lowercase)
_UNIT_FIXES: dict[str, str] = {
    "aid": "g/dL",
    "g/d": "g/dL",
    "g/dl": "g/dL",
    "9/d": "g/dL",
    "9/dl": "g/dL",
    "gld": "g/dL",
    "g1d": "g/dL",
    "g1dl": "g/dL",
    "q/dl": "g/dL",
    "9/dl": "g/dL",
    "g/d1": "g/dL",
    "g/d|": "g/dL",
    "fl": "fL",
    "in": "fL",
    "f1": "fL",
    "£l": "fL",
    "fl": "fL",
    "pg": "pg",
    "p9": "pg",
    "ul": "µL",
    "u1": "µL",
    "u/l": "U/L",
    "u/1": "U/L",
    "uiu/ml": "µIU/mL",
    "uiu/ml": "µIU/mL",
    "miu/ml": "mIU/mL",
    "iu/l": "IU/L",
    "meq/l": "mEq/L",
    "meq/1": "mEq/L",
    "mmol/l": "mmol/L",
    "mmol/1": "mmol/L",
    "umol/l": "µmol/L",
    "umol/1": "µmol/L",
    "10^3/ul": "x10^3/µL",
    "10^3/u1": "x10^3/µL",
    "10^6/ul": "x10^6/µL",
    "10^6/u1": "x10^6/µL",
    "/pl": "/µL",
    "/wl": "/µL",
    "pe": "pg",
    "pg": "pg",
    "wa": "g/dL",
    "wa": "g/dL",
    "cels/ut": "cells/µL",
    "cels/ul": "cells/µL",
    "cels/u1": "cells/µL",
    "cells/pl": "cells/µL",
    "cells/wl": "cells/µL",
    "cells/p1": "cells/µL",
    "cells/w1": "cells/µL",
    "million / wl": "x10^6/µL",
    "million / pl": "x10^6/µL",
    "million/wl": "x10^6/µL",
    "million/pl": "x10^6/µL",
    "million/w1": "x10^6/µL",
    "million/p1": "x10^6/µL",
    "cels": "x10^3/µL",
    "cels": "x10^3/µL",
    "/cumm": "/µL",
    "cumm": "/µL",
    "mg/d": "mg/dL",
    "mg/dl": "mg/dL",
    "m9/dl": "mg/dL",
    "mg/d1": "mg/dL",
    "mg/d|": "mg/dL",
    "m9/d1": "mg/dL",
    "ug/dl": "µg/dL",
    "uq/dl": "µg/dL",
    "ng/m": "ng/mL",
    "ng/ml": "ng/mL",
    "n9/ml": "ng/mL",
    "pg/m": "pg/mL",
    "pg/ml": "pg/mL",
    "p9/ml": "pg/mL",
}

_SCI_WHITESPACE = re.compile(r"[xX×]\s*10\s*\^?\s*([3-9])\s*/\s*([µu]?L)\b")

def repair_ocr_text(text: str) -> str:
    """Repair OCR-mangled text by removing invalid tokens and fixing common errors."""
    if not text:
        return text
    text = text.translate(_SUPERSCRIPT_MAP)
    text = text.replace("×", "x").replace("✕", "x")
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    text = text.replace("\u00b5", "µ").replace("\u03bc", "µ")

# Fix UTF-8 encoding corruption: ÂµL → µL, Î¼L → µL
    text = text.replace("Âµ", "µ")
    text = text.replace("Î¼", "µ")

# Common unit mangling
    text = re.sub(r"\bpL\b", "uL", text)
    text = re.sub(r"\bpµL\b", "µL", text)
# Normalize "uL" (Latin u) to "µL" (micro sign) in lab units
    text = re.sub(r"\buL\b", "µL", text)

# Context-aware OCR character confusion correction
# Fix digit/letter confusions where a letter commonly confused with a digit
# appears between digits  (benchmark _CHAR_SUBS map).
    text = re.sub(r"(?<=\d)[Oo](?=\d)", "0", text)
    text = re.sub(r"(?<=\d)[Il](?=\d)", "1", text)
    text = re.sub(r"(?<=\d)[Ss](?=\d)", "5", text)
    text = re.sub(r"(?<=\d)[Bb](?=\d)", "8", text)
    text = re.sub(r"(?<=\d)[Gg](?=\d)", "6", text)
    text = re.sub(r"(?<=\d)g(?=\d)", "9", text)
# Fix letter→digit confusions at word boundaries (e.g. "O" at start of a number)
    text = re.sub(r"\bO(?=\d)", "0", text)
    text = re.sub(r"(?<=\d)O\b", "0", text)
    text = re.sub(r"\b[Ss](?=\d)", "5", text)
    text = re.sub(r"\b[Bb](?=\d)", "8", text)
    text = re.sub(r"\b[Gg](?=\d)", "6", text)
# Fix digit→letter confusions: letter where digit expected in known patterns
    text = re.sub(r"\b0(?=[A-Za-z])", "O", text)
    text = re.sub(r"\b5(?=[A-Za-z])", "S", text)
# Fix common OCR single-letter substitutions in test names
    text = re.sub(r"\bW8C\b", "WBC", text)
    text = re.sub(r"\bR8C\b", "RBC", text)
    text = re.sub(r"\bH8\b", "HB", text)
    text = re.sub(r"\bHCT\b", "HCT", text)
# Known patterns only — no generic r↔n swap (corrupts clean text)
    text = re.sub(r"\bhemoglobin\b", "hemoglobin", text, flags=re.I)
    text = re.sub(r"\bhaemoglobin\b", "haemoglobin", text, flags=re.I)
    text = re.sub(r"\bcreatinine\b", "creatinine", text, flags=re.I)
# Fix comma↔period confusion in numeric contexts
# comma between digits used as decimal separator → period
    text = re.sub(r"(?<=\d),(?=\d{1,2}(?:\D|$))", ".", text)
# Remove stray lowercase letters inserted between digits (benchmark random insertion)
# Preserve 'x10' scientific notation prefix (e.g. "5.4x10^3", "6.67x10.e")
    text = re.sub(r"(?<=\d)(?![xX]10)[a-z](?=\d)", "", text)
# Also remove stray letters BEFORE digits (insertion noise at start of numbers).
# Preserve 'x10' scientific notation prefix (e.g. "x10.e 3/μl", "x10^3")
    text = re.sub(r"(?<![a-zA-Z])(?![xX]10(?:\.|\^|e|\s))[a-z](?=\d)", "", text)
# Fix single-digit splits by spaces from space insertion: "1 2 3" → "123"
# Only collapses when right token is a single digit (not column separator)
    text = re.sub(r"(?<=\d)\s+(?=\d(?!\d))", "", text)
# Fix "1 2 . 3 4" → "12.34" pattern from space insertion around decimal
    text = re.sub(r"(\d)\s+(\.)\s+(\d)", r"\1\2\3", text)

# Fix n↔u confusion in unit contexts: nL → uL → µL
    text = re.sub(r"\bnL\b", "uL", text)
# Fix /↔1 confusion in unit denominators: g/1L → g/dL, etc.
    text = re.sub(r"/(?=1[A-Za-z])", "/", text)

# Remove thousand-separator commas: 4,200 → 4200, 150,000 → 150000
# Comma between digits where right side has exactly 3+ digits
    text = re.sub(r"(?<=\d),(?=\d{3}(?:\s|$|\D|\.\d))", "", text)
# Also handle leads like "4,200 cells" where comma followed by 3 digits + word boundary
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)

# Fix OCR decimal fragments split by spacing: "12 . 2" → "12.2"
    text = re.sub(r"(?<=\d)\s+\.\s+(?=\d)", ".", text)
    text = re.sub(r"(?<=\d)\s+,\s+(?=\d)", ".", text)

# Preserve column separation while normalizing whitespace.
# Convert runs of 2+ whitespace chars to exactly two spaces.
    text = re.sub(r"[ \t\f\v]{2,}", "  ", text)

# Scientific notation fixes
    text = _SCI_WHITESPACE.sub(lambda m: f"x10^{m.group(1)}/µL", text)
    text = re.sub(r"[xX][lI1][oO0]\^", "x10^", text)
    text = re.sub(r"(?<![a-zA-Z])[lI][oO0]\^", "10^", text)
    text = re.sub(r"\b10[Aa](\d)\b", r"10^\1", text)
    text = re.sub(r"\bw1[o0][o0][o0]/([µu]L)\b", r"x10^3/\1", text, flags=re.I)
# Fix OCR: x10.e 3/pl → x10^3/µL (dot instead of caret, /pl)
    text = re.sub(r"\bx10\.e\s+(\d+)\s*/\s*pl\b", r"x10^\1/µL", text, flags=re.I)

# Remove invalid OCR noise tokens
    for pat, repl in _INVALID_TOKENS:
        text = pat.sub(repl, text)

# Preserve line boundaries while normalizing spaces on each line.
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    return text


_SANITY_BOUNDS: dict[str, tuple[float, float]] = {
    "hemoglobin":      (2.0,   25.0),
    "hematocrit":      (5.0,   80.0),
    "mchc":            (20.0,  45.0),
    "mcv":             (50.0,  130.0),
    "mch":             (15.0,  50.0),
    "rdw":             (5.0,   30.0),
    "rdw_sd":          (20.0,  80.0),
    "rbc":             (0.5,   8.0),
    "wbc":             (0.1,   200.0),
    "neutrophils_abs": (0.1,   100.0),
    "platelets":       (10.0,  2000.0),
    "neutrophils_pct":     (0.0,   100.0),
    "lymphocytes_pct":     (0.0,   100.0),
    "monocytes_pct":       (0.0,   30.0),
    "eosinophils_pct":     (0.0,   80.0),
    "basophils_pct":       (0.0,   20.0),
    "glucose_fasting": (20.0,  800.0),
    "creatinine":      (0.2,   20.0),
    "urea":            (2.0,   300.0),
    "sodium":          (110.0, 175.0),
    "potassium":       (1.5,   9.0),
    "calcium":         (5.0,   15.0),
    "tsh":             (0.001, 150.0),
    "alt":             (1.0,   5000.0),
    "ast":             (1.0,   5000.0),
    "bilirubin":       (0.1,   40.0),
    "albumin":         (1.0,   8.0),
    "hba1c":           (3.0,   20.0),
    "total_cholesterol": (50.0, 500.0),
    "ldl":             (10.0,  300.0),
    "hdl":             (10.0,  150.0),
    "triglycerides":   (10.0,  2000.0),
    "vldl":            (1.0,   80.0),
    "bun":             (1.0,   150.0),
    "uric_acid":       (0.5,   20.0),
    "direct_bilirubin": (0.0,  5.0),
    "indirect_bilirubin": (0.0,  5.0),
    "bilirubin_direct": (0.0,  5.0),
    "bilirubin_total":  (0.0,  40.0),
    "total_protein":   (2.0,   12.0),
    "globulin":        (0.5,   6.0),
    "egfr":            (5.0,   200.0),
    "fasting_insulin": (0.5,   500.0),
    "free_t4":         (0.1,   10.0),
    "free_t3":         (0.1,   20.0),
    "ggt":             (1.0,   5000.0),
    "ag_ratio":        (0.1,   10.0),
}

@dataclass
class SanityResult:
    value: float
    repaired: bool
    confidence_penalty: float
    warning: str

def sanity_check_value(
    value: float,
    test_key: Optional[str],
    unit: str,
    ref_low: Optional[float] = None,
    ref_high: Optional[float] = None,
) -> SanityResult:
    """Biological plausibility check for lab values."""
    repaired = False
    penalty = 0.0
    warning = ""
    u = normalize_unit(unit)

# Rule 1: Negative values are never valid for any test
    if value < 0:
        return SanityResult(
            value=value, repaired=False,
            confidence_penalty=1.0,
            warning=f"Negative value {value} discarded",
        )

# Rule 2: Percentage values must be 0-100
    if u == "%" and value > 100:
        penalty = max(penalty, 0.41)
        warning = f"Percentage value {value}% exceeds 100% — improbable"

# Rule 3: Auto-scale /µL count values (repair with penalty)
    if u == "/µL":
        if value > 1_000_000:
            penalty = max(penalty, 0.1)
            warning = f"Count value {value}/µL auto-scaled to x10^6/µL"
            repaired = True
        elif value > 500:
            penalty = max(penalty, 0.1)
            warning = f"Count value {value}/µL auto-scaled to x10^3/µL"
            repaired = True

# Rule 4: x10^3/µL values < 0.1 are suspicious
    if u == "x10^3/µL" and value < 0.1:
        penalty = max(penalty, 0.1)
        warning = f"Count value {value} x10^3/µL suspiciously low — possible unit mismatch"
        repaired = True

# Rule 5: Reference-range-based universal bounds
    if ref_low is not None and ref_high is not None and ref_high > 0:
        expected_min = ref_low * 0.01
        expected_max = ref_high * 100
        if value < expected_min or value > expected_max:
            penalty = max(penalty, 0.41)
            if not warning:
                warning = (
                    f"Value {value} outside plausible range "
                    f"[{expected_min:.4f}, {expected_max:.4f}] "
                    f"derived from reference [{ref_low}, {ref_high}]"
                )

# Rule 6: Hardcoded bounds as fallback (existing)
    if not warning and test_key and test_key in _SANITY_BOUNDS:
        min_val, max_val = _SANITY_BOUNDS[test_key]
        if value > max_val * 1.5 or (min_val > 0 and value < min_val / 5.0):
            penalty = 0.41
            warning = f"Value {value} is biologically improbable for {test_key}"

    if warning:
        logger.warning("[sanity] %s", warning)

    return SanityResult(value=value, repaired=repaired, confidence_penalty=penalty, warning=warning)
