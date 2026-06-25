"""
Benchmark Dataset Generator for Medical Blood Test Analysis System.
Generates 600+ realistic reports with ground truth across 7 report types,
including clean text, OCR-corrupted text, and 6 quality degradation levels.
"""
from __future__ import annotations

import json
import logging
import math
import os
import random
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

random.seed(42)

# 1.  REPORT TYPE DEFINITIONS (test panels + value generators)

# Each panel entry: (test_key, canonical_unit, generate_value_fn)
# generate_value_fn(ref_low, ref_high) -> float

def _normal_range(ref_low, ref_high):
    """Generate a value solidly within the reference range."""
    if ref_low is None and ref_high is None:
        return round(random.uniform(10, 100), 1)
    if ref_low is None:
        return round(random.uniform(0, ref_high * 0.8), 1)
    if ref_high is None:
        return round(random.uniform(ref_low, ref_low * 2), 1)
    mid = (ref_low + ref_high) / 2
    spread = (ref_high - ref_low) * 0.4
    return round(random.uniform(mid - spread, mid + spread), 1)

def _high_range(ref_low, ref_high):
    """Generate a value above the reference range."""
    if ref_high is None:
        return round(random.uniform(ref_low * 1.5, ref_low * 3), 1)
    return round(random.uniform(ref_high * 1.05, ref_high * 1.5), 1)

def _low_range(ref_low, ref_high):
    """Generate a value below the reference range."""
    if ref_low is None or ref_low <= 0:
        return round(random.uniform(0.1, 0.5), 1)
    return round(random.uniform(ref_low * 0.3, ref_low * 0.95), 1)

def _any_value(ref_low, ref_high):
    """Generate any plausible value across all categories."""
    r = random.random()
    if r < 0.6:
        return _normal_range(ref_low, ref_high)
    elif r < 0.8:
        return _high_range(ref_low, ref_high)
    else:
        return _low_range(ref_low, ref_high)

CBC_PANEL = [
    ("wbc", "x10^3/µL"),
    ("rbc", "x10^6/µL"),
    ("hemoglobin", "g/dL"),
    ("hematocrit", "%"),
    ("mcv", "fL"),
    ("mch", "pg"),
    ("mchc", "g/dL"),
    ("rdw", "%"),
    ("platelets", "x10^3/µL"),
    ("mpv", "fL"),
    ("neutrophils_pct", "%"),
    ("lymphocytes_pct", "%"),
    ("monocytes_pct", "%"),
    ("eosinophils_pct", "%"),
    ("basophils_pct", "%"),
]

LIPID_PANEL = [
    ("total_cholesterol", "mg/dL"),
    ("ldl", "mg/dL"),
    ("hdl", "mg/dL"),
    ("triglycerides", "mg/dL"),
    ("vldl", "mg/dL"),
    ("non_hdl_cholesterol", "mg/dL"),
]

LIVER_PANEL = [
    ("alt", "U/L"),
    ("ast", "U/L"),
    ("alp", "U/L"),
    ("ggt", "U/L"),
    ("total_bilirubin", "mg/dL"),
    ("direct_bilirubin", "mg/dL"),
    ("indirect_bilirubin", "mg/dL"),
    ("albumin", "g/dL"),
    ("total_protein", "g/dL"),
    ("ag_ratio", "ratio"),
]

KIDNEY_PANEL = [
    ("creatinine", "mg/dL"),
    ("bun", "mg/dL"),
    ("urea", "mg/dL"),
    ("uric_acid", "mg/dL"),
    ("egfr", "mL/min/1.73m²"),
    ("sodium", "mEq/L"),
    ("potassium", "mEq/L"),
    ("chloride", "mEq/L"),
    ("calcium", "mg/dL"),
    ("phosphorus", "mg/dL"),
]

DIABETES_PANEL = [
    ("glucose_fasting", "mg/dL"),
    ("hba1c", "%"),
    ("insulin_fasting", "µIU/mL"),
]

THYROID_PANEL = [
    ("tsh", "µIU/mL"),
    ("free_t4", "ng/dL"),
    ("free_t3", "pg/mL"),
]

PANELS = {
    "CBC": CBC_PANEL,
    "Lipid Profile": LIPID_PANEL,
    "Liver Function": LIVER_PANEL,
    "Kidney Function": KIDNEY_PANEL,
    "Diabetes": DIABETES_PANEL,
    "Thyroid": THYROID_PANEL,
}


# 2.  REFERENCE RANGE LOADER

def _load_reference_ranges():
    """Load reference ranges from the project's lab_reference_dataset.json."""
    path = os.path.join(os.path.dirname(__file__), "..", "medical", "lab_reference_dataset.json")
    with open(path) as f:
        db = json.load(f)

    ranges: dict[str, list] = {}
    for entry in db:
        key = entry.get("key", "")
        canonical_unit = entry.get("canonical_unit", "")
        gender_ranges = entry.get("ranges", {})
        adult_male = (gender_ranges.get("male") or {}).get("adult", {})
        adult_female = (gender_ranges.get("female") or {}).get("adult", {})
        combined = adult_male or adult_female or {}
        lo = combined.get("low")
        hi = combined.get("high")
        ranges[key] = (lo, hi, canonical_unit)
    return ranges


_REF_RANGES = _load_reference_ranges()


def get_ref_range(test_key: str):
    """Get (low, high, unit) for a test key. Returns (None, None, '') if not found."""
    return _REF_RANGES.get(test_key, (None, None, ""))


# 3.  VALUE GENERATION STRATEGIES

def pick_status():
    """Randomly pick a classification status with weighted distribution."""
    r = random.random()
    if r < 0.60:
        return "normal"
    elif r < 0.80:
        return "high"
    else:
        return "low"


def generate_value(test_key: str, status: str):
    """Generate a plausible value for a test given the desired status."""
    lo, hi, unit = get_ref_range(test_key)
    if status == "normal":
        return _normal_range(lo, hi)
    elif status == "high":
        return _high_range(lo, hi)
    else:
        return _low_range(lo, hi)


# 4.  TEXT FORMATTING (lab report print formats)

DISPLAY_NAMES = {
    "wbc": "WBC",
    "rbc": "RBC",
    "hemoglobin": "Hemoglobin",
    "hematocrit": "Hematocrit",
    "mcv": "MCV",
    "mch": "MCH",
    "mchc": "MCHC",
    "rdw": "RDW-CV",
    "platelets": "Platelet Count",
    "mpv": "MPV",
    "neutrophils_pct": "Neutrophils",
    "lymphocytes_pct": "Lymphocytes",
    "monocytes_pct": "Monocytes",
    "eosinophils_pct": "Eosinophils",
    "basophils_pct": "Basophils",
    "total_cholesterol": "Total Cholesterol",
    "ldl": "LDL",
    "hdl": "HDL",
    "triglycerides": "Triglycerides",
    "vldl": "VLDL",
    "non_hdl_cholesterol": "Non-HDL Cholesterol",
    "alt": "ALT",
    "ast": "AST",
    "alp": "ALP",
    "ggt": "GGT",
    "total_bilirubin": "Total Bilirubin",
    "direct_bilirubin": "Direct Bilirubin",
    "indirect_bilirubin": "Indirect Bilirubin",
    "albumin": "Albumin",
    "total_protein": "Total Protein",
    "ag_ratio": "A/G Ratio",
    "creatinine": "Creatinine",
    "bun": "BUN",
    "urea": "Urea",
    "uric_acid": "Uric Acid",
    "egfr": "eGFR",
    "sodium": "Sodium",
    "potassium": "Potassium",
    "chloride": "Chloride",
    "calcium": "Calcium",
    "phosphorus": "Phosphorus",
    "glucose_fasting": "Fasting Glucose",
    "hba1c": "HbA1c",
    "insulin_fasting": "Fasting Insulin",
    "tsh": "TSH",
    "free_t4": "Free T4",
    "free_t3": "Free T3",
}

COLUMN_HEADERS = "Test Name                     Value       Unit         Ref Range"


def _format_ref_str(test_key: str) -> str:
    lo, hi, unit = get_ref_range(test_key)
    if lo is not None and hi is not None:
        return f"{lo}-{hi}"
    elif lo is not None:
        return f">{lo}"
    elif hi is not None:
        return f"<{hi}"
    return ""


def _format_clean_line(test_key: str, value: float, unit: str) -> str:
    display = DISPLAY_NAMES.get(test_key, test_key.replace("_", " ").title())
    ref = _format_ref_str(test_key)
# Fixed-width columns: left-align test name, right-align value/unit/ref
    return f"{display:<30s} {str(value):>8s}  {unit:<12s} {ref}"


def generate_clean_report(report_type: str, test_values: dict[str, dict], panel: list = None) -> str:
    """Generate a clean multi-column lab report."""
    if panel is None:
        panel = PANELS.get(report_type, [])
    lines = [f"=== {report_type.upper()} ===", "", COLUMN_HEADERS, "-" * 70]
    for test_key, _ in panel:
        if test_key in test_values:
            info = test_values[test_key]
            lines.append(_format_clean_line(test_key, info["value"], info["unit"]))
    lines.append("-" * 70)
    return "\n".join(lines)


# 5.  OCR CORRUPTION ENGINE

# Character substitution maps for simulating OCR errors
_CHAR_SUBS = {
    "0": "O", "O": "0",
    "1": "I", "I": "1", "l": "1",
    "5": "S", "S": "5",
    "8": "B", "B": "8",
    "6": "G", "G": "6",
    ".": ",", ",": ".",
    "g": "9",
    "r": "n",
    "n": "r",
    "u": "n",
    "/": "1",
}


def _make_ocr_params(quality: str) -> dict:
    """Return OCR corruption parameters for a given quality level."""
    params = {
        "sub_prob": 0.03, "del_prob": 0.02, "ins_prob": 0.01,
        "sp_del_prob": 0.02, "sp_ins_prob": 0.02,
    }
    if quality == "clean":
        params.update({k: 0.0 for k in params})
    elif quality == "standard":
        params.update({"sub_prob": 0.03, "del_prob": 0.01, "ins_prob": 0.005,
                       "sp_del_prob": 0.01, "sp_ins_prob": 0.01})
    elif quality == "low":
        params.update({"sub_prob": 0.08, "del_prob": 0.04, "ins_prob": 0.02,
                       "sp_del_prob": 0.05, "sp_ins_prob": 0.03})
    elif quality == "mobile":
        params.update({"sub_prob": 0.06, "del_prob": 0.03, "ins_prob": 0.015,
                       "sp_del_prob": 0.08, "sp_ins_prob": 0.04})
    elif quality == "rotated":
        params.update({"sub_prob": 0.07, "del_prob": 0.05, "ins_prob": 0.02,
                       "sp_del_prob": 0.06, "sp_ins_prob": 0.04})
    elif quality == "pdf":
        params.update({"sub_prob": 0.02, "del_prob": 0.01, "ins_prob": 0.005,
                       "sp_del_prob": 0.005, "sp_ins_prob": 0.005})
    return params


def corrupt_text(text: str, quality: str = "standard") -> str:
    """Apply simulated OCR corruption at varying quality levels."""
    p = _make_ocr_params(quality)
    if p["sub_prob"] == 0.0 and p["del_prob"] == 0.0:
        return text

    _SUBS_KEYS = set(_CHAR_SUBS.keys())

    def _corrupt_char(c: str, p: dict) -> str:
        r = random.random()
        if r < p["del_prob"]:
            return ""
        if r < p["del_prob"] + p["ins_prob"]:
            return c + random.choice("abcdefghijklmnopqrstuvwxyz")
        if c in _SUBS_KEYS and random.random() < p["sub_prob"]:
            return _CHAR_SUBS[c]
        return c

    result = []
    for line in text.split("\n"):
        corrupted_line = "".join(_corrupt_char(c, p) for c in line)
        if p["sp_del_prob"] > 0 and random.random() < p["sp_del_prob"]:
            corrupted_line = corrupted_line.replace("  ", " ", 1)
        if p["sp_ins_prob"] > 0 and random.random() < p["sp_ins_prob"]:
            idx = random.randint(0, max(1, len(corrupted_line)))
            corrupted_line = corrupted_line[:idx] + " " + corrupted_line[idx:]
        result.append(corrupted_line)

    return "\n".join(result)


# 6.  MIXED REPORT GENERATOR

_MIXED_FLAT = (
    CBC_PANEL[:5] + LIPID_PANEL[:3] + LIVER_PANEL[:4] +
    KIDNEY_PANEL[:4] +
    [("glucose_fasting", "mg/dL"), ("hba1c", "%")] +
    [("tsh", "µIU/mL"), ("free_t4", "ng/dL"),
     ("ferritin", "ng/mL"), ("crp", "mg/L"), ("esr", "mm/hr")]
)
MIXED_PANEL = list(dict.fromkeys(_MIXED_FLAT))


# 7.  BENCHMARK DATASET GENERATOR

@dataclass
class GroundTruthReport:
    report_id: str
    report_type: str
    quality: str
    clean_text: str
    corrupted_text: str
    ground_truth_values: dict[str, float]
    ground_truth_units: dict[str, str]
    ground_truth_ranges: dict[str, tuple]
    ground_truth_statuses: dict[str, str]
    metadata: dict


QUALITIES = ["clean", "standard", "low", "mobile", "rotated", "pdf"]


def generate_report(report_type: str, report_id: str, quality: str = "standard") -> GroundTruthReport:
    """Generate a single benchmark report with full ground truth."""
    panel = PANELS.get(report_type, [])
    if report_type == "Mixed":
        panel = MIXED_PANEL

    test_values = {}
    gt_values = {}
    gt_units = {}
    gt_ranges = {}
    gt_statuses = {}

    for test_key, canonical_unit in panel:
        status = pick_status()
        value = generate_value(test_key, status)
        lo, hi, unit = get_ref_range(test_key)
        display_unit = canonical_unit or unit or ""

        test_values[test_key] = {
            "value": value,
            "unit": display_unit,
            "status": status,
        }
        gt_values[test_key] = value
        gt_units[test_key] = display_unit
        gt_ranges[test_key] = (lo, hi)
        gt_statuses[test_key] = status

    clean_text = generate_clean_report(report_type, test_values, panel)
    corrupted_text = corrupt_text(clean_text, quality)

    return GroundTruthReport(
        report_id=report_id,
        report_type=report_type,
        quality=quality,
        clean_text=clean_text,
        corrupted_text=corrupted_text,
        ground_truth_values=gt_values,
        ground_truth_units=gt_units,
        ground_truth_ranges=gt_ranges,
        ground_truth_statuses=gt_statuses,
        metadata={"gender": random.choice(["male", "female"]),
                  "age": random.randint(20, 80)},
    )


def generate_dataset(output_dir: str = None) -> list[GroundTruthReport]:
    """Generate the complete benchmark dataset"""
    reports = []
    report_id = 0

    for report_type in list(PANELS.keys()) + ["Mixed"]:
        for quality in QUALITIES:
            if quality == "clean":
                count = 10  # 10 clean per type = 70
            elif quality == "standard":
                count = 10  # 10 standard per type = 70
            else:
                count = 5   # 5 of each degradation per type = 25x5 = 125 per type

            for _ in range(count):
                report_id += 1
                rid = f"RPT-{report_type[:3].upper()}-{quality.upper()}-{report_id:04d}"
                try:
                    report = generate_report(report_type, rid, quality)
                    reports.append(report)
                except Exception as e:
                    logger.warning("Failed to generate %s: %s", rid, e)

    logger.info("Generated %d benchmark reports", len(reports))

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        for r in reports:
            entry = {
                "report_id": r.report_id,
                "report_type": r.report_type,
                "quality": r.quality,
                "ground_truth_values": r.ground_truth_values,
                "ground_truth_units": r.ground_truth_units,
                "ground_truth_ranges": {k: list(v) for k, v in r.ground_truth_ranges.items()},
                "ground_truth_statuses": r.ground_truth_statuses,
                "metadata": r.metadata,
            }
            path = os.path.join(output_dir, f"{r.report_id}.json")
            with open(path, "w") as f:
                json.dump(entry, f, indent=2)

# Also save the text corpora
        clean_dir = os.path.join(output_dir, "text_clean")
        corrupt_dir = os.path.join(output_dir, "text_corrupted")
        os.makedirs(clean_dir, exist_ok=True)
        os.makedirs(corrupt_dir, exist_ok=True)
        for r in reports:
            with open(os.path.join(clean_dir, f"{r.report_id}.txt"), "w") as f:
                f.write(r.clean_text)
            with open(os.path.join(corrupt_dir, f"{r.report_id}.txt"), "w") as f:
                f.write(r.corrupted_text)

# Save a master index
        index = []
        for r in reports:
            index.append({
                "report_id": r.report_id,
                "report_type": r.report_type,
                "quality": r.quality,
                "tests": len(r.ground_truth_values),
                "clean_file": f"text_clean/{r.report_id}.txt",
                "corrupted_file": f"text_corrupted/{r.report_id}.txt",
                "ground_truth_file": f"{r.report_id}.json",
            })
        with open(os.path.join(output_dir, "index.json"), "w") as f:
            json.dump(index, f, indent=2)

        logger.info("Dataset saved to %s", output_dir)

    return reports


if __name__ == "__main__":
    generate_dataset("/tmp/benchmark_dataset")
