"""Strict lab report parser with dictionary-based validation"""
from __future__ import annotations

import logging
import re

from core.normalization import repair_ocr_text, normalize_unit

logger = logging.getLogger(__name__)

# 1.  Canonical Lab Test Dictionary
# Maps canonical_key -> list of lowercase aliases (including common OCR variants)
_LAB_TEST_NAMES: dict[str, list[str]] = {
# Complete Blood Count
    "hemoglobin": [
        "hemoglobin", "haemoglobin", "hb", "hgb", "hemoglobn", "hemglobin",
        "haemoglobn", "hemog10bin", "hemog1obin",
    ],
    "hematocrit": [
        "hematocrit", "haematocrit", "hct", "pcv", "packed cell volume",
        "hematort", "haematort", "hemotocrit",
    ],
    "wbc": [
        "wbc", "white blood cell", "white blood cells",
        "white cell", "white cells",
        "leukocyte", "leukocytes", "leucocyte", "leucocytes",
        "total leucocyte count", "tlc", "total leukocyte count",
        "w8c",
    ],
    "rbc": [
        "rbc", "red blood cell", "red blood cells", "red cell count",
        "erythrocyte", "erythrocytes", "r8c",
    ],
    "mcv": ["mcv", "mean corpuscular volume"],
    "mch": ["mch", "mean corpuscular hemoglobin"],
    "mchc": ["mchc", "mean corpuscular hemoglobin concentration"],
    "rdw": ["rdw", "rdw-cv", "red cell distribution width", "rdw cv", "row-cv"],
    "rdw_sd": ["rdw sd"],
    "platelet_count": [
        "platelet count", "platelets", "plt", "platelet",
        "thrombocyte", "thrombocytes",
        "total platelet count",
    ],
    "mpv": ["mpv", "mean platelet volume"],
    "pdw": ["pdw", "platelet distribution width"],
    "mpv": ["mpv", "mean platelet volume", "mean platelet volume (mpv)"],
    "pdw": ["pdw", "platelet distribution width"],
    "neutrophils": [
        "neutrophils", "neutrophil", "neutrophil count",
        "absolute neutrophil count", "anc",
        "neutrophils absolute", "neut",
    ],
    "lymphocytes": [
        "lymphocytes", "lymphocyte", "lymphocyte count",
        "absolute lymphocyte count", "alc",
        "lymphocytes absolute", "lymp", "lymph",
    ],
    "monocytes": [
        "monocytes", "monocyte", "monocyte count",
        "absolute monocyte count",
        "monocytes absolute", "mono",
    ],
    "eosinophils": [
        "eosinophils", "eosinophil", "eosinophil count",
        "absolute eosinophil count",
        "eosinophils absolute", "eo", "eos",
    ],
    "basophils": [
        "basophils", "basophil", "basophil count",
        "absolute basophil count",
        "basophils absolute", "baso",
    ],
# Biochemistry
    "alt": ["alt", "alanine aminotransferase", "sgpt", "gpt", "alanine transaminase"],
    "ast": ["ast", "aspartate aminotransferase", "sgot", "got", "aspartate transaminase"],
    "alp": ["alp", "alkaline phosphatase", "alk phos", "alkaline phosphatise"],
    "ggt": ["ggt", "gamma gt", "gamma glutamyl transferase", "ggtp", "gamma-glutamyl transferase"],
    "bilirubin_total": ["total bilirubin", "bilirubin total", "bilirubin"],
    "bilirubin_direct": ["direct bilirubin", "bilirubin direct", "conjugated bilirubin"],
    "bilirubin_indirect": ["indirect bilirubin", "bilirubin indirect", "unconjugated bilirubin"],
    "total_protein": ["total protein", "protein total", "serum total protein"],
    "albumin": ["albumin", "serum albumin", "s.albumin"],
    "globulin": ["globulin", "serum globulin"],
    "ag_ratio": ["a/g ratio", "albumin globulin ratio", "ag ratio", "a g ratio"],
    "creatinine": ["creatinine", "creat", "serum creatinine"],
    "bun": ["bun", "blood urea nitrogen"],
    "urea": ["urea", "blood urea", "serum urea"],
    "uric_acid": ["uric acid", "urate", "serum uric acid"],
    "sodium": ["sodium", "na", "serum sodium"],
    "potassium": ["potassium", "k", "serum potassium"],
    "chloride": ["chloride", "cl", "serum chloride"],
    "bicarbonate": ["bicarbonate", "hco3", "co2", "carbon dioxide"],
    "calcium": ["calcium", "ca", "serum calcium"],
    "phosphorus": ["phosphorus", "phosphate", "p", "serum phosphorus"],
    "magnesium": ["magnesium", "mg", "serum magnesium"],
# Lipid Profile
    "total_cholesterol": ["total cholesterol", "cholesterol", "chol", "serum cholesterol"],
    "hdl": ["hdl", "hdl cholesterol", "high density lipoprotein"],
    "ldl": ["ldl", "ldl cholesterol", "low density lipoprotein"],
    "vldl": ["vldl", "vldl cholesterol"],
    "triglycerides": ["triglycerides", "triglyceride", "tg", "trig"],
    "non_hdl": ["non hdl", "non hdl cholesterol", "non-hdl"],
# Thyroid
    "tsh": ["tsh", "thyroid stimulating hormone", "thyrotropin"],
    "t3": ["t3", "triiodothyronine", "free t3", "ft3"],
    "t4": ["t4", "thyroxine", "free t4", "ft4"],
# Diabetes
    "hba1c": [
        "hba1c", "hb a1c", "glycated hemoglobin", "glycosylated hemoglobin",
        "a1c", "hba1c %",
    ],
    "fasting_glucose": [
        "fasting glucose", "fasting blood sugar", "fbs",
        "fasting sugar", "fasting plasma glucose",
    ],
    "postprandial_glucose": [
        "postprandial glucose", "ppbs",
        "post prandial blood sugar", "pp sugar",
        "post meal glucose",
    ],
    "random_glucose": [
        "random glucose", "random blood sugar", "rbs",
        "casual plasma glucose",
    ],
# Inflammation / Immunology
    "crp": ["crp", "c reactive protein", "c-reactive protein"],
    "esr": ["esr", "erythrocyte sedimentation rate"],
    "ferritin": ["ferritin", "serum ferritin"],
    "vitamin_b12": ["vitamin b12", "b12", "vit b12", "cyanocobalamin"],
    "vitamin_d": [
        "vitamin d", "25 oh vitamin d", "25-hydroxy vitamin d",
        "vit d", "25-hydroxyvitamin d",
    ],
    "iron": ["iron", "serum iron"],
    "tibc": ["tibc", "total iron binding capacity"],
    "transferrin_saturation": ["transferrin saturation", "iron saturation", "transferrin sat"],
# Cardiac / Enzymes
    "troponin_i": ["troponin i", "trop i"],
    "troponin_t": ["troponin t", "trop t"],
    "ck_mb": ["ck mb", "ck-mb"],
    "ck": ["ck", "creatine kinase", "cpk", "total cpk"],
    "ldh": ["ldh", "lactate dehydrogenase"],
# Coagulation
    "pt": ["pt", "prothrombin time"],
    "inr": ["inr", "international normalized ratio"],
    "aptt": ["aptt", "activated partial thromboplastin time", "ptt"],
    "fibrinogen": ["fibrinogen"],
    "d_dimer": ["d dimer", "d-dimer"],
# Urine
    "urine_ph": ["urine ph", "ph urine"],
    "urine_specific_gravity": ["urine specific gravity", "specific gravity"],
    "urine_protein": ["urine protein", "protein urine", "urine albumin"],
    "urine_glucose": ["urine glucose", "glucose urine"],
    "urine_ketones": ["urine ketones", "ketones urine"],
    "urine_blood": ["urine blood", "blood urine"],
    "urine_bilirubin": ["urine bilirubin", "bilirubin urine"],
    "urine_urobilinogen": ["urine urobilinogen", "urobilinogen"],
    "urine_nitrite": ["urine nitrite", "nitrite"],
    "urine_leukocytes": ["urine leukocytes", "leukocytes urine", "pus cells"],
# Tumor Markers
    "psa": ["psa", "prostate specific antigen"],
    "cea": ["cea", "carcinoembryonic antigen"],
    "afp": ["afp", "alpha fetoprotein"],
    "ca125": ["ca 125", "ca125"],
    "ca199": ["ca 19 9", "ca199"],
    "ca153": ["ca 15 3", "ca153"],
    "beta_hcg": ["beta hcg", "b hcg", "beta hcg total"],
# Other
    "amylase": ["amylase", "serum amylase"],
    "lipase": ["lipase", "serum lipase"],
    "lactate": ["lactate", "lactic acid"],
    "ammonia": ["ammonia", "nh3", "serum ammonia"],
    "homocysteine": ["homocysteine"],
    "folate": ["folate", "folic acid"],
    "blood_group": ["blood group", "blood type", "abo group"],
    "rh_factor": ["rh factor", "rh"],
}

# Build reverse lookup: lowercase alias -> canonical key
_ALIAS_TO_KEY: dict[str, str] = {}
for key, aliases in _LAB_TEST_NAMES.items():
    for alias in aliases:
        _ALIAS_TO_KEY[alias] = key
    _ALIAS_TO_KEY[key.replace("_", " ")] = key


# 2.  Known Units (surface forms — no normalization applied during detection)
_KNOWN_UNITS: set[str] = {
# Chemistry
    "g/dL", "g/dl", "gm/dl", "gm%", "g%", "gm/dL",
    "mg/dL", "mg/dl",
    "mmol/L", "mmol/l",
    "µmol/L", "umol/l",
    "IU/L", "iu/l", "u/l", "u/L", "U/L",
    "mIU/L", "miu/l",
    "mIU/mL", "miu/ml",
    "µIU/mL", "uiu/ml", "µiu/ml",
    "ng/mL", "ng/ml",
    "ng/dL", "ng/dl",
    "pg/mL", "pg/ml",
    "µg/L", "ug/l",
    "µg/mL", "ug/ml",
    "µg/dL", "ug/dl",
    "mEq/L", "meq/l",
    "g/L", "g/l",
    "mg/L", "mg/l",
    "nmol/L", "nmol/l",
    "pmol/L", "pmol/l",
# Hematology
    "fL", "fl",
    "pg",
    "%",
    "x10^3/uL", "x10^3/µL", "x10^3/ul",
    "x10^6/uL", "x10^6/µL", "x10^6/ul",
    "x10^9/L", "x10^9/µL",
    "10^3/uL", "10^3/µL",
    "10^6/uL", "10^6/µL",
    "/uL", "/µL", "/ul",
    "/cumm", "/cu mm", "/cmm", "/mm3", "cumm",
    "cells/uL", "cells/µL",
    "Lakh cells", "lakh cells", "Lakhs cells",
    "million/uL", "million/µL",
    "thousand/uL", "thousand/µL",
    "K/uL", "k/ul",
    "lakh/cumm",
# OCR variants of x10^3/µL etc.
    "x10.e 3/pl", "x10.e 3/µL",
    "x10.e 6/uL", "x10.e 6/µL",
# OCR common unit manglings — multi-token forms for 3-token matching
    "/pl", "/wl",
    "pe",
    "cells/pl", "cells/wl",
    "million/pl", "million/wl",
    "million / wl", "million / pl",
    "cels/ut", "cels/µL",
    "cels/ul",
    "wa",
# Special
    "ratio",
    "index",
    "mg/g",
# ESR / Time
    "mm/hr", "mm/h", "mm/hour",
    "mm 1st hour", "mm 1st hr",
    "min", "minutes",
    "sec", "seconds",
# Hormone
    "mIU/ml",
    "µIU/ml",
}

_KNOWN_UNITS_LOWER = {u.lower().replace(" ", "") for u in _KNOWN_UNITS}


def _is_unit_token(token: str) -> bool:
    """Check if token is a known laboratory unit (exact or normalized)."""
    t = token.strip()
    if not t:
        return False
# Direct surface-form match
    if t.lower().replace(" ", "") in _KNOWN_UNITS_LOWER:
        return True
# Fallback: normalize and check
    n = normalize_unit(t)
    if n and n.lower().replace(" ", "") in _KNOWN_UNITS_LOWER:
        return True
    return False


# 3.  Metadata / Header / Rejection Patterns

_METADATA_KEYWORDS: list[str] = [
# Contact
    "phone", "mobile", "contact", "email", "e-mail", "website", "fax",
# Address
    "address", "nagar", "road", "street", "colony", "society", "area", "sector",
# Patient / Report IDs — use FULL phrases only to avoid killing real test lines
    "patient id", "patient name", "patient no", "patient number",
    "uhid", "unique health id", "health id",
    "report id", "report no", "report number",
    "barcode", "bar code", "qrcode", "qr code",
# Doctor / Referral
    "doctor", "consultant", "ref by", "referred by", "ref dr",
# Demographics — use full phrases to avoid catching numeric lab values
    "date of birth", "patient age", "patient gender", "patient sex",
# Dates / Times
    "collection date", "collection at", "collected at",
    "collection centre", "collection center",
    "report date", "reported at", "reported on", "reporting date",
# Sample / Specimen — full phrases only (not bare "sample" which can appear in headers)
    "specimen type", "specimen collected", "specimen received",
    "sample collected", "sample received", "sample type",
# Facility / Lab — use full phrases so bare "lab" or "name" don't kill test lines
    "hospital name", "laboratory name", "lab address",
# Interpretation
    "interpretation", "signature", "remarks", "comments",
    "generated on", "generated at", "printed on", "printed at",
# Page / Invoice
    "invoice no", "invoice number", "registration no", "registration number",
# Registration numbers
    "reg no", "reg id", "reg number",
    "ip no", "op no",
# Column headers
    "ref range", "normal range", "normal value",
    "test name", "test description", "test parameter",
    "observed value", "expected value",
# Clinical history
    "clinical history", "clinical details",
    "investigation requested",
# Authorization
    "forwarded", "authorized by",
# Misc
    "prepared by", "reviewed by",
    "collected on", "received on",
# Hospital / lab names commonly appearing in headers
    "metropolis", "thyrocare", "lal pathlabs", "srl diagnostics",
    "apollo diagnostics", "suburban diagnostics",
    "tata medical", "fortis", "max health", "medanta",
    "health cart", "1mg", "pharmeasy", "netmeds", "practo",
    "clarity medical", "lifecell", "agilus",
]

_META_RE = re.compile(
    r"(?:" + "|".join(
        re.escape(kw) if not kw.endswith("\\.") else kw
        for kw in _METADATA_KEYWORDS
    ) + r")",
    re.I,
)

_SECTION_HEADERS: list[str] = [
    "haematology", "hematology", "biochemistry", "immunology", "microbiology",
    "serology", "pathology", "histopathology", "cytopathology",
    "blood bank", "blood transfusion", "transfusion medicine",
    "complete blood count", "cbc", "hemogram", "blood count",
    "liver function test", "lft", "hepatic function",
    "kidney function test", "kft", "renal function test", "rft",
    "lipid profile", "lipid panel", "lipid study",
    "thyroid profile", "thyroid panel", "thyroid function",
    "thyroid function test", "tft",
    "iron studies", "iron profile", "iron deficiency profile",
    "diabetes profile", "diabetes panel", "diabetic profile",
    "electrolyte panel", "electrolyte profile", "metabolic panel",
    "basic metabolic panel", "bmp",
    "comprehensive metabolic panel", "cmp",
    "cardiac profile", "cardiac panel", "cardiac markers",
    "coagulation profile", "coagulation panel", "coagulation study",
    "urine analysis", "urine routine", "urine examination", "urinalysis",
    "urine microscopy", "urine culture",
    "stool analysis", "stool examination", "stool culture",
    "hormonal assay", "hormone profile",
    "tumor markers", "tumour markers",
    "test description", "test name", "test parameter",
    "result", "results",
    "reference range", "reference ranges", "ref range", "normal range",
    "unit", "units",
    "biochemical", "hematological", "serolog",
    "normal value", "observed value", "expected value",
    "parameter", "investigation requested",
]

_HEADER_RE = re.compile(
    r"^(?:\s*(?:" + "|".join(re.escape(h) for h in _SECTION_HEADERS) + r")\s*)$",
    re.I,
)

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
# Phone patterns that won't match lab reference ranges like "4000-10000"
# Pattern A: 10+ consecutive digits (no separators) — e.g. "9876543210"
# Pattern B: precisely grouped like (123) 456-7890 or 123-456-7890
# Pattern C: +91-XXXXXXXXXX (country code with 10 consecutive digits)
_PHONE_RE = re.compile(
    r"\d{10,}"                                              # 10+ consecutive digits
    r"|\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}"                   # (XXX) XXX-XXXX
    r"|\+\d{1,3}[-.\s]?\d{10}"                              # +91-XXXXXXXXXX
)

_DATE_LINE_RE = re.compile(
    r"^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}$"
    r"|^\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}$"
    r"|^\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?$",
)

_DATE_MONTH_RE = re.compile(
    r"^\d{1,2}\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", re.I,
)
_DATE_MONTH2_RE = re.compile(
    r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s*\d{4}$", re.I,
)


# 4.  Reference Range Patterns

def _is_ref_range_token(token: str) -> bool:
    """Check if token is a reference range pattern."""
    t = token.strip().strip("()[]{}").strip()
    if not t:
        return False

# Range: 13-17, 4.0-11.0, 150000-410000
    if re.match(r"^[<>≤≥]?\s*[\d,]+\.?\d*\s*[-–]\s*[\d,]+\.?\d*%?$", t):
        return True

# Threshold: <5, >10, ≤5, ≥10, <5
    if re.match(r"^[<>≤≥]\s*[\d,]+\.?\d*%?$", t):
        return True

# Qualitative reference values
    if t.lower() in {
        "negative", "positive", "normal", "abnormal",
        "reactive", "non reactive", "nonreactive",
        "nil", "trace",
    }:
        return True

    return False


def _is_qualitative_value(token: str) -> bool:
    t = token.strip().lower()
    return t in {
        "negative", "positive", "normal", "abnormal",
        "reactive", "non reactive", "nonreactive",
        "nil", "trace", "detected", "not detected",
        "present", "absent",
    }


def _extract_numeric(token: str) -> float | None:
    """Extract numeric value, handling <, >, ≤, ≥ prefixes, commas, and trailing %."""
    t = token.strip().strip("()[]{}")
    if not t:
        return None
# Strip trailing % for numeric extraction
    pct = t.endswith('%')
    t_clean = t.rstrip('%') if pct else t
# Try direct parse
    try:
        return float(t_clean.replace(",", ""))
    except ValueError:
        pass
# Try with comparison prefix
    m = re.match(r"^[<>≤≥]\s*([\d,]+\.?\d*)$", t_clean)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return None


def _normalize_ref_range(ref: str) -> str:
    """Normalize reference range format: remove spaces around dash, collapse whitespace."""
    s = ref.strip().strip("()[]{}").strip()
    s = re.sub(r"\s*[-–]\s*", "-", s)
    s = re.sub(r"\s*to\s+", "-", s)
    return s


# 5.  OCR Cleaning

_LEADING_NOISE_RE = re.compile(r"^[\*\-\•'\"\`®€©●■►◆◇▸▪→⇒≈✦✧⬤○●]+")
_TRAILING_PAGE_RE = re.compile(r"\s*page\s*\d+\s*$", re.I)
_TRAILING_FRAGMENT = re.compile(r"\s*\d{1,2}\s*/\s*\d{1,4}\s*$")


def _clean_line(line: str) -> str:
    s = (line or "").strip()
    if not s:
        return ""
    s = _LEADING_NOISE_RE.sub("", s)
# Preserve # and % prefixes for hematology differential test names
# e.g. "#NEUT" (absolute) and "% Neut" (percentage) — the resolver
# uses these prefixes to distinguish neutrophils_abs from neutrophils_pct.
    prefix = ""
    m_prefix = re.match(r"^([#%]\s*?)(?=NEUT|LYMP|MONO|EOS|BASO|neut|lymp|mono|eos|baso)", s, re.I)
    if m_prefix:
        prefix = m_prefix.group(1)
        s = s[len(prefix):]
    s = re.sub(r"^[^A-Za-z0-9]+", "", s)
    s = prefix + s
    s = _TRAILING_PAGE_RE.sub("", s)
    s = _TRAILING_FRAGMENT.sub("", s)
# Preserve double-space column separators while collapsing other whitespace
    s = re.sub(r"[ \t\f\v]{2,}", "  ", s).strip()
    return s


# 6.  Lab Test Name Lookup

def _lookup_test(name_str: str) -> str | None:
    """Find canonical key for a test name (exact fuzzy match)."""
    n = name_str.strip().lower()
    n = re.sub(r"\s+", " ", n)
# Exact match
    if n in _ALIAS_TO_KEY:
        return _ALIAS_TO_KEY[n]
# Strip trailing non-alpha chars (e.g. "Hb :" -> "hb")
    n_clean = re.sub(r"[^a-z0-9\s]", "", n).strip()
    if n_clean in _ALIAS_TO_KEY:
        return _ALIAS_TO_KEY[n_clean]
# Try removing trailing single-letter artifacts
    n_short = re.sub(r"\s+[a-z]\s*$", "", n_clean).strip()
    if n_short and n_short != n_clean and n_short in _ALIAS_TO_KEY:
        return _ALIAS_TO_KEY[n_short]
    return None


# 7.  Core Parsing Strategies


def _extract_ref_range_backward(tokens: list[str], idx: int) -> tuple[str, int] | None:
    """Extract a ref range ending at token idx"""
# Single-token: "13-17" or "(4.0-11.0)"
    cleaned = tokens[idx].strip("()[]{}").strip()
    if _is_ref_range_token(cleaned):
        return cleaned, idx - 1

# Multi-token: "31.5 - 34.5"  (three tokens: lower, dash, upper)
    if (idx >= 2
            and _extract_numeric(tokens[idx]) is not None
            and tokens[idx - 1] in ("-", "–", "—")
            and _extract_numeric(tokens[idx - 2]) is not None):
        return f"{tokens[idx - 2]}-{tokens[idx]}", idx - 3

# Defensive: idx points to dash, upper bound is to the right
    if (idx >= 1 and idx + 1 < len(tokens)
            and tokens[idx] in ("-", "–", "—")
            and _extract_numeric(tokens[idx - 1]) is not None
            and _extract_numeric(tokens[idx + 1]) is not None):
        return f"{tokens[idx - 1]}-{tokens[idx + 1]}", idx - 1

    return None


def _backward_token_parse(tokens: list[str]) -> dict | None:
    """Parse tokens right-to-left handling all reference range orderings."""
    if len(tokens) < 2:
        return None

# Clean parentheses from each token (common for reference ranges)
    cleaned = [t.strip("()[]{}").strip() for t in tokens]

    idx = len(cleaned) - 1
    unit = ""
    ref_range = ""
    value: float | None = None
    qual_value = ""
    flag = ""

# Phase 1: Handle trailing flag (H / L / N)
    _FLAG_SET = {"H", "L", "N", "HIGH", "LOW", "NORMAL"}
    _FLAG_OCR = {"TOW", "NORMA", "NORM", "WC", "WICH", "LOW", "HIGH", "NORMAL"}
    if idx >= 0:
        upper = cleaned[idx].upper()
        if upper in _FLAG_SET or upper in _FLAG_OCR:
            flag = tokens[idx]
            idx -= 1

# Phase 2: Handle trailing dash (truncated ref range)
# e.g. "4.800 -" or "40 -" where the upper bound is missing
    if idx >= 1 and cleaned[idx] in ("-", "–", "—"):
        prev_val = _extract_numeric(tokens[idx - 1])
        if prev_val is not None:
            ref_range = tokens[idx - 1] + "-"
            idx -= 2

    if idx < 0:
        return None

# Phase 3: Identify the last meaningful token
    last_cleaned = cleaned[idx]
    is_unit = _is_unit_token(last_cleaned)
    is_ref = _is_ref_range_token(last_cleaned)
    is_value = _extract_numeric(last_cleaned) is not None

# Phase 3a: Last token is a unit
# Pattern: ... VALUE [REF] UNIT
    if is_unit:
        unit = tokens[idx]
        idx -= 1
        if idx >= 0 and _is_ref_range_token(cleaned[idx]):
            ref_range = tokens[idx]
            idx -= 1
        if idx >= 0:
            v = _extract_numeric(tokens[idx])
            if v is not None:
                value = v
                if not unit and tokens[idx].rstrip(')').endswith('%'):
                    unit = '%'
                idx -= 1

# Phase 3b: Last token is a ref range
# Pattern: ... VALUE [UNIT] REF
    elif is_ref:
        ref_range = last_cleaned
        idx -= 1
        if idx >= 0 and _is_unit_token(tokens[idx]):
            unit = tokens[idx]
            idx -= 1
        if idx >= 0:
            v = _extract_numeric(tokens[idx])
            if v is not None:
                value = v
                if not unit and tokens[idx].rstrip(')').endswith('%'):
                    unit = '%'
                idx -= 1

# Phase 3c: Last token is a numeric value
# Pattern: ... REF UNIT VALUE   or   ... REF VALUE
# Also handles split ranges: ... VALUE UNIT lower - upper
    elif is_value:
# Check for split ref range first: "lower - upper" (three tokens)
        if (idx >= 2
                and tokens[idx - 1] in ("-", "–", "—")
                and _extract_numeric(tokens[idx - 2]) is not None):
            ref_range = f"{tokens[idx - 2]}-{tokens[idx]}"
            idx -= 3
# Find value and optional unit to the left of the range (longest match first)
            if idx >= 0:
                found_unit = False
                if idx >= 2:
                    combined3 = tokens[idx - 2] + " " + tokens[idx - 1] + " " + tokens[idx]
                    if _is_unit_token(combined3):
                        unit = combined3
                        idx -= 3
                        found_unit = True
                if not found_unit and idx >= 1:
                    combined = tokens[idx - 1] + " " + tokens[idx]
                    if _is_unit_token(combined):
                        unit = combined
                        idx -= 2
                        found_unit = True
                if not found_unit and _is_unit_token(tokens[idx]):
                    unit = tokens[idx]
                    idx -= 1
            if idx >= 0:
                v = _extract_numeric(tokens[idx])
                if v is not None:
                    value = v
                    if not unit and tokens[idx].rstrip(')').endswith('%'):
                        unit = '%'
                    idx -= 1
        else:
            value = _extract_numeric(tokens[idx])
            if not unit and tokens[idx].rstrip(')').endswith('%'):
                unit = '%'
            idx -= 1

# Look for unit before value (supports multi-word units, longest first)
            if idx >= 0:
                found_unit = False
                if idx >= 2:
                    combined3 = tokens[idx - 2] + " " + tokens[idx - 1] + " " + tokens[idx]
                    if _is_unit_token(combined3):
                        unit = combined3
                        idx -= 3
                        found_unit = True
                if not found_unit and idx >= 1:
                    combined = tokens[idx - 1] + " " + tokens[idx]
                    if _is_unit_token(combined):
                        unit = combined
                        idx -= 2
                        found_unit = True
                if not found_unit and _is_unit_token(tokens[idx]):
                    unit = tokens[idx]
                    idx -= 1

# Look for ref range before unit
            if idx >= 0:
                ref_result = _extract_ref_range_backward(tokens, idx)
                if ref_result:
                    ref_range, idx = ref_result

# Phase 3d: Neither — try multi-word unit at end
    else:
        found_unit = False
        if idx >= 2:
            combined3 = tokens[idx - 2] + " " + tokens[idx - 1] + " " + tokens[idx]
            if _is_unit_token(combined3):
                unit = combined3
                idx -= 3
                found_unit = True
        if not found_unit and idx >= 1:
            combined = tokens[idx - 1] + " " + tokens[idx]
            if _is_unit_token(combined):
                unit = combined
                idx -= 2
                found_unit = True
        if not found_unit and _is_unit_token(tokens[idx]):
            unit = tokens[idx]
            idx -= 1
# Extract ref range and value regardless of whether a unit was found
        if idx >= 0 and _is_ref_range_token(cleaned[idx]):
            ref_range = tokens[idx]
            idx -= 1
        if idx >= 0:
            v = _extract_numeric(tokens[idx])
            if v is not None:
                value = v
                if not unit and tokens[idx].rstrip(')').endswith('%'):
                    unit = '%'
                idx -= 1

    if value is None and not qual_value:
        return None

# Phase 4: Remaining tokens = test name
    if idx < 0:
        return None

    name_tokens = tokens[:idx + 1]
    name = " ".join(name_tokens).strip()
    name = re.sub(r"[^A-Za-z0-9\s/\-\.%#]", " ", name).strip()
    name = re.sub(r"\s+", " ", name).strip()
    if not name or len(name) < 2:
        return None

# Remove known flag abbreviations from the END of the name
    name = re.sub(r"\s+(H|L|N|HIGH|LOW|NORMAL)\s*$", "", name, flags=re.I).strip()
# Remove trailing colon/dash noise from name
    name = name.rstrip(":=-").strip()
    if not name or len(name) < 2:
        return None

    if ref_range:
        ref_range = _normalize_ref_range(ref_range)

    test_key = _lookup_test(name)

    return {
        "test_name": name,
        "value": value,
        "qualitative_value": qual_value,
        "unit": unit,
        "reference_range": ref_range,
        "test_key": test_key,
    }


def _parse_multicolumn(tokens: list[str]) -> dict | None:
    """
    Parse multi-column format (2+ space split).
    Expected columns: [test_name, value, (unit|ref), (ref|unit)]
    """
    if len(tokens) < 3:
        return None

    name = tokens[0]
    if len(name) < 2 or not re.search(r"[A-Za-z]", name):
        return None

    value = _extract_numeric(tokens[1])
    if value is None:
        return None

    unit = ""
    ref_range = ""
    rest = tokens[2:]

    if len(rest) == 1:
        tok = rest[0]
        if _is_ref_range_token(tok):
            ref_range = tok
        elif _is_unit_token(tok):
            unit = tok
        else:
            return None
    elif len(rest) >= 2:
        c1, c2 = rest[0], rest[1]
# Try (unit, ref) order
        if _is_unit_token(c1) and _is_ref_range_token(c2):
            unit = c1
            ref_range = c2
# Try (ref, unit) order
        elif _is_ref_range_token(c1) and _is_unit_token(c2):
            ref_range = c1
            unit = c2
# Try (unit, unknown) — ref might span multiple tokens
        elif _is_unit_token(c1):
            unit = c1
            ref_rest = rest[1:]
            ref_tokens = [t for t in ref_rest if _is_ref_range_token(t) or _extract_numeric(t) is not None]
            if ref_tokens:
                ref_range = _normalize_ref_range(" ".join(ref_tokens))
# Try (ref, unknown) — unit might be further right
        elif _is_ref_range_token(c1):
            ref_range = c1
            unit_rest = rest[1:]
            for t in unit_rest:
                if _is_unit_token(t):
                    unit = t
                    break
        else:
            return None

    if ref_range:
        ref_range = _normalize_ref_range(ref_range)

    test_key = _lookup_test(name)

    return {
        "test_name": name,
        "value": value,
        "qualitative_value": "",
        "unit": unit,
        "reference_range": ref_range,
        "test_key": test_key,
    }


# 8.  Entry Point

def parse_lab_report(text: str) -> list[dict]:
    """Extract lab results from OCR text."""
    raw = (text or "").strip()
    if not raw:
        return []

    logger.info("[parser] starting extraction on %d chars", len(raw))
    logger.debug("[parser] raw OCR input:\n%s", raw)

    cleaned_text = repair_ocr_text(raw)
    logger.debug("[parser] cleaned text:\n%s", cleaned_text)

    results: list[dict] = []

    for raw_line in cleaned_text.splitlines():
        line = _clean_line(raw_line)
        if not line or len(line) < 3:
            logger.debug("[parser] REJECT too short: %r", raw_line)
            continue

# Stage 1: Reject Metadata / Headers
# URL / email / phone
        if _URL_RE.search(line):
            logger.debug("[parser] REJECT contains URL: %r", line)
            continue
        if _EMAIL_RE.search(line):
            logger.debug("[parser] REJECT contains email: %r", line)
            continue
# Phone detection — use strict pattern to avoid matching lab values
        if _PHONE_RE.search(line):
            logger.debug("[parser] REJECT contains phone: %r", line)
            continue

# Section / column headers
        if _HEADER_RE.match(line):
            logger.debug("[parser] REJECT section header: %r", line)
            continue

# Metadata keywords
        if _META_RE.search(line):
            logger.debug("[parser] REJECT metadata keyword: %r", line)
            continue

# Date-only lines
        if _DATE_LINE_RE.match(line) or _DATE_MONTH_RE.match(line) or _DATE_MONTH2_RE.match(line):
            logger.debug("[parser] REJECT date only: %r", line)
            continue

# Lines without any alphabetic character
        if not re.search(r"[A-Za-z]", line):
            logger.debug("[parser] REJECT no alphabetic chars: %r", line)
            continue

# Lines without any numeric or qualitative value potential
        if not re.search(r"\d", line) and not re.search(
            r"(negative|positive|normal|abnormal|reactive|nil|trace|detected|present|absent)",
            line, re.I,
        ):
            logger.debug("[parser] REJECT no value possible: %r", line)
            continue

        logger.debug("[parser] ACCEPT line: %r", line)

# Stage 2: Multi-column parsing
        if "  " in line:
            mc_tokens = [t.strip() for t in re.split(r"\s{2,}", line) if t.strip()]
            if len(mc_tokens) >= 3:
                parsed = _parse_multicolumn(mc_tokens)
                if parsed and parsed["test_name"] and (parsed["value"] is not None or parsed["qualitative_value"]):
                    logger.info(
                        "[parser] multicolumn match: %r -> name=%r value=%s unit=%r ref=%r",
                        line, parsed["test_name"], parsed["value"],
                        parsed["unit"], parsed["reference_range"],
                    )
                    results.append({
                        "test_name": parsed["test_name"],
                        "value": parsed["value"] if parsed["value"] is not None else 0.0,
                        "unit": parsed["unit"] or "",
                        "raw_unit": parsed["unit"],
                        "reference_range": parsed["reference_range"],
                    })
                    continue

# Stage 3: Single-space token parsing
        tokens = line.split()
# Allow 2-token lines (e.g. "TSH 2.5" or "HB 13") — value-only results
        if len(tokens) < 2:
            logger.debug("[parser] REJECT too few tokens: %r", line)
            continue

        parsed = _backward_token_parse(tokens)
        if parsed is None:
            logger.debug("[parser] REJECT backward parse failed: %r", line)
            continue

        name = parsed["test_name"]
        value = parsed["value"]
        qual = parsed["qualitative_value"]
        unit = parsed["unit"]
        ref = parsed["reference_range"]
        test_key = parsed["test_key"]

# Stage 4: Validate
        if not name or len(name) < 2:
            logger.debug("[parser] REJECT invalid name: %r (line=%r)", name, line)
            continue

        if value is None and not qual:
            logger.debug("[parser] REJECT no value: name=%r line=%r", name, line)
            continue

# Reject suspicious test names (metadata that slipped through)
        alpha_count = sum(1 for c in name if c.isalpha())
        if alpha_count < 3:
            logger.debug("[parser] REJECT name insufficient alpha: %r (line=%r)", name, line)
            continue

# Use only clearly non-medical terms that would never appear as a test name
        suspicious = [
            r"\bphone\b", r"\bmobile\b", r"\bcontact\b", r"\bemail\b",
            r"\bwebsite\b", r"\bfax\b", r"\baddress\b",
            r"\bbarcode\b", r"\bdoctor\b", r"\bconsultant\b",
            r"\bremarks\b", r"\bsignature\b",
            r"\+91",
        ]
        if any(re.search(p, name, re.I) for p in suspicious):
            logger.debug("[parser] REJECT suspicious name: %r (line=%r)", name, line)
            continue

# Discard unresolvable names (not in dictionary) unless they look plausible
        if not test_key:
# Name must be at least 4 alpha chars and not look like noise
            if name.isupper() and len(set(name)) <= 3:
                logger.debug("[parser] REJECT likely abbreviation/header: %r (line=%r)", name, line)
                continue
# Check for non-medical-looking names
            if not re.search(r"[A-Za-z]{3,}", name):
                logger.debug("[parser] REJECT name too short alpha: %r (line=%r)", name, line)
                continue

        logger.info(
            "[parser] match: %r -> name=%r value=%s unit=%r ref=%r",
            line, name, value, unit, ref,
        )

        results.append({
            "test_name": name,
            "value": value if value is not None else 0.0,
            "unit": unit or "",
            "raw_unit": unit,
            "reference_range": ref,
        })

    logger.info("[parser] extraction complete: %d results found", len(results))
    return results
