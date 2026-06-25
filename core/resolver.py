"""Test-name resolver — semantic + deterministic alias lookup + fuzzy fallback"""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Optional

from core.embeddings import SEMANTIC_SEARCH_AVAILABLE
from core.normalization import normalize_test_name

logger = logging.getLogger(__name__)

# RAG LAYER: Lazy import to avoid circular dependencies
def _get_vector_store():
    """Lazy import of vector store (only if needed)."""
    try:
        from core.vector_store import get_vector_store, is_vector_store_available
        if is_vector_store_available():
            return get_vector_store()
    except Exception as exc:
        logger.debug("[resolver] vector store not available: %s", exc)
    return None

# ALIAS TABLE  (normalized name → canonical key)
ALIASES: dict[str, str] = {
# CBC
    "wbc":                        "wbc",
    "wbc count":                  "wbc",
    "white blood cells":          "wbc",
    "white blood cell":           "wbc",
    "white blood cell count":     "wbc",
    "total wbc":                  "wbc",
    "t wbc":                      "wbc",
    "leukocytes":                 "wbc",
    "leukocyte count":            "wbc",
    "tlc":                        "wbc",
    "total leukocyte count":      "wbc",
    "total leucocyte count":      "wbc",
    "wbc count x 10 3 ul":        "wbc",   # Parsed form
    "white cell":                 "wbc",
    "white cells":                "wbc",

    "rbc":                        "rbc",
    "rbc count":                  "rbc",
    "red blood cells":            "rbc",
    "red blood cell":             "rbc",
    "red blood cell count":       "rbc",
    "erythrocytes":               "rbc",
    "erythrocyte count":          "rbc",
    "rbc count x 10 6 ul":        "rbc",   # Parsed form
    "red cell":                   "rbc",
    "red cells":                  "rbc",

    "platelets":                  "platelets",
    "platelet":                   "platelets",
    "plt":                        "platelets",
    "plt count":                  "platelets",
    "platelet count":             "platelets",
    "thrombocytes":               "platelets",
    "thrombocyte count":          "platelets",
    "plateletcount":              "platelets",

    "hemoglobin":                 "hemoglobin",
    "haemoglobin":                "hemoglobin",
    "hb":                         "hemoglobin",
    "hgb":                        "hemoglobin",
    "hemoglobn":                  "hemoglobin",
    "hemglobin":                  "hemoglobin",

    "hematocrit":                 "hematocrit",
    "haematocrit":                "hematocrit",
    "hct":                        "hematocrit",
    "packed cell volume":         "hematocrit",
    "pcv":                        "hematocrit",

    "mcv":                        "mcv",
    "mean corpuscular volume":    "mcv",
    "mean cell volume":           "mcv",

    "mch":                        "mch",
    "mean corpuscular hemoglobin":"mch",
    "mean cell hemoglobin":       "mch",

    "mchc":                       "mchc",
    "mean corpuscular hemoglobin concentration": "mchc",
    "mean cell hemoglobin concentration":        "mchc",

    "rdw":                        "rdw",
    "red cell distribution width":"rdw",
    "rdw-cv":                     "rdw",
    "rdw cv":                     "rdw",
    "rdw_cv":                     "rdw",
    "rdw-sd":                     "rdw_sd",
    "rdw sd":                     "rdw_sd",
    "rdw_sd":                     "rdw_sd",
    "r0w-cv":                     "rdw",
    "row-cv":                     "rdw",   # OCR: O→R in ROW
    "row-cv":                     "rdw",
    "rdwcv":                      "rdw",
    "pow":                        "rdw",

    "mpv":                        "mpv",
    "mean platelet volume":       "mpv",
    "mean platelet volume (mpv)":"mpv",
    "m p v":                      "mpv",
    "plateletcrit":               "plateletcrit",
    "pct":                        "plateletcrit",

    "pdw":                        "pdw",
    "platelet distribution width":"pdw",

# OCR-damaged CBC names
    "hematort":                   "hematocrit",
    "haematort":                  "hematocrit",
    "hemotocrit":                 "hematocrit",
    "hct.":                       "hematocrit",
    "total wbc count":            "wbc",
    "total wbc":                  "wbc",
    "total leucocyte":            "wbc",
    "total leukocyte":            "wbc",
    "leucocyte":                  "wbc",
    "leucocytes":                 "wbc",
    "red cell":                   "rbc",
    "red cells":                  "rbc",
    "red blood cell count (rbc)":"rbc",

    "mpv":                        "mpv",
    "mean platelet volume":       "mpv",
    "mean platelet volume (mpv)":"mpv",
    "m p v":                      "mpv",
    "plateletcrit":               "plateletcrit",
    "pct":                        "plateletcrit",

    "pdw":                        "pdw",
    "platelet distribution width":"pdw",

# Differential WBC
    "neutrophils":                "neutrophils_pct",
    "neutrophil":                 "neutrophils_pct",
    "neutrophil count":           "neutrophils_pct",
    "polymorphs":                 "neutrophils_pct",
    "segmented neutrophils":      "neutrophils_pct",
    "segs":                       "neutrophils_pct",
    "granulocytes":               "neutrophils_pct",
    "neutrofils":                 "neutrophils_pct",   # OCR: ph->f
    "neutophils":                 "neutrophils_pct",   # OCR: missing r
    "neutrophil %":               "neutrophils_pct",
    "neutrophils %":              "neutrophils_pct",
    "neut":                       "neutrophils_pct",

    "absolute neutrophil count":  "neutrophils_abs",
    "anc":                        "neutrophils_abs",
    "neutrophils abs":            "neutrophils_abs",
    "neutrophil absolute":        "neutrophils_abs",
    "abs neutrophils":            "neutrophils_abs",
    "abs neutrophil count":       "neutrophils_abs",
    "absolute neutrophils":       "neutrophils_abs",
    "absolute neutrophil":        "neutrophils_abs",
    "#neut":                      "neutrophils_abs",
    "abs neut":                   "neutrophils_abs",

    "absolute lymphocyte count":  "lymphocytes_abs",
    "lymphs":                     "lymphocytes_pct",
    "limphocyte":                 "lymphocytes_pct",   # OCR: i->m
    "lymphosytes":                "lymphocytes_pct",   # OCR: misspell
    "lympocytes":                 "lymphocytes_pct",   # OCR: missing h
    "lymphocyte %":               "lymphocytes_pct",
    "absolute lymphocyte":        "lymphocytes_abs",
    "alc":                        "lymphocytes_abs",
    "lymphocytes absolute":       "lymphocytes_abs",
    "#lymp":                      "lymphocytes_abs",
    "#lymph":                     "lymphocytes_abs",
    "abs lymp":                   "lymphocytes_abs",
    "lymphocytes":                "lymphocytes_pct",
    "lymphocyte":                 "lymphocytes_pct",
    "lymphocyte count":           "lymphocytes_pct",
    "lymp":                       "lymphocytes_pct",
    "lymph":                      "lymphocytes_pct",

    "monocytes":                  "monocytes_pct",
    "monocyte":                   "monocytes_pct",
    "monocyte count":             "monocytes_pct",
    "mono":                       "monocytes_pct",
    "monos":                      "monocytes_pct",
    "monocyte %":                 "monocytes_pct",
    "monocytes %":                "monocytes_pct",
    "menoenes":                   "monocytes_pct",   # OCR noise
    "mnoenes":                    "monocytes_pct",   # OCR noise
    "monoenes":                   "monocytes_pct",   # OCR noise
    "menones":                    "monocytes_pct",   # OCR noise

    "monocytes abs":              "monocytes_abs",
    "monocyte absolute":          "monocytes_abs",
    "absolute monocyte count":    "monocytes_abs",
    "absolute monocyte":          "monocytes_abs",
    "abs monocytes":              "monocytes_abs",
    "monocytes absolute":         "monocytes_abs",
    "abs monocyte count":         "monocytes_abs",
    "mono abs":                   "monocytes_abs",
    "monos abs":                  "monocytes_abs",
    "#mono":                      "monocytes_abs",
    "abs mono":                   "monocytes_abs",

    "eosinophils":                "eosinophils_pct",
    "eosinophil":                 "eosinophils_pct",
    "eosnophis":                  "eosinophils_pct",   # common OCR damage
    "eosnophils":                 "eosinophils_pct",
    "eosinophil count":           "eosinophils_pct",
    "eos":                        "eosinophils_pct",
    "eosniophils":                "eosinophils_pct",   # OCR: n->ni
    "eosinophil %":               "eosinophils_pct",
    "eosinophils %":              "eosinophils_pct",

    "eosinophils abs":            "eosinophils_abs",
    "eosinophil absolute":        "eosinophils_abs",
    "absolute eosinophil count":  "eosinophils_abs",
    "absolute eosinophil":        "eosinophils_abs",
    "abs eosinophils":            "eosinophils_abs",
    "eosinophils absolute":       "eosinophils_abs",
    "eos abs":                    "eosinophils_abs",
    "#eos":                       "eosinophils_abs",
    "abs eos":                    "eosinophils_abs",

    "basophils":                  "basophils_pct",
    "basophil":                   "basophils_pct",
    "basos":                      "basophils_pct",
    "basophil %":                 "basophils_pct",

    "basophils abs":              "basophils_abs",
    "basophil absolute":          "basophils_abs",
    "absolute basophil count":    "basophils_abs",
    "absolute basophil":          "basophils_abs",
    "abs basophils":              "basophils_abs",
    "basophils absolute":         "basophils_abs",
    "baso abs":                   "basophils_abs",
    "#baso":                      "basophils_abs",
    "abs baso":                   "basophils_abs",
    "basophils %":                "basophils_pct",

# Metabolic
    "glucose":                    "glucose_fasting",
    "blood sugar":                "glucose_fasting",
    "blood sugar fasting":        "glucose_fasting",
    "fasting glucose":            "glucose_fasting",
    "glucose fasting":            "glucose_fasting",
    "fasting blood sugar":        "glucose_fasting",
    "fbs":                        "glucose_fasting",
    "blood glucose":              "glucose_fasting",
    "rbs":                        "glucose_fasting",

    "creatinine":                 "creatinine",
    "serum creatinine":           "creatinine",
    "s.creatinine":               "creatinine",
    "s creatinine":               "creatinine",

    "urea":                       "urea",
    "blood urea":                 "urea",
    "bun":                        "bun",
    "blood urea nitrogen":        "bun",
    "serum urea":                 "urea",

    "uric acid":                  "uric_acid",
    "serum uric acid":            "uric_acid",
    "urate":                      "uric_acid",

    "hba1c":                      "hba1c",
    "a1c":                        "hba1c",
    "glycated hemoglobin":        "hba1c",
    "glycosylated hemoglobin":    "hba1c",
    "hemoglobin a1c":             "hba1c",
    "haemoglobin a1c":            "hba1c",
    "glycohemoglobin":            "hba1c",

    "insulin":                    "insulin_fasting",
    "fasting insulin":                    "insulin_fasting",
    "serum insulin":              "insulin_fasting",

# Electrolytes
    "sodium":                     "sodium",
    "na":                         "sodium",
    "serum sodium":               "sodium",
    "s.sodium":                   "sodium",

    "potassium":                  "potassium",
    "serum potassium":            "potassium",
    "s.potassium":                "potassium",

    "chloride":                   "chloride",
    "cl":                         "chloride",
    "serum chloride":             "chloride",

    "calcium":                    "calcium",
    "serum calcium":              "calcium",
    "s.calcium":                  "calcium",
    "total calcium":              "calcium",

    "magnesium":                  "magnesium",
    "serum magnesium":            "magnesium",
    "s.magnesium":                "magnesium",

    "phosphorus":                 "phosphorus",
    "phosphate":                  "phosphorus",
    "serum phosphorus":           "phosphorus",
    "serum phosphate":            "phosphorus",
    "inorganic phosphate":        "phosphorus",

# Lipids
    "cholesterol":                "total_cholesterol",
    "total cholesterol":          "total_cholesterol",
    "serum cholesterol":          "total_cholesterol",
    "t.cholesterol":              "total_cholesterol",

    "ldl":                        "ldl",
    "ldl cholesterol":            "ldl",
    "low density lipoprotein":    "ldl",
    "ldl-c":                      "ldl",

    "hdl":                        "hdl",
    "hdl cholesterol":            "hdl",
    "high density lipoprotein":   "hdl",
    "hdl-c":                      "hdl",

    "triglycerides":              "triglycerides",
    "triglyceride":               "triglycerides",
    "tg":                         "triglycerides",
    "serum triglycerides":        "triglycerides",
    "vldl":                       "vldl",
    "vldl cholesterol":           "vldl",

    "non-hdl cholesterol":        "non_hdl_cholesterol",
    "non hdl cholesterol":        "non_hdl_cholesterol",
    "non-hdl":                    "non_hdl_cholesterol",
    "non hdl":                    "non_hdl_cholesterol",
    "non-hdl-c":                  "non_hdl_cholesterol",

# Thyroid
    "tsh":                        "tsh",
    "thyroid stimulating hormone":"tsh",
    "thyrotropin":                "tsh",
    "s.tsh":                      "tsh",
    "thyroid stimulating hormonal":"tsh",

    "t3":                         "free_t3",
    "free t3":                    "free_t3",
    "ft3":                        "free_t3",
    "triiodothyronine":           "free_t3",
    "free triiodothyronine":      "free_t3",

    "t4":                         "free_t4",
    "free t4":                    "free_t4",
    "ft4":                        "free_t4",
    "thyroxine":                  "free_t4",
    "free thyroxine":             "free_t4",

# Liver Function
    "alt":                        "alt",
    "sgpt":                       "alt",
    "alanine aminotransferase":   "alt",
    "alanine transaminase":       "alt",
    "s.alt":                      "alt",

    "ast":                        "ast",
    "sgot":                       "ast",
    "aspartate aminotransferase": "ast",
    "aspartate transaminase":     "ast",
    "s.ast":                      "ast",

    "alp":                        "alp",
    "alkaline phosphatase":       "alp",
    "alk phos":                   "alp",
    "alk phosphatase":            "alp",

    "total bilirubin":            "total_bilirubin",
    "serum bilirubin":            "total_bilirubin",
    "t.bilirubin":                "total_bilirubin",
    "bilirubin":                  "total_bilirubin",

    "albumin":                    "albumin",
    "serum albumin":              "albumin",
    "s.albumin":                  "albumin",

    "ggt":                        "ggt",
    "gamma gt":                   "ggt",
    "gamma glutamyl transferase": "ggt",
    "ggtp":                       "ggt",

    "ag ratio":                   "ag_ratio",
    "a/g ratio":                  "ag_ratio",
    "albumin globulin ratio":     "ag_ratio",

    "direct bilirubin":           "direct_bilirubin",
    "bilirubin direct":           "direct_bilirubin",
    "conjugated bilirubin":       "direct_bilirubin",

    "indirect bilirubin":         "indirect_bilirubin",
    "bilirubin indirect":         "indirect_bilirubin",
    "unconjugated bilirubin":     "indirect_bilirubin",

# Iron Studies
    "iron":                       "iron",
    "serum iron":                 "iron",
    "fe":                         "iron",

    "ferritin":                   "ferritin",
    "serum ferritin":             "ferritin",

    "tibc":                       "tibc",
    "total iron binding capacity":"tibc",

# Vitamins
    "vitamin d":                  "vitamin_d",
    "vitamin d3":                 "vitamin_d",
    "25-oh vitamin d":            "vitamin_d",
    "25 oh vitamin d":            "vitamin_d",
    "25-hydroxyvitamin d":        "vitamin_d",
    "vit d":                      "vitamin_d",
    "vit.d":                      "vitamin_d",

    "vitamin b12":                "vitamin_b12",
    "b12":                        "vitamin_b12",
    "cobalamin":                  "vitamin_b12",
    "cyanocobalamin":             "vitamin_b12",
    "vit b12":                    "vitamin_b12",
    "vit.b12":                    "vitamin_b12",

# Inflammatory Markers
    "esr":                        "esr",
    "erythrocyte sedimentation rate": "esr",
    "sedimentation rate":         "esr",
    "westergren":                 "esr",

    "crp":                        "crp",
    "c-reactive protein":         "crp",
    "c reactive protein":         "crp",
    "hs-crp":                     "crp",
    "high sensitivity crp":       "crp",
    "hscrp":                      "crp",

# Liver / Protein Panel
    "total protein":              "total_protein",
    "protein total":              "total_protein",
    "serum total protein":        "total_protein",
    "serum protein":              "total_protein",
    "t.protein":                  "total_protein",
    "total proteins":             "total_protein",

    "globulin":                   "globulin",
    "serum globulin":             "globulin",
    "s.globulin":                 "globulin",
    "globulins":                  "globulin",

    "a/g ratio":                  "ag_ratio",
    "ag ratio":                   "ag_ratio",
    "albumin/globulin":           "ag_ratio",
    "albumin globulin ratio":     "ag_ratio",
    "a g ratio":                  "ag_ratio",

    "direct bilirubin":           "direct_bilirubin",
    "bilirubin direct":           "direct_bilirubin",
    "conjugated bilirubin":       "direct_bilirubin",
    "d.bilirubin":                "direct_bilirubin",
    "bili direct":                "direct_bilirubin",

    "indirect bilirubin":         "indirect_bilirubin",
    "bilirubin indirect":         "indirect_bilirubin",
    "unconjugated bilirubin":     "indirect_bilirubin",
    "i.bilirubin":                "indirect_bilirubin",
    "bili indirect":              "indirect_bilirubin",

# CBC extras
    "pdw":                        "pdw",
    "platelet distribution width":"pdw",

    "plateletcrit":               "plateletcrit",
    "pct":                        "plateletcrit",

    "nrbc":                       "nrbc",
    "nucleated rbc":              "nrbc",
    "nucleated red blood cells":  "nrbc",

# Lipids extras
    "non-hdl":                    "non_hdl_cholesterol",
    "non hdl":                    "non_hdl_cholesterol",
    "non hdl-c":                  "non_hdl_cholesterol",
    "vldl cholesterol":           "vldl",
    "very low density lipoprotein":"vldl",

# Glucose variants
    "postprandial glucose":       "postprandial_glucose",
    "post prandial glucose":      "postprandial_glucose",
    "ppbs":                       "postprandial_glucose",
    "pp glucose":                 "postprandial_glucose",
    "post meal glucose":          "postprandial_glucose",
    "2 hour ppbs":                "postprandial_glucose",

    "random glucose":             "random_glucose",
    "random blood sugar":         "random_glucose",
    "rbs":                        "random_glucose",
    "casual glucose":             "random_glucose",

# Coagulation
    "pt":                         "pt",
    "prothrombin time":           "pt",
    "p.t.":                       "pt",

    "inr":                        "inr",
    "international normalized ratio": "inr",

    "aptt":                       "aptt",
    "activated partial thromboplastin time": "aptt",
    "ptt":                        "aptt",
    "a.p.t.t.":                   "aptt",

    "d-dimer":                    "d_dimer",
    "d dimer":                    "d_dimer",
    "fibrinogen":                 "fibrinogen",

# Iron studies extras
    "transferrin saturation":     "transferrin_saturation",
    "iron saturation":            "transferrin_saturation",
    "tsat":                       "transferrin_saturation",
    "tibc":                       "tibc",
    "total iron binding capacity":"tibc",

# Kidney extras
    "egfr":                       "egfr",
    "estimated gfr":              "egfr",
    "glomerular filtration rate": "egfr",
    "bun/creatinine ratio":       "bun_creatinine_ratio",
    "bun creatinine ratio":       "bun_creatinine_ratio",

# Vitamins / Minerals extras
    "folate":                     "folate",
    "folic acid":                 "folate",
    "serum folate":               "folate",

    "zinc":                       "zinc",
    "serum zinc":                 "zinc",

    "copper":                     "copper",
    "serum copper":               "copper",

# Cardiac
    "troponin i":                 "troponin_i",
    "troponin-i":                 "troponin_i",
    "trop i":                     "troponin_i",

    "troponin t":                 "troponin_t",
    "troponin-t":                 "troponin_t",
    "trop t":                     "troponin_t",

    "ck-mb":                      "ck_mb",
    "ck mb":                      "ck_mb",
    "creatine kinase mb":         "ck_mb",

    "ck":                         "ck",
    "creatine kinase":            "ck",
    "cpk":                        "ck",
    "total cpk":                  "ck",

    "ldh":                        "ldh",
    "lactate dehydrogenase":      "ldh",

# Hormones
    "testosterone":               "testosterone",
    "serum testosterone":         "testosterone",
    "total testosterone":         "testosterone",

    "cortisol":                   "cortisol",
    "serum cortisol":             "cortisol",
    "morning cortisol":           "cortisol",

    "prolactin":                  "prolactin",
    "serum prolactin":            "prolactin",

    "lh":                         "lh",
    "luteinizing hormone":        "lh",

    "fsh":                        "fsh",
    "follicle stimulating hormone":"fsh",

    "dhea-s":                     "dhea_s",
    "dheas":                      "dhea_s",
    "dehydroepiandrosterone":     "dhea_s",

# Misc panel items
    "amylase":                    "amylase",
    "serum amylase":              "amylase",
    "lipase":                     "lipase",
    "serum lipase":               "lipase",
    "homocysteine":               "homocysteine",
    "serum homocysteine":         "homocysteine",
    "ammonia":                    "ammonia",
    "serum ammonia":              "ammonia",
    "lactate":                    "lactate",
    "lactic acid":                "lactate",
}

# Pre-build a list of (normalized_key, canonical_key) for fuzzy search
_ALIAS_KEYS: list[tuple[str, str]] = list(ALIASES.items())
_CANONICAL_KEYS: set[str] = set(ALIASES.values())


# FUZZY MATCHING HELPERS

def _token_sort(s: str) -> str:
    """Sort tokens alphabetically for token-set similarity."""
    return " ".join(sorted(s.split()))


def _similarity(a: str, b: str) -> float:
    """Combined similarity: max of direct ratio and token-sort ratio."""
    direct = SequenceMatcher(None, a, b).ratio()
    token  = SequenceMatcher(None, _token_sort(a), _token_sort(b)).ratio()
    return max(direct, token)


# SEMANTIC RETRIEVAL LAYER (RAG)

def _resolve_semantic(raw_test_name: str) -> Optional[tuple[str, float]]:
    """
    Attempt to resolve test name using semantic similarity search.

    Returns:
        (canonical_key, semantic_score) if found, None otherwise
    """
    if not SEMANTIC_SEARCH_AVAILABLE:
        logger.debug("[resolver] semantic search unavailable due to missing embeddings package")
        return None

    store = _get_vector_store()
    if store is None or not store.is_available():
        logger.debug("[resolver] semantic search unavailable: vector store unavailable")
        return None

    try:
# Search for test definitions in vector store
# Query format: include the raw test name for semantic matching
        query = f"test: {raw_test_name}"

# Use cached search if available, otherwise regular search
        if hasattr(store, "cached_search"):
            results = store.cached_search(query, k=5, threshold=0.5)
        else:
            results = store.search(query, k=5, threshold=0.5)

        if not results:
            logger.debug("[resolver] semantic search found no results for %r", raw_test_name)
            return None

# Find the best matching test definition
        for doc_id, score in results:
# Extract test key from doc_id (format: "test_<test_key>" or "test_clinical_<test_key>")
            if doc_id.startswith("test_"):
                key_part = doc_id.replace("test_clinical_", "").replace("test_", "")
                if key_part in ALIASES.values():
                    logger.debug(
                        "[resolver] semantic search matched %r → %s (score=%.3f)",
                        raw_test_name, key_part, score
                    )
                    return key_part, score

# If we found results but couldn't extract a valid test key, return None
        logger.debug("[resolver] semantic search matched but couldn't extract valid test key for %r", raw_test_name)
        return None

    except Exception as exc:
        logger.warning("[resolver] semantic search failed for %r: %s", raw_test_name, exc)
        return None


# PUBLIC API

def resolve_test_key(raw_test_name: str) -> Optional[str]:
    """Resolve a raw test name to canonical key. Returns None if unresolvable."""
    key, _ = resolve_test_key_with_confidence(raw_test_name)
    return key


@lru_cache(maxsize=512)
def resolve_test_key_with_confidence(
    raw_test_name: str,
    fuzzy_threshold: float = 0.65,
) -> tuple[Optional[str], float]:
    """Resolve raw test name to (canonical_key, confidence)"""
    n = normalize_test_name(raw_test_name)
    if not n:
        return None, 0.0

# Tier 0: Handle # prefix for absolute counts (#NEUT → neutrophils_abs)
    if raw_test_name.startswith("#"):
        base_key, base_conf = resolve_test_key_with_confidence(raw_test_name[1:])
        if base_key:
            base_root = base_key.rsplit("_", 1)[0] if "_" in base_key else base_key
            abs_candidate = base_root + "_abs"
            if abs_candidate in _CANONICAL_KEYS:
                logger.debug("[resolver] #-prefix absolute match %r → %r", raw_test_name, abs_candidate)
                return abs_candidate, 1.0

# Tier 1: exact normalized alias match
    if n in ALIASES:
        logger.debug("[resolver] exact match %r → %r", n, ALIASES[n])
        return ALIASES[n], 1.0

# Tier 2: Abbreviation embedded in raw name (only for merged OCR tokens)
# e.g. "MEAN CELL HAEMOGLOBIN CON,MCHC H" contains "MCHC" as a distinct code
    if "," in raw_test_name or "/" in raw_test_name:
        abbr_key = _extract_abbreviation(raw_test_name)
        if abbr_key:
            logger.info("[resolver] abbreviation match %r → %s via embedded code", raw_test_name, abbr_key)
            return abbr_key, 1.0

# Tier 3: SEMANTIC SEARCH
    semantic_result = _resolve_semantic(raw_test_name)
    if semantic_result:
        canonical_key, semantic_score = semantic_result
        confidence = min(0.95, 0.80 + semantic_score * 0.15)
        logger.info(
            "[resolver] semantic match %r → %r (score=%.3f, confidence=%.2f)",
            n, canonical_key, semantic_score, confidence,
        )
        return canonical_key, round(confidence, 2)

# Tier 4: fuzzy search across all alias keys
    best_score = 0.0
    best_key: Optional[str] = None

    for alias_norm, canonical in _ALIAS_KEYS:
        score = _similarity(n, alias_norm)
        if score > best_score:
            best_score = score
            best_key = canonical

# Tiebreaker: prefer longer canonical name when scores are close
# (prevents MCH from winning over MCHC)
    if best_key:
        for alias_norm, canonical in _ALIAS_KEYS:
            if canonical != best_key:
                score = _similarity(n, alias_norm)
                if abs(score - best_score) < 0.05 and len(canonical) > len(best_key):
                    best_key = canonical
                    best_score = score

    if best_score >= 0.82 and best_key:
        confidence = min(0.85, 0.70 + best_score * 0.15)
        logger.info(
            "[resolver] high-confidence fuzzy %r → %r (score=%.2f, confidence=%.2f)",
            n, best_key, best_score, confidence,
        )
        return best_key, round(confidence, 2)

    if best_score >= fuzzy_threshold and best_key:
        confidence = min(0.75, 0.55 + best_score * 0.20)
        logger.info(
            "[resolver] fuzzy match %r → %r (score=%.2f, confidence=%.2f)",
            n, best_key, best_score, confidence,
        )
        return best_key, round(confidence, 2)

    logger.warning(
        "[dropped] test_name=%s confidence=%.2f",
        raw_test_name, 0.0,
    )
    return None, 0.0


_SHORT_ABBR = re.compile(r"^[A-Z0-9]{2,6}$")


def _find_abbr_in_name(raw: str) -> str | None:
    """Extract known abbreviation tokens (prefers short all-caps)."""
    parts = re.split(r"[\s,/+]+", raw)
# First pass: look for short all-caps abbreviations
    for part in parts:
        p = part.strip()
        if _SHORT_ABBR.match(p) and p.lower() in ALIASES:
            return p.lower()
# Second pass: any known alias
    for part in parts:
        p = part.strip().lower()
        if p in ALIASES:
            return p
    return None


def _extract_abbreviation(raw_test_name: str) -> str | None:
    """Resolve via known abbreviation token in raw test name."""
    abbr = _find_abbr_in_name(raw_test_name)
    if abbr:
        return ALIASES[abbr]
    return None
