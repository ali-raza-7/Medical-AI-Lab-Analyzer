"""
Test-name resolver — semantic + deterministic alias lookup + fuzzy fallback.

Resolution tiers (in order):
  1. Exact normalized alias match       → confidence 1.0
  2. Semantic similarity search (≥0.7)  → confidence 0.85–0.95
  3. Token-set fuzzy match (≥0.82)      → confidence 0.75–0.85
  4. Fuzzy best-effort match (≥0.65)    → confidence 0.60–0.75
  5. No match                           → None, confidence 0.0

SEMANTIC RETRIEVAL:
- Uses sentence-transformers embeddings for meaning-based matching
- Searches vector store of test definitions and patterns
- Gracefully degrades to fuzzy matching if embeddings unavailable
"""

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

# ═══════════════════════════════════════════════════════════════════════════════
# ALIAS TABLE  (normalized name → canonical key)
# ═══════════════════════════════════════════════════════════════════════════════
ALIASES: dict[str, str] = {
    # ── CBC ──────────────────────────────────────────────────────────────────
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
    "rdwcv":                      "rdw",
    "pow":                        "rdw",

    # ── Differential WBC ─────────────────────────────────────────────────────
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

    "absolute neutrophil count":  "neutrophils_abs",
    "anc":                        "neutrophils_abs",
    "neutrophils abs":            "neutrophils_abs",
    "neutrophil absolute":        "neutrophils_abs",
    "abs neutrophils":            "neutrophils_abs",
    "abs neutrophil count":       "neutrophils_abs",
    "absolute neutrophils":       "neutrophils_abs",
    "absolute neutrophil":        "neutrophils_abs",

    "absolute lymphocyte count":  "lymphocytes_abs",
    "lymphs":                     "lymphocytes_pct",
    "limphocyte":                 "lymphocytes_pct",   # OCR: i->m
    "lymphosytes":                "lymphocytes_pct",   # OCR: misspell
    "lympocytes":                 "lymphocytes_pct",   # OCR: missing h
    "lymphocyte %":               "lymphocytes_pct",
    "absolute lymphocyte":        "lymphocytes_abs",
    "alc":                        "lymphocytes_abs",
    "lymphocytes absolute":       "lymphocytes_abs",
    "lymphocytes":                "lymphocytes_pct",
    "lymphocyte":                 "lymphocytes_pct",
    "lymphocyte count":           "lymphocytes_pct",

    "monocytes":                  "monocytes_pct",
    "monocyte":                   "monocytes_pct",
    "monocyte count":             "monocytes_pct",
    "monos":                      "monocytes_pct",
    "monocyte %":                 "monocytes_pct",
    "monocytes %":                "monocytes_pct",

    "eosinophils":                "eosinophils_pct",
    "eosinophil":                 "eosinophils_pct",
    "eosnophis":                  "eosinophils_pct",   # common OCR damage
    "eosnophils":                 "eosinophils_pct",
    "eosinophil count":           "eosinophils_pct",
    "eos":                        "eosinophils_pct",
    "eosniophils":                "eosinophils_pct",   # OCR: n->ni
    "eosinophil %":               "eosinophils_pct",
    "eosinophils %":              "eosinophils_pct",

    "basophils":                  "basophils_pct",
    "basophil":                   "basophils_pct",
    "basos":                      "basophils_pct",
    "basophil %":                 "basophils_pct",
    "basophils %":                "basophils_pct",

    # ── Metabolic ─────────────────────────────────────────────────────────────
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

    # ── Electrolytes ──────────────────────────────────────────────────────────
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

    # ── Lipids ────────────────────────────────────────────────────────────────
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

    # ── Thyroid ───────────────────────────────────────────────────────────────
    "tsh":                        "tsh",
    "thyroid stimulating hormone":"tsh",
    "thyrotropin":                "tsh",
    "s.tsh":                      "tsh",
    "thyroid stimulating hormonal":"tsh",

    "t3":                         "t3",
    "free t3":                    "t3",
    "ft3":                        "t3",
    "triiodothyronine":           "t3",
    "free triiodothyronine":      "t3",

    "t4":                         "t4",
    "free t4":                    "t4",
    "ft4":                        "t4",
    "thyroxine":                  "t4",
    "free thyroxine":             "t4",

    # ── Liver Function ────────────────────────────────────────────────────────
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

    "bilirubin":                  "bilirubin",
    "total bilirubin":            "bilirubin",
    "serum bilirubin":            "bilirubin",
    "t.bilirubin":                "bilirubin",

    "albumin":                    "albumin",
    "serum albumin":              "albumin",
    "s.albumin":                  "albumin",

    # ── Iron Studies ──────────────────────────────────────────────────────────
    "iron":                       "iron",
    "serum iron":                 "iron",
    "fe":                         "iron",

    "ferritin":                   "ferritin",
    "serum ferritin":             "ferritin",

    "tibc":                       "tibc",
    "total iron binding capacity":"tibc",

    # ── Vitamins ──────────────────────────────────────────────────────────────
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

    # ── Inflammatory Markers ──────────────────────────────────────────────────
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
}

# Pre-build a list of (normalized_key, canonical_key) for fuzzy search
_ALIAS_KEYS: list[tuple[str, str]] = list(ALIASES.items())


# ═══════════════════════════════════════════════════════════════════════════════
# FUZZY MATCHING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _token_sort(s: str) -> str:
    """Sort tokens alphabetically for token-set similarity."""
    return " ".join(sorted(s.split()))


def _similarity(a: str, b: str) -> float:
    """Combined similarity: max of direct ratio and token-sort ratio."""
    direct = SequenceMatcher(None, a, b).ratio()
    token  = SequenceMatcher(None, _token_sort(a), _token_sort(b)).ratio()
    return max(direct, token)


# ═══════════════════════════════════════════════════════════════════════════════
# SEMANTIC RETRIEVAL LAYER (RAG)
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_test_key(raw_test_name: str) -> Optional[str]:
    """Resolve a raw test name to canonical key. Returns None if unresolvable."""
    key, _ = resolve_test_key_with_confidence(raw_test_name)
    return key


@lru_cache(maxsize=512)
def resolve_test_key_with_confidence(
    raw_test_name: str,
    fuzzy_threshold: float = 0.65,
) -> tuple[Optional[str], float]:
    """
    Resolve raw test name to (canonical_key, confidence).

    Resolution order:
      1. Exact alias match                    → confidence 1.00
      2. Semantic similarity search (≥0.7)    → confidence 0.85–0.95
      3. Fuzzy match (≥0.82)                  → confidence 0.75–0.85
      4. Low fuzzy match (≥0.65)              → confidence 0.60–0.75
      5. No match                             → None, 0.00
    
    Semantic search uses vector embeddings for meaning-based retrieval,
    providing better accuracy for OCR errors and synonyms.
    Falls back gracefully to fuzzy matching if embeddings unavailable.
    """
    n = normalize_test_name(raw_test_name)
    if not n:
        return None, 0.0

    # Tier 1: exact normalized alias match
    if n in ALIASES:
        logger.debug("[resolver] exact match %r → %r", n, ALIASES[n])
        return ALIASES[n], 1.0

    # Tier 2: SEMANTIC SEARCH (new RAG layer)
    semantic_result = _resolve_semantic(raw_test_name)
    if semantic_result:
        canonical_key, semantic_score = semantic_result
        confidence = min(0.95, 0.80 + semantic_score * 0.15)  # 0.80-0.95 range
        logger.info(
            "[resolver] semantic match %r → %r (score=%.3f, confidence=%.2f)",
            n, canonical_key, semantic_score, confidence,
        )
        return canonical_key, round(confidence, 2)

    # Tier 3: fuzzy search across all alias keys
    best_score = 0.0
    best_key: Optional[str] = None

    for alias_norm, canonical in _ALIAS_KEYS:
        score = _similarity(n, alias_norm)
        if score > best_score:
            best_score = score
            best_key = canonical

    # Tier 3: High-confidence fuzzy (≥0.82)
    if best_score >= 0.82 and best_key:
        confidence = min(0.85, 0.70 + best_score * 0.15)
        logger.info(
            "[resolver] high-confidence fuzzy %r → %r (score=%.2f, confidence=%.2f)",
            n, best_key, best_score, confidence,
        )
        return best_key, round(confidence, 2)

    # Tier 4: Low-confidence fuzzy (≥ fuzzy_threshold)
    if best_score >= fuzzy_threshold and best_key:
        confidence = min(0.75, 0.55 + best_score * 0.20)
        logger.info(
            "[resolver] fuzzy match %r → %r (score=%.2f, confidence=%.2f)",
            n, best_key, best_score, confidence,
        )
        return best_key, round(confidence, 2)

    logger.warning(
        "[resolver] no match for %r (normalized=%r, best_score=%.2f)",
        raw_test_name, n, best_score,
    )
    return None, 0.0