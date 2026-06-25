"""Centralized Clinical Knowledge Base — structured for RAG retrieval"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# PATTERN DEFINITIONS — retrieval-friendly structure

@dataclass(frozen=True)
class ClinicalPattern:
    """Represents a detectable clinical condition pattern"""
    pattern_id: str                         # e.g. "anemia_iron_deficiency"
    condition_name: str                     # display name
    test_dependencies: list[str]            # required test_key matches
    keywords: list[str]                     # for semantic/keyword search
    description: str                        # clinical explanation
    severity_level: str                     # "mild" | "moderate" | "severe"
    possible_causes: list[str]
    suggested_next_steps: list[str]


# CLINICAL PATTERNS — CENTRALIZED (future retrieval source)

def _load_clinical_patterns_from_json() -> list[ClinicalPattern]:
    """Load clinical patterns from clinical_kb.json (empty list on failure)."""
    path = Path(__file__).parent / "clinical_kb.json"
    if not path.exists():
        logger.error(
            "clinical_kb.json not found at expected path: %s; falling back to hardcoded patterns",
            path,
        )
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        logger.warning(
            "[clinical_kb] failed to load clinical_kb.json: %s; falling back to hardcoded patterns",
            exc,
        )
        return []

    patterns: list[ClinicalPattern] = []
    for entry in data:
# support common alternative key names
        test_deps = entry.get("test_dependencies") or entry.get("test_keys") or entry.get("tests") or []
        keywords = entry.get("keywords") or entry.get("kw") or []
        patterns.append(
            ClinicalPattern(
                pattern_id=entry.get("pattern_id") or entry.get("id"),
                condition_name=entry.get("condition_name") or entry.get("condition") or entry.get("name") or "",
                test_dependencies=list(test_deps),
                keywords=list(keywords),
                description=entry.get("description", ""),
                severity_level=entry.get("severity_level") or entry.get("severity") or "",
                possible_causes=entry.get("possible_causes") or entry.get("causes") or [],
                suggested_next_steps=entry.get("suggested_next_steps") or entry.get("next_steps") or [],
            )
        )
    return patterns


# Load patterns from external JSON file (preferred). If the JSON does not
# contain recognizable pattern entries, fall back to the original hardcoded
# patterns to preserve current functionality.
_loaded_patterns = _load_clinical_patterns_from_json()

# Original hardcoded patterns (kept as fallback to avoid breaking behavior)
_HARDCODED_CLINICAL_PATTERNS = [
# ANEMIA PATTERNS
    ClinicalPattern(
        pattern_id="anemia_iron_deficiency",
        condition_name="Iron Deficiency Anemia",
        test_dependencies=["hemoglobin", "hematocrit", "mcv", "mch"],
        keywords=["iron deficiency", "microcytic anemia", "hypochromic", "low iron"],
        description="Low Hb + Low MCV + Low MCHC/MCH — classic sign of microcytic hypochromic anemia",
        severity_level="moderate",
        possible_causes=["Iron deficiency", "Chronic blood loss", "Poor dietary intake"],
        suggested_next_steps=["Iron panel (ferritin, serum iron, TIBC)", "Hemoglobin recheck", "Dietary assessment"],
    ),
    ClinicalPattern(
        pattern_id="anemia_vitamin_b12",
        condition_name="Vitamin B12/Folate Deficiency Anemia",
        test_dependencies=["hemoglobin", "mcv", "rbc"],
        keywords=["B12 deficiency", "folate deficiency", "macrocytic anemia", "megaloblastic"],
        description="Low Hb + High MCV (large red cells) — suggests macrocytic anemia",
        severity_level="moderate",
        possible_causes=["Vitamin B12 deficiency", "Folate deficiency", "Pernicious anemia"],
        suggested_next_steps=["B12 level", "Folate level", "Parietal cell antibody test"],
    ),

# INFECTION/IMMUNE PATTERNS
    ClinicalPattern(
        pattern_id="infection_bacterial",
        condition_name="Bacterial Infection",
        test_dependencies=["wbc", "neutrophils_pct", "crp"],
        keywords=["bacterial infection", "elevated WBC", "left shift", "neutrophilia"],
        description="Elevated WBC + High neutrophils + High CRP — suggests active infection",
        severity_level="moderate",
        possible_causes=["Bacterial infection", "Pneumonia", "Urinary tract infection"],
        suggested_next_steps=["Blood cultures", "Imaging if indicated", "Antibiotic consideration"],
    ),
    ClinicalPattern(
        pattern_id="infection_viral",
        condition_name="Viral Infection",
        test_dependencies=["wbc", "lymphocytes_pct"],
        keywords=["viral infection", "lymphocytosis", "low neutrophils"],
        description="Normal/Low WBC + High lymphocytes — suggests viral infection",
        severity_level="mild",
        possible_causes=["Viral infection", "Acute viral syndrome"],
        suggested_next_steps=["Supportive care", "Repeat labs if symptoms persist"],
    ),

# IRON METABOLISM PATTERNS
    ClinicalPattern(
        pattern_id="iron_overload",
        condition_name="Iron Overload",
        test_dependencies=["iron", "ferritin", "tibc"],
        keywords=["hemochromatosis", "iron overload", "high ferritin", "saturation"],
        description="Elevated Iron + High Ferritin + Low TIBC — suggests iron overload",
        severity_level="moderate",
        possible_causes=["Hemochromatosis", "Multiple transfusions", "Iron supplementation"],
        suggested_next_steps=["Transferrin saturation", "Genetic testing for HFE", "Iron chelation therapy"],
    ),

# LIPID PATTERNS
    ClinicalPattern(
        pattern_id="dyslipidemia_high_ldl",
        condition_name="Elevated LDL Cholesterol",
        test_dependencies=["ldl", "total_cholesterol"],
        keywords=["high LDL", "cardiovascular risk", "atherosclerosis risk"],
        description="High LDL + High total cholesterol — cardiovascular risk factor",
        severity_level="moderate",
        possible_causes=["Genetic predisposition", "Poor diet", "Sedentary lifestyle"],
        suggested_next_steps=["Diet modification", "Statin therapy consideration", "Exercise"],
    ),
    ClinicalPattern(
        pattern_id="dyslipidemia_low_hdl",
        condition_name="Low HDL Cholesterol",
        test_dependencies=["hdl"],
        keywords=["low HDL", "protective factor low", "cardiovascular risk"],
        description="Low HDL — lack of protective cholesterol",
        severity_level="moderate",
        possible_causes=["Sedentary lifestyle", "Smoking", "Metabolic syndrome"],
        suggested_next_steps=["Increase physical activity", "Smoking cessation", "Diet modification"],
    ),

# THYROID PATTERNS
    ClinicalPattern(
        pattern_id="thyroid_hypothyroidism",
        condition_name="Hypothyroidism",
        test_dependencies=["tsh"],
        keywords=["high TSH", "hypothyroidism", "low thyroid function"],
        description="High TSH — suggests primary hypothyroidism",
        severity_level="moderate",
        possible_causes=["Hashimoto's thyroiditis", "Iodine deficiency", "Post-thyroidectomy"],
        suggested_next_steps=["Free T4 level", "TPO antibodies", "Levothyroxine initiation"],
    ),
    ClinicalPattern(
        pattern_id="thyroid_hyperthyroidism",
        condition_name="Hyperthyroidism",
        test_dependencies=["tsh", "t3", "t4"],
        keywords=["low TSH", "hyperthyroidism", "high thyroid function"],
        description="Low TSH + High T3/T4 — suggests primary hyperthyroidism",
        severity_level="moderate",
        possible_causes=["Graves disease", "Thyroiditis", "Toxic multinodular goiter"],
        suggested_next_steps=["TSI/TRAb antibodies", "Thyroid ultrasound", "Endocrinology referral"],
    ),

# KIDNEY PATTERNS
    ClinicalPattern(
        pattern_id="kidney_dysfunction",
        condition_name="Renal Dysfunction",
        test_dependencies=["creatinine", "urea"],
        keywords=["renal function", "kidney disease", "elevated creatinine"],
        description="Elevated Creatinine + Elevated Urea — suggests reduced kidney function",
        severity_level="moderate",
        possible_causes=["Chronic kidney disease", "Acute kidney injury", "Dehydration"],
        suggested_next_steps=["Estimated GFR", "Urinalysis", "Renal imaging if indicated"],
    ),

# LIVER PATTERNS
    ClinicalPattern(
        pattern_id="liver_hepatitis",
        condition_name="Hepatitis/Liver Inflammation",
        test_dependencies=["alt", "ast", "bilirubin"],
        keywords=["elevated transaminases", "hepatitis", "liver inflammation"],
        description="Elevated ALT/AST + High Bilirubin — suggests hepatocellular injury",
        severity_level="moderate",
        possible_causes=["Viral hepatitis", "Alcoholic liver disease", "Autoimmune hepatitis"],
        suggested_next_steps=["Viral hepatitis serologies", "Liver function panel", "Hepatology referral"],
    ),
    ClinicalPattern(
        pattern_id="liver_cirrhosis",
        condition_name="Cirrhosis/Advanced Liver Disease",
        test_dependencies=["alt", "ast", "albumin", "bilirubin"],
        keywords=["cirrhosis", "advanced liver disease", "low albumin", "coagulopathy"],
        description="Elevated ALT/AST + Low Albumin + High Bilirubin — suggests cirrhosis",
        severity_level="severe",
        possible_causes=["Alcoholic cirrhosis", "Viral hepatitis C", "Nonalcoholic fatty liver disease"],
        suggested_next_steps=["Liver ultrasound with Doppler", "Platelet count", "INR/PT", "Hepatology referral"],
    ),

# METABOLIC PATTERNS
    ClinicalPattern(
        pattern_id="electrolyte_hyponatremia",
        condition_name="Low Sodium (Hyponatremia)",
        test_dependencies=["sodium"],
        keywords=["low sodium", "hyponatremia", "hypo-osmolarity"],
        description="Low Sodium — altered fluid/electrolyte balance",
        severity_level="moderate",
        possible_causes=["SIADH", "Dehydration", "Liver/kidney disease"],
        suggested_next_steps=["Osmolality check", "Urine sodium", "Fluid restriction or hypertonic saline"],
    ),
    ClinicalPattern(
        pattern_id="electrolyte_hyperkalemia",
        condition_name="High Potassium (Hyperkalemia)",
        test_dependencies=["potassium"],
        keywords=["high potassium", "hyperkalemia", "cardiac risk"],
        description="High Potassium — can cause cardiac arrhythmias",
        severity_level="severe",
        possible_causes=["Renal failure", "Hemolysis in sample", "Rhabdomyolysis"],
        suggested_next_steps=["ECG", "Repeat K+ (rule out hemolysis)", "Calcium/glucose/insulin if critical"],
    ),

# PLATELET / CBC PATTERNS
    ClinicalPattern(
        pattern_id="rdw_high",
        condition_name="Elevated RDW (Anisocytosis)",
        test_dependencies=["rdw", "rdw_sd"],
        keywords=["high RDW", "anisocytosis", "red cell distribution width"],
        description="High RDW — red blood cells vary significantly in size",
        severity_level="mild",
        possible_causes=["Iron deficiency", "B12/folate deficiency", "Mixed anemia", "Recent blood loss"],
        suggested_next_steps=["CBC recheck", "Iron studies", "B12 and folate levels"],
    ),
    ClinicalPattern(
        pattern_id="mpv_abnormal",
        condition_name="Abnormal Mean Platelet Volume",
        test_dependencies=["mpv"],
        keywords=["high MPV", "low MPV", "platelet volume", "mean platelet volume"],
        description="Abnormal MPV — may indicate platelet production or destruction issues",
        severity_level="mild",
        possible_causes=["High MPV: Increased platelet destruction", "Low MPV: Bone marrow disorder", "Inflammatory conditions"],
        suggested_next_steps=["Platelet count recheck", "Peripheral smear review", "Clinical correlation"],
    ),
    ClinicalPattern(
        pattern_id="pdw_high",
        condition_name="Elevated Platelet Distribution Width",
        test_dependencies=["pdw"],
        keywords=["high PDW", "platelet distribution width", "platelet anisocytosis"],
        description="High PDW — variation in platelet size, often seen with high MPV",
        severity_level="mild",
        possible_causes=["Increased platelet turnover", "Inflammatory conditions", "Iron deficiency"],
        suggested_next_steps=["Repeat CBC with platelet parameters", "Iron studies", "Clinical correlation"],
    ),

# GLUCOSE CONTROL PATTERNS
    ClinicalPattern(
        pattern_id="diabetes_poorly_controlled",
        condition_name="Poorly Controlled Diabetes",
        test_dependencies=["glucose_fasting", "hba1c"],
        keywords=["high glucose", "high HbA1c", "diabetes", "hyperglycemia"],
        description="High fasting glucose + High HbA1c — indicates poor glycemic control",
        severity_level="moderate",
        possible_causes=["Type 2 diabetes", "Inadequate medication", "Poor compliance"],
        suggested_next_steps=["Intensify medications", "Dietary counseling", "Endocrinology referral"],
    ),
]

# Prefer loaded patterns when they look valid, otherwise use the fallback
if _loaded_patterns and all(getattr(p, "pattern_id", None) for p in _loaded_patterns):
    CLINICAL_PATTERNS = _loaded_patterns
else:
    CLINICAL_PATTERNS = _HARDCODED_CLINICAL_PATTERNS

# Create pattern index for O(1) lookup
PATTERN_BY_ID = {p.pattern_id: p for p in CLINICAL_PATTERNS}

# Create reverse index: test_key → patterns that use it (for retrieval optimization)
PATTERNS_BY_TEST = {}
for pattern in CLINICAL_PATTERNS:
    for test_key in pattern.test_dependencies:
        if test_key not in PATTERNS_BY_TEST:
            PATTERNS_BY_TEST[test_key] = []
        PATTERNS_BY_TEST[test_key].append(pattern.pattern_id)


# TEST CATEGORIZATION — retrieval bucketing

TEST_CATEGORIES = {
    "CBC": [
        "hemoglobin", "hematocrit", "rbc", "wbc", "platelets",
        "mcv", "mch", "mchc", "rdw", "rdw_sd", "mpv", "pdw"
    ],
    "Differential": [
        "neutrophils_pct", "neutrophils_abs", "lymphocytes_pct",
        "monocytes_pct", "eosinophils_pct", "basophils_pct"
    ],
    "Metabolic": [
        "glucose_fasting", "hba1c", "sodium", "potassium",
        "chloride", "calcium", "magnesium", "phosphorus"
    ],
    "Kidney": ["creatinine", "urea", "uric_acid"],
    "Liver": ["alt", "ast", "alp", "ggt", "total_bilirubin", "direct_bilirubin", "indirect_bilirubin", "albumin", "total_protein", "ag_ratio", "bilirubin"],
    "Lipids": ["total_cholesterol", "ldl", "hdl", "triglycerides", "vldl", "non_hdl_cholesterol"],
    "Thyroid": ["tsh", "free_t4", "free_t3", "t3", "t4"],
    "Iron": ["iron", "ferritin", "tibc"],
    "Vitamins": ["vitamin_d", "vitamin_b12"],
    "Inflammatory": ["esr", "crp"],
}

# Reverse map: test_key → category (for future retrieval/bucketing)
TEST_KEY_TO_CATEGORY = {}
for category, test_keys in TEST_CATEGORIES.items():
    for test_key in test_keys:
        TEST_KEY_TO_CATEGORY[test_key] = category


# RETRIEVAL HELPER FUNCTIONS (future vector search fallback)

def get_patterns_for_test(test_key: str) -> list[str]:
    """
    Returns pattern IDs that involve this test.

    FUTURE: This will be enhanced with semantic similarity when vectors are available.
    Currently: keyword and structural matching.
    """
    return PATTERNS_BY_TEST.get(test_key, [])


def get_patterns_by_category(category: str) -> list[str]:
    """
    Returns all pattern IDs for a clinical category.

    FUTURE: Can be vectorized and sorted by relevance.
    """
    if category not in TEST_CATEGORIES:
        return []
    test_keys = TEST_CATEGORIES[category]
    pattern_ids = set()
    for test_key in test_keys:
        pattern_ids.update(PATTERNS_BY_TEST.get(test_key, []))
    return list(pattern_ids)


def find_patterns_by_keywords(keywords: list[str]) -> list[str]:
    """
    Keyword-based pattern search.

    FUTURE: Will be supplemented with vector similarity search.
    Currently: exact keyword matching as fallback.
    """
    matches = []
    keyword_set = {kw.lower() for kw in keywords}
    for pattern in CLINICAL_PATTERNS:
        pattern_keywords = {kw.lower() for kw in pattern.keywords}
        if pattern_keywords & keyword_set:  # intersection
            matches.append(pattern.pattern_id)
    return matches
