"""
OCR-tolerant lab report parser.

Pipeline per line:
  clean_ocr_text() → pattern matching → normalize_unit()

Handles:
  - "WBC Count: 7.5 x10^3/uL (4.0-11.0)"
  - "Hemoglobin 9.5 g/dL"
  - "Absolute Neutrophil Count 341 1043/pL"   ← OCR-mangled
  - "RBC 4.2 million/uL"
  - "Platelets 150k"
  - "WBc 13000 /uL"
"""
from __future__ import annotations

import logging
import re

from core.normalization import repair_ocr_text, normalize_unit

logger = logging.getLogger(__name__)

# Numeric: allow spaces or common OCR noise in numbers (cleaned later)
_NUM = r"(?:(?:\d{1,3}(?:[ ,]\d{3})+)|\d+)(?:[\.,]\d+)?(?:[eE][+\-]?\d+)?"

# Unit-like token: allow almost anything that looks like a unit, including OCR noise
_UNIT_TOK = r"[A-Za-zµ%/\^x\.\d\u00B2\u00B3\u2070-\u2079\*\+\-]+"

# Reference range: more flexible pattern
_REF = r"\(?\s*(?:[\d,]+\.?\d*)\s*(?:-|–|to)\s*(?:[\d,]+\.?\d*)\s*\)?"

def _clean_line(line: str) -> str:
    s = (line or "").strip()
    if not s:
        return ""
    # Strip leading OCR noise: bullets, dashes, digits+dot, and stray quotes/apostrophes
    s = re.sub(r"^(?:[\*\-\•'\"\`]+|\d+\.)\s*", "", s)
    # Strip leading non-alphanumeric symbols (e.g. ® € © that prefix lab names)
    s = re.sub(r"^[^A-Za-z0-9]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _clean_multicolumn_line(line: str) -> str:
    s = (line or "").strip()
    if not s:
        return ""
    s = re.sub(r"^(?:[\*\-\•'\"\`]+|\d+\.)\s*", "", s)
    s = re.sub(r"^[^A-Za-z0-9]+", "", s)
    s = s.replace("\t", "  ")
    s = re.sub(r"[ \t\f\v]{2,}", "  ", s)
    return s


def _parse_value(num: str) -> float:
    # Remove spaces, commas, and handle common OCR decimal errors
    s = num.replace(" ", "").replace(",", "")
    # If multiple dots appear (OCR error), take the first one or last one? 
    # Usually the last one if it looks like a decimal. 
    if s.count(".") > 1:
        parts = s.split(".")
        s = "".join(parts[:-1]) + "." + parts[-1]
    return float(s)


# Bare numeric reference range (without parentheses): e.g. 83-101 or 13.0 - 17.0
_REF_BARE = rf"{_NUM}\s*[-\u2013]\s*{_NUM}"

# Ordered list of regex patterns — most specific first.
_PATTERNS = [
    # P1: "Name: value unit (ref)" or "Name = value unit" — colon/equals separator
    re.compile(
        rf"^(?P<name>[A-Za-z0-9][A-Za-z0-9 \(\)/\.\-%]+?)\s*[:=]\s*"
        rf"(?P<value>{_NUM})\s*"
        rf"(?P<unit>{_UNIT_TOK})?\s*"
        rf"(?:\((?P<ref>[^)]+)\))?\s*$",
        re.I
    ),
    # P2: "Name value unit (ref)" — space separator, parens ref (generic fallback)
    # Name should be LETTERS ONLY (no digits), to avoid consuming numbers
    re.compile(
        rf"^(?P<name>[A-Za-z][A-Za-z \(\)/\.\-%]*?)\s+"
        rf"(?P<value>{_NUM})\s*"
        rf"(?P<unit>{_UNIT_TOK})?\s*"
        rf"(?:\((?P<ref>[^)]+)\))?\s*$",
        re.I
    ),
    # P3: "Name - value unit [bare-ref]" — dash separator (e.g. "MCV - 87.7 fL 83-101")
    # Name should be LETTERS ONLY (no digits), to prevent matching numbers as part of name
    re.compile(
        rf"^(?P<name>[A-Za-z][A-Za-z ]*?)\s+[-\u2013]\s+"
        rf"(?P<value>{_NUM})\s*"
        rf"(?P<unit>{_UNIT_TOK})?\s*"
        rf"(?P<ref>{_REF_BARE})?\s*$",
        re.I
    ),
    # P4: "Name value unit lo-hi" — space separator WITH required bare ref range
    # Alpha-only name + required unit + required bare ref (for high-confidence matches)
    re.compile(
        rf"^(?P<name>[A-Za-z][A-Za-z ]+?)\s+"
        rf"(?P<value>{_NUM})\s+"
        rf"(?P<unit>{_UNIT_TOK})\s+"
        rf"(?P<ref>{_REF_BARE})\s*$",
        re.I
    ),
]

# Lines that are pure column-header rows — skip only when there is NO numeric value on the line.
# Deliberately narrow: avoid matching real test lines that start with words like "Lab", "Health",
# "Medical", etc. which legitimately appear as part of test names.
_SKIP_RE = re.compile(
    r"^(?!.*\d)\s*(test\s*name|result|reference\s*range?|normal\s*range|unit|hemoglobin\s*low)\s*$",
    re.I,
)

# Separate pattern for hard metadata lines that never contain test values
_META_RE = re.compile(
    r"^\s*(patient\s*id|uhid|ref(?:erred)?\s*by|registration|report\s*id|"
    r"collection\s*date|received|printed\s*by|authorized\s*by|specimen\s*type|"
    r"tel:|phone:|mobile:|dr\.\s+[A-Za-z]|mrs?\.\s+[A-Za-z]|miss\.\s+[A-Za-z]|"
    r"age\s*[:/]?\s*\d+|gender\s*[:/]?\s*[MF]|sex\s*[:/]?\s*[MF]|"
    r"date\s*[:/]?\s*\d+|total\s*tests?|abnormal\s*tests?|page\s*\d+|"
    # Lab-report header lines commonly seen in OCR output
    r"automated\s+\d|age\s*/\s*gender|pathlabs?|pathlab|\(.*\).*pathlabs?)",
    re.I,
)

# Valid unit characters (expanded for robustness)
_VALID_UNIT_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789%/^.µx*+-"

def _is_valid_unit(unit_str: str) -> bool:
    """Check if unit string contains reasonable characters and is not pure noise."""
    if not unit_str:
        return True
    u = unit_str.lower()

    # Medical units often have specific chars
    medical_markers = ["/", "µ", "%", "^", "10"]
    if any(m in u for m in medical_markers):
        return True

    # Check for at least one reasonable unit character
    valid_count = sum(1 for c in u if c in _VALID_UNIT_CHARS)
    if valid_count < 1:
        logger.debug("[parser] rejecting invalid unit (no valid chars): %r", unit_str)
        return False

    # Reject pure noise tokens
    noise_patterns = [r"\borsl\b", r"\brors\b", r"\bfe\b", r"\bpo\b", r"\ba\b", r"\bmeeacop\b"]
    for pattern in noise_patterns:
        if re.search(pattern, u, re.I):
            logger.debug("[parser] rejecting unit with noise token: %r", unit_str)
            return False

    # Reject long strings that are likely just text
    if len(u.split()) > 4:
        logger.debug("[parser] rejecting long textual unit: %r", unit_str)
        return False

    return True


def _is_garbage_line(line: str) -> bool:
    """
    Reject lines that are mostly garbage OCR noise.
    A line is garbage if it has lots of non-dictionary words with no structure.
    Test lines have: [word] [number] [unit/word] [number-number] ...
    Garbage lines have: gibberish [space] gibberish gibberish...
    """
    words = line.lower().split()
    if len(words) < 2:
        return False
    
    # Common English/medical words that are always valid
    valid_words = {
        'and', 'or', 'the', 'a', 'an', 'by', 'from', 'to', 'of', 'in', 'for',
        'test', 'name', 'result', 'unit', 'range', 'reference', 'normal',
        'low', 'high', 'value', 'patient', 'age', 'date', 'report', 'lab',
        # Medical-specific
        'count', 'level', 'hemoglobin', 'glucose', 'cell', 'blood', 'ratio',
        'absolute', 'lymphocyte', 'neutrophil', 'monocyte', 'eosinophil',
    }
    
    real_word_count = 0
    num_count = 0
    alpha_word_count = 0
    alpha_tokens: list[str] = []
    
    for word in words:
        # Numbers and numeric patterns are legitimate in test lines
        # Updated to handle percentages (40%), ranges (37-47%), and parenthesized ranges ((37-47%))
        if re.match(r'^[\d\.e\-\+%\(\)]+$', word):
            num_count += 1
            continue
        # Dashes alone are not words
        if word in ['-', '–', '—', 'to']:
            continue
        # Track tokens containing alphabetic chars for test-name detection
        if re.search(r'[A-Za-z]', word):
            alpha_word_count += 1
            alpha_tokens.append(word)
        # Check if it's a known word or valid text token
        if word in valid_words or (len(word) >= 3 and re.search(r'[A-Za-z]', word)):
            real_word_count += 1
    
    # Reject single short alphabetic test names that are not approved medical abbreviations.
    if num_count >= 1 and len(alpha_tokens) == 1:
        token = alpha_tokens[0]
        if re.fullmatch(r'[A-Za-z]{1,3}', token):
            approved_short_terms = {
                'RBC', 'WBC', 'MCH', 'MCV', 'TSH', 'HDL',
                'LDL', 'ALT', 'AST', 'ESR', 'CRP', 'PSA', 'HIV', 'RDW', 'POW'
            }
            if token.upper() not in approved_short_terms:
                return True

    # If line has both numeric results and alphabetic tokens, it's likely a valid test line.
    if num_count >= 1 and alpha_word_count >= 1:
        return False

    # If we have mostly real words (>= 40% real), it's a test line
    total_tokens = real_word_count + num_count
    if total_tokens >= 2:
        ratio = real_word_count / total_tokens
        if ratio >= 0.4:
            return False
    
    # Everything else is garbage
    logger.debug("[parser] rejecting garbage line: %r (real_words=%d, alpha_words=%d, nums=%d)", line, real_word_count, alpha_word_count, num_count)
    return True


def _extract_first_value(line: str) -> tuple[str, float, str] | None:
    """
    Extract (name, value, rest_of_line) from a line.
    Returns: (name_part, first_number_value, remaining_text_after_number)
    """
    # Find first standalone number in line, not digits embedded in a word like T4 or B12.
    num_match = re.search(rf"(?<![A-Za-z0-9]){_NUM}", line)
    if not num_match:
        return None
    
    name_part = line[:num_match.start()].strip().rstrip(":=-").strip()
    if len(name_part) < 2:
        return None
    
    try:
        value = _parse_value(num_match.group(0))
    except:
        return None
    
    rest_of_line = line[num_match.end():].strip()
    return (name_part, value, rest_of_line)


def _looks_like_ref_range(text: str) -> bool:
    return bool(re.search(rf"{_REF_BARE}", text))


def _parse_multicolumn_line(line: str) -> dict | None:
    """
    Parse a line that appears to have multiple columns separated by large whitespace.
    Expected columns: name, value, unit, reference range.
    This avoids confusing the reference range as the value.
    """
    columns = [col.strip() for col in re.split(r"\s{2,}", line) if col.strip()]
    if len(columns) < 3:
        return None

    # Repair numeric fragments split across adjacent columns, e.g. "12 . 2" → "12.2".
    if len(columns) >= 4 and columns[2] in {'.', ','} and re.fullmatch(r"\d+(?:[\.,]\d*)?", columns[1]) and re.fullmatch(r"\d+", columns[3]):
        columns[1] = f"{columns[1].replace(',', '')}.{columns[3]}"
        del columns[2:4]

    name = columns[0]
    if len(name) < 2 or not re.search(r"[A-Za-z]", name):
        return None

    # Column 1 should be the numeric result
    value_part = columns[1]
    try:
        value = _parse_value(value_part)
    except Exception:
        return None

    raw_unit = columns[2]
    ref = ""
    if len(columns) >= 4:
        ref = " ".join(columns[3:]).strip()

    # If the third column itself looks like a reference range, then unit is missing
    if _looks_like_ref_range(raw_unit):
        ref = raw_unit if not ref else f"{raw_unit} {ref}".strip()
        raw_unit = ""

    # If the fourth+ columns are not ranges, attempt to parse again more conservatively
    if ref and not _looks_like_ref_range(ref):
        # Maybe the third column was actually the unit and fourth column is part of the unit
        if len(columns) == 3:
            # Nothing further to do
            pass
        else:
            # If a later column is rangeish, assign from there
            for idx, col in enumerate(columns[3:], start=3):
                if _looks_like_ref_range(col):
                    ref = col
                    raw_unit = columns[2]
                    break

    if raw_unit and not _is_valid_unit(raw_unit):
        logger.debug("[parser] multicolumn clearing invalid unit noise: %r", raw_unit)
        raw_unit = ""

    unit = normalize_unit(raw_unit) or raw_unit
    logger.info("[parser] multicolumn match: %r -> name=%r value=%s unit=%r ref=%r", line, name, value, unit, ref)

    return {
        "test_name": name,
        "value": value,
        "unit": unit,
        "raw_unit": raw_unit,
        "reference_range": ref,
    }


def _extract_unit_and_ref(rest_of_line: str) -> tuple[str, str]:
    """
    From the rest of the line after the value, extract unit and reference range.
    Returns: (unit_str, reference_range_str)
    """
    unit = ""
    ref = ""
    
    # Try to find unit at the start of rest_of_line
    unit_match = re.match(rf"^({_UNIT_TOK})\s*", rest_of_line)
    if unit_match:
        unit = unit_match.group(1)
        remaining = rest_of_line[unit_match.end():].strip()
    else:
        remaining = rest_of_line
    
    # Try to find reference range in what remains
    range_match = re.match(rf"^({_REF_BARE})\s*$", remaining)
    if range_match:
        ref = range_match.group(1)
    elif remaining and not remaining.startswith("("):
        # Unstructured remaining text - might be a range
        if re.search(rf"{_REF_BARE}", remaining):
            ref = remaining.strip()
    
    return (unit, ref)


def parse_lab_report(text: str) -> list[dict]:
    """
    Extract lab results from OCR/text.
    Uses two-stage parsing:
      1. Regex patterns (for well-structured formats)
      2. Fallback to first-number extraction (for multi-column/complex formats)
    
    Returns list of dicts: {test_name, value, unit, reference_range}
    """
    raw = (text or "").strip()
    if not raw:
        return []

    logger.info("[parser] starting extraction on %d chars", len(raw))
    logger.debug("[parser] raw OCR input:\n%s", raw)

    # Apply global OCR corrections first
    cleaned_text = repair_ocr_text(raw)
    logger.debug("[parser] cleaned text:\n%s", cleaned_text)

    results: list[dict] = []

    for raw_line in cleaned_text.splitlines():
        line = _clean_line(raw_line)
        multi_column_line = _clean_multicolumn_line(raw_line)
        if not line or len(line) < 3:
            continue
        
        # Skip pure column-header rows, but do not skip any line with numeric output.
        if _SKIP_RE.match(line):
            logger.debug("[parser] skip header line: %r", line)
            continue
        
        # Skip hard metadata lines that can never be test values
        if _META_RE.search(line):
            logger.debug("[parser] skip metadata line: %r", line)
            continue
        
        # Skip garbage lines (mostly OCR noise)
        if _is_garbage_line(line):
            logger.debug("[parser] skip garbage line: %r", line)
            continue

        matched = False
        
        # STAGE 1: Try structured regex patterns (colon/equals format)
        for pat in _PATTERNS:
            m = pat.match(line)
            if not m:
                continue

            name = (m.group("name") or "").strip().rstrip(":=-")
            name = re.sub(r"\s+", " ", name).strip()
            if len(name) < 2:
                continue

            try:
                value_str = m.group("value")
                value = _parse_value(value_str)
            except Exception as e:
                logger.debug("[parser] failed value parse for %r: %s", line, e)
                continue

            raw_unit = (m.group("unit") or "").strip()
            if raw_unit and not _is_valid_unit(raw_unit):
                logger.debug("[parser] clearing invalid unit noise: %r", raw_unit)
                raw_unit = ""

            unit = normalize_unit(raw_unit) or raw_unit
            ref = (m.group("ref") or "").strip()

            logger.info("[parser] pattern match: %r -> name=%r value=%s unit=%r ref=%r", line, name, value, unit, ref)

            results.append({
                "test_name": name,
                "value": value,
                "unit": unit,
                "raw_unit": raw_unit,
                "reference_range": ref,
            })
            matched = True
            break

        if matched:
            continue

        # STAGE 2: Try multi-column extraction for structured lines
        multicol = _parse_multicolumn_line(multi_column_line)
        if multicol is not None:
            results.append(multicol)
            continue

        # STAGE 3: Fallback to first-number extraction (for unstructured lines)
        extraction = _extract_first_value(line)
        if extraction:
            name, value, rest = extraction
            
            # Extract unit and reference range from what's left
            raw_unit, ref = _extract_unit_and_ref(rest)
            
            if raw_unit and not _is_valid_unit(raw_unit):
                logger.debug("[parser] clearing invalid unit noise: %r", raw_unit)
                raw_unit = ""
            
            unit = normalize_unit(raw_unit) or raw_unit
            
            logger.info("[parser] fallback match: %r -> name=%r value=%s unit=%r ref=%r", line, name, value, unit, ref)
            
            results.append({
                "test_name": name,
                "value": value,
                "unit": unit,
                "raw_unit": raw_unit,
                "reference_range": ref,
            })

    logger.info("[parser] extraction complete: %d results found", len(results))
    return results