
"""
Production-grade OCR-tolerant lab normalization pipeline.

Pipeline order:
  raw text → repair_ocr_text() → normalize_test_name() / normalize_unit()
           → normalize_count_to_per_uL() / convert_value()
           → parse_reference_range() → classify_numeric()
"""
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
    ]
    for pat, replacement in _ocr_words:
        s = pat.sub(replacement, s)
    s = re.sub(r"\s*-\s*", "-", s)
    return s.strip()


def normalize_unit(unit: str) -> str:
    s = (unit or "").strip()
    if not s:
        return ""
    s = clean_ocr_unit(s)
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
                return ParsedRange(low=None, high=val, unit=unit)
            return ParsedRange(low=val, high=None, unit=unit)
    parts = re.split(r"\s*-\s*", core)
    if len(parts) >= 2:
        try:
            low = _to_float(parts[0])
            high = _to_float(parts[1])
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

# Invalid OCR tokens that should never appear in values or units
# Only target known garbage patterns, not all single letters
_INVALID_TOKENS = [
    (re.compile(r"\bmeeacop\b", re.I), ""),   # Known OCR noise
    (re.compile(r"^\s*a\s*$", re.I), ""), # Standalone 'a' as noise
]

_CORRUPT_UNITS = [
    (re.compile(r"\bo/dt\b", re.I), "g/dL"),
    (re.compile(r"\bafd\b", re.I), "g/dL"),
    (re.compile(r"\baid\b", re.I), "g/dL"),    # OCR-corrupted "g/dL"
    (re.compile(r"\bgldl\b", re.I), "g/dL"),
    (re.compile(r"\bq/dl\b", re.I), "g/dL"),
    (re.compile(r"\borsl\b", re.I), "x10^6/µL"),  # Map to RBC multiplier safely
    (re.compile(r"\brors\b", re.I), "x10^6/µL"),
    (re.compile(r"\bw1ooo\b", re.I), "x10^6/µL"),
    (re.compile(r"\bl0\^6\b", re.I), "x10^6/µL"),
    (re.compile(r"\bio\^6\b", re.I), "x10^6/µL"),
    (re.compile(r"\bcells\b", re.I), "/µL"),
    (re.compile(r"\bcelIs\b", re.I), "/µL"),
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
]

_SCI_WHITESPACE = re.compile(r"[xX×]\s*10\s*\^?\s*([3-9])\s*/\s*([µu]?L)\b")

def repair_ocr_text(text: str) -> str:
    """Repair OCR-mangled text by removing invalid tokens and fixing common errors."""
    if not text:
        return text
    text = text.translate(_SUPERSCRIPT_MAP)
    text = text.replace("×", "x").replace("✕", "x")
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    text = text.replace("\u00b5", "µ").replace("\u03bc", "µ")
    
    # Common unit mangling
    text = re.sub(r"\bpL\b", "uL", text)
    text = re.sub(r"\bpµL\b", "µL", text)

    # Preserve OCR-decimal fragments that were split by spacing: "12 . 2" → "12.2".
    text = re.sub(r"(?<=\d)\s*[\.,]\s*(?=\d)", ".", text)
    
    # Preserve column separation while normalizing whitespace.
    # Convert runs of 2+ whitespace chars to exactly two spaces.
    text = re.sub(r"[ \t\f\v]{2,}", "  ", text)
    
    # Scientific notation fixes
    text = _SCI_WHITESPACE.sub(lambda m: f"x10^{m.group(1)}/{m.group(2)}", text)
    text = re.sub(r"[xX][lI1][oO0]\^", "x10^", text)
    text = re.sub(r"(?<![a-zA-Z])[lI][oO0]\^", "10^", text)
    text = re.sub(r"\b10[Aa](\d)\b", r"10^\1", text)
    text = re.sub(r"\bw1[o0][o0][o0]/([µu]L)\b", r"x10^3/\1", text, flags=re.I)
    
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
}

@dataclass
class SanityResult:
    value: float
    repaired: bool
    confidence_penalty: float
    warning: str

def sanity_check_value(value: float, test_key: Optional[str], unit: str) -> SanityResult:
    """
    Sanity check for biological plausibility.
    
    MEDICAL SAFETY RULE: 
    Never automatically repair patient numeric values. 
    If a value is biologically implausible (e.g., Potassium 15.0), 
    flag it with a high confidence penalty to force REVIEW_REQUIRED status.
    """
    repaired = False
    penalty = 0.0
    warning = ""
    
    if test_key and test_key in _SANITY_BOUNDS:
        min_val, max_val = _SANITY_BOUNDS[test_key]

        # Flag suspicious values (potential OCR damage or critical medical state)
        # We use a 1.5x buffer for extreme clinical cases
        if value > max_val * 1.5 or (min_val > 0 and value < min_val / 5.0):
            penalty = 0.41  # Force confidence below 0.60 for Review Required
            warning = f"Value {value} is biologically improbable for {test_key}. Potential OCR error or critical condition."
            logger.warning("[sanity] %s", warning)

    return SanityResult(value=value, repaired=False, confidence_penalty=penalty, warning=warning)

