from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

# EXISTING INSIGHT SOURCES
from medical.clinical_rules import FALLBACK_INSIGHTS, INSIGHTS_KB

# RAG LAYER: centralized pattern knowledge base (future retrieval source)
from medical.clinical_kb import (
    CLINICAL_PATTERNS,
    PATTERN_BY_ID,
    get_patterns_for_test,
    TEST_KEY_TO_CATEGORY,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LabResult:
    test_key: str
    test_name: str
    status: str             # low | normal | high | unknown
    value: float
    unit: str
    value_normalized: Optional[float] = None
    unit_normalized: Optional[str] = None


def _is_low(r: LabResult) -> bool:  return r.status == "low"
def _is_high(r: LabResult) -> bool: return r.status == "high"
def _is_ab(r: LabResult) -> bool:   return r.status in ("low", "high")


def _find(results: list[LabResult], *keys: str) -> Optional[LabResult]:
    """Find first result whose test_key matches any of the given keys."""
    k_set = {k.lower() for k in keys}
    for r in results:
        if r.test_key.lower() in k_set:
            return r
    return None


def _ab_count(results: list[LabResult]) -> int:
    return sum(1 for r in results if _is_ab(r))


# RAG LAYER: centralized pattern retrieval helpers
# SEMANTIC RETRIEVAL: vector similarity search for clinical patterns

def _get_vector_store():
    """Lazy import of vector store (only if needed)."""
    try:
        from core.vector_store import get_vector_store, is_vector_store_available
        if is_vector_store_available():
            return get_vector_store()
    except Exception as exc:
        logger.debug("[insights] vector store not available: %s", exc)
    return None


def get_applicable_patterns_for_test(test_key: str) -> list[dict]:
    """Retrieve patterns applicable to this test from centralized KB"""
# Tier 1: Try semantic search
    semantic_patterns = _retrieve_patterns_semantic(test_key)
    if semantic_patterns:
        logger.debug("[insights] retrieved %d patterns via semantic search for %s",
                    len(semantic_patterns), test_key)
        return semantic_patterns

# Tier 2: Fall back to rule-based retrieval
    logger.debug("[insights] falling back to rule-based pattern retrieval for %s", test_key)
    pattern_ids = get_patterns_for_test(test_key)
    return [
        {
            "pattern_id": pid,
            "name": PATTERN_BY_ID[pid].condition_name,
            "keywords": PATTERN_BY_ID[pid].keywords,
            "severity": PATTERN_BY_ID[pid].severity_level,
            "possible_causes": PATTERN_BY_ID[pid].possible_causes,
        }
        for pid in pattern_ids
    ]


def _retrieve_patterns_semantic(test_key: str) -> list[dict]:
    """
    Retrieve clinical patterns using semantic similarity search.

    Returns:
        List of pattern dicts (enriched metadata) or empty list if search unavailable
    """
    store = _get_vector_store()
    if store is None:
        return []

    try:
# Search for patterns related to this test
        query = f"test: {test_key} clinical patterns"
        results = store.search(query, k=5, threshold=0.5)

        if not results:
            logger.debug("[insights] semantic search found no patterns for %s", test_key)
            return []

# Extract pattern IDs from results and build result list
        retrieved_patterns = []
        seen_ids = set()

        for doc_id, score in results:
# Extract pattern ID from doc_id (format: "pattern_<pattern_id>" or "pattern_keywords_<pattern_id>")
            if "pattern_" in doc_id:
                pid = doc_id.replace("pattern_keywords_", "").replace("pattern_", "")

# Avoid duplicates and ensure pattern exists
                if pid not in seen_ids and pid in PATTERN_BY_ID:
                    seen_ids.add(pid)
                    pattern = PATTERN_BY_ID[pid]
                    retrieved_patterns.append({
                        "pattern_id": pid,
                        "name": pattern.condition_name,
                        "keywords": pattern.keywords,
                        "severity": pattern.severity_level,
                        "possible_causes": pattern.possible_causes,
                        "semantic_score": round(score, 3),  # Include retrieval score
                    })

        logger.debug("[insights] semantic search returned %d patterns for %s",
                    len(retrieved_patterns), test_key)
        return retrieved_patterns

    except Exception as exc:
        logger.warning("[insights] semantic pattern retrieval failed for %s: %s", test_key, exc)
        return []

def _determine_severity_level(
    value: float,
    ref_min: float,
    ref_max: float,
    status: str,
    test_key: str = "",
) -> str:
    if status.lower() not in ["high", "low"]:
        return "NORMAL"

    try:
        ref_min = float(ref_min)
        ref_max = float(ref_max)
        value = float(value)
    except (TypeError, ValueError):
        return f"MILD_{status.upper()}"

    range_span = ref_max - ref_min
    if range_span <= 0:
        return f"MILD_{status.upper()}"

    deviation = 0.0
    if status.lower() == "high":
        deviation = (value - ref_max) / range_span
    elif status.lower() == "low":
        deviation = (ref_min - value) / range_span

    tk = test_key.lower()
    if tk in ["eosinophils", "lymphocytes", "monocytes", "basophils", "neutrophils"]:
        deviation = deviation * 0.2
    elif tk in ["mchc", "mcv", "mch", "rdw"]:
        deviation = deviation * 0.3
    elif tk in ["ast", "alt", "alp", "ferritin", "triglycerides", "tsh"]:
        deviation = deviation * 0.1
    elif tk in ["glucose_fasting", "cholesterol", "ldl", "hdl"]:
        deviation = deviation * 0.5
    elif tk in ["sodium", "potassium", "calcium", "magnesium"]:
        deviation = deviation * 3.0
    elif tk in ["ph", "pco2", "po2"]:
        deviation = deviation * 5.0

    if deviation > 2.0:
        return f"CRITICAL_{status.upper()}"
    elif deviation > 1.0:
        return f"SEVERE_{status.upper()}"
    elif deviation > 0.4:
        return f"MODERATE_{status.upper()}"
    else:
        return f"MILD_{status.upper()}"


def _get_age_context(age: int, base_context: Dict[str, Any]) -> str:
    if age < 30:
        return base_context.get("young", "")
    elif age < 50:
        return base_context.get("adult", "")
    elif age < 65:
        return base_context.get("senior", "")
    else:
        return base_context.get("elderly", "")


def _get_gender_context(gender: str, base_context: Dict[str, Any]) -> str:
    g = gender.lower()
    if g == "male":
        return base_context.get("male", "")
    elif g == "female":
        return base_context.get("female", "")
    return ""


def generate_clinical_insight(
    test_key: str,
    test_name: str,
    value: float,
    ref_min: float,
    ref_max: float,
    status: str,
    age: int,
    gender: str,
) -> Optional[Dict[str, Any]]:
    if status.lower() not in ["high", "low"]:
        return None

    kb_entry = INSIGHTS_KB.get(test_key)
    if not kb_entry:
        for k, v in INSIGHTS_KB.items():
            if test_name.lower() in k.lower() or k.lower() in test_key.lower():
                kb_entry = v
                break

    if not kb_entry:
        kb_entry = FALLBACK_INSIGHTS

    direction_data = kb_entry.get(status.lower())
    if not direction_data:
        direction_data = FALLBACK_INSIGHTS.get(status.lower())

    severity_str = _determine_severity_level(value, ref_min, ref_max, status, test_key)
    summary = f"{test_name} is {severity_str.replace('_', ' ').lower()} for a {age}-year-old {gender}."

    possible_causes = direction_data.get("causes", ["Possible underlying condition", "Diet or lifestyle factors"])
    suggested_next_steps = direction_data.get("next_steps", ["Discuss with a healthcare provider"])

    age_related_risk = _get_age_context(age, direction_data.get("age_context", {}))
    gender_related_risk = _get_gender_context(gender, direction_data.get("gender_context", {}))

    if "CRITICAL" in severity_str:
        severity_comment = f"A {severity_str.replace('_', ' ').lower()} result requires medical evaluation to rule out acute issues."
    elif "SEVERE" in severity_str:
        severity_comment = f"A {severity_str.replace('_', ' ').lower()} result suggests a clear abnormality that warrants medical evaluation."
    elif "MODERATE" in severity_str:
        severity_comment = f"A {severity_str.replace('_', ' ').lower()} result indicates a variation that should be monitored and discussed with a doctor."
    else:
        severity_comment = f"A {severity_str.replace('_', ' ').lower()} result may be temporary or benign, but warrants observation."

    clinical_insight_dict = {
        "summary": summary,
        "severity": severity_str,
        "possible_causes": possible_causes,
        "severity_comment": severity_comment,
        "suggested_next_steps": suggested_next_steps,
    }
    if age_related_risk:
        clinical_insight_dict["age_related_risk"] = age_related_risk
    if gender_related_risk:
        clinical_insight_dict["gender_related_risk"] = gender_related_risk

    return {
        "test_name": test_name,
        "status": status.upper(),
        "clinical_insight": clinical_insight_dict,
    }


def generate_grouped_insights(results: list[LabResult]) -> dict:
    """
    Generate insights grouped by clinical category.
    Returns dict with both category-grouped flags and patterns.
    """
# Get pattern insights (existing function)
    patterns = generate_insights(results)

# Build category grouping
    by_category = {
        "CBC": [],
        "Differential": [],
        "Metabolic": [],
        "Kidney": [],
        "Liver": [],
        "Lipids": [],
        "Thyroid": [],
        "Iron": [],
        "Vitamins": [],
        "Inflammatory": [],
    }

    for result in results:
        if result.status in ("low", "high"):
            cat = TEST_KEY_TO_CATEGORY.get(result.test_key, None)
            if cat:
                flag = f"{'↓' if result.status == 'low' else '↑'} {result.test_name}"
                if flag not in by_category[cat]:
                    by_category[cat].append(flag)

# Remove empty categories
    by_category = {k: v for k, v in by_category.items() if v}

    return {
        "by_category": by_category,
        "patterns": patterns,
    }


# Internal Pattern Handlers

def _get_anemia_patterns(results: list[LabResult], insights: list[str]):
    hb    = _find(results, "hemoglobin")
    rbc   = _find(results, "rbc")
    mcv   = _find(results, "mcv")
    mch   = _find(results, "mch")
    mchc  = _find(results, "mchc")
    rdw   = _find(results, "rdw")
    ferr  = _find(results, "ferritin")
    b12   = _find(results, "vitamin_b12")

    if hb and _is_low(hb) and mcv and _is_low(mcv) and (
        (mchc and _is_low(mchc)) or (mch and _is_low(mch))
    ):
        insights.append(
            "🔴 Pattern: Low Hb + Low MCV + Low MCHC/MCH — this combination is a "
            "classic sign of microcytic hypochromic anemia, most commonly caused by "
            "iron deficiency. Iron studies (ferritin, serum iron, TIBC) are recommended."
        )
    elif hb and _is_low(hb) and ferr and _is_low(ferr):
        insights.append(
            "🔴 Pattern: Low Hb + Low Ferritin — strongly suggests iron deficiency anemia. "
            "Dietary iron or supplementation may be needed. Consult your doctor."
        )
    elif hb and _is_low(hb) and mcv and _is_high(mcv):
        insights.append(
            "🔴 Pattern: Low Hb + High MCV (large red cells) — suggests macrocytic anemia, "
            "commonly caused by Vitamin B12 or folate deficiency. "
            "B12 levels and dietary history should be reviewed."
        )
    elif hb and rbc and _is_low(hb) and _is_low(rbc):
        insights.append(
            "🔴 Pattern: Low Hb + Low RBC — consistent with anemia. "
            "Further evaluation can help identify whether it is due to blood loss, "
            "chronic disease, or reduced red cell production."
        )
    elif hb and _is_low(hb):
        insights.append(
            "⚠️ Low hemoglobin detected — may indicate anemia. "
            "Common causes include iron deficiency, chronic disease, or blood loss. "
            "A full CBC and iron panel can help narrow the cause."
        )

    if b12 and _is_low(b12) and hb and _is_low(hb) and mcv and _is_high(mcv):
        insights.append(
            "🔴 Pattern: Low B12 + Low Hb + High MCV — classic megaloblastic anemia. "
            "B12 or folate supplementation is typically required. Consult your doctor."
        )

    if rdw and _is_high(rdw) and hb and _is_low(hb):
        insights.append(
            "⚠️ High RDW + Low Hemoglobin — red blood cells vary significantly in size, "
            "which can occur in iron deficiency, B12/folate deficiency, or mixed anemia. "
            "Iron studies and B12 levels may help identify the cause."
        )

    if mchc and _is_low(mchc) and hb and _is_low(hb):
        insights.append(
            "⚠️ Low MCHC + Low Hemoglobin — red blood cells have less hemoglobin than normal "
            "(hypochromic anemia). Iron deficiency is the most common cause. "
            "Iron studies are recommended."
        )

def _get_infection_patterns(results: list[LabResult], insights: list[str]):
    wbc   = _find(results, "wbc")
    neut  = _find(results, "neutrophils", "neutrophils_abs")
    lymph = _find(results, "lymphocytes")
    eos   = _find(results, "eosinophils")
    esr   = _find(results, "esr")
    crp   = _find(results, "crp")

    if wbc and _is_high(wbc) and neut and _is_high(neut):
        insights.append(
            "🔴 Pattern: High WBC + High Neutrophils — strongly suggests bacterial "
            "infection or acute inflammation. Prompt medical evaluation is recommended."
        )
    elif wbc and _is_high(wbc) and lymph and _is_high(lymph):
        insights.append(
            "⚠️ Pattern: High WBC + High Lymphocytes — may suggest a viral infection "
            "(e.g., mononucleosis, viral fever). Consult your doctor for evaluation."
        )
    elif wbc and _is_high(wbc):
        insights.append(
            "⚠️ High WBC count — may indicate infection, inflammation, or stress response. "
            "This is not a diagnosis."
        )

    if neut and _is_low(neut):
        insights.append(
            "⚠️ Low neutrophil count (neutropenia) — increases risk of infection. "
            "This may be due to viral illness, medication side effects, or bone marrow issues. "
            "Discuss with your doctor promptly."
        )

    if eos and _is_high(eos):
        insights.append(
            "⚠️ Elevated eosinophils — may suggest allergic reaction, asthma, "
            "or parasitic infection. A clinical history review is recommended."
        )

    if esr and crp and _is_high(esr) and _is_high(crp):
        insights.append(
            "⚠️ Pattern: High ESR + High CRP — indicates active inflammation in the body. "
            "Could be infection, autoimmune condition, or tissue injury. Needs clinical evaluation."
        )

def _get_metabolic_patterns(results: list[LabResult], insights: list[str]):
    glc   = _find(results, "glucose_fasting")
    hba1c = _find(results, "hba1c")
    ldl   = _find(results, "ldl")
    hdl   = _find(results, "hdl")
    tg    = _find(results, "triglycerides")
    uric  = _find(results, "uric_acid")

    if glc and _is_high(glc) and hba1c and _is_high(hba1c):
        insights.append(
            "🔴 Pattern: High fasting glucose + High HbA1c — strongly suggests "
            "poorly controlled diabetes or undiagnosed diabetes. "
            "Medical evaluation and management plan is essential."
        )
    elif glc and _is_high(glc):
        insights.append(
            "⚠️ High fasting glucose — may indicate pre-diabetes or diabetes. "
            "HbA1c test can confirm the pattern over time."
        )
    elif hba1c and _is_high(hba1c):
        insights.append(
            "⚠️ High HbA1c — reflects elevated average blood sugar over 2–3 months. "
            "May indicate diabetes or poor glucose control. Discuss with your doctor."
        )
    elif glc and _is_low(glc):
        insights.append(
            "⚠️ Low fasting glucose (hypoglycemia) — may cause dizziness or fainting. "
            "Could be related to medication, diet, or other conditions. Seek evaluation."
        )

    if uric and _is_high(uric):
        insights.append(
            "⚠️ High uric acid (hyperuricemia) — may increase risk of gout or kidney stones. "
            "Dietary changes (reducing red meat, alcohol, fructose) may help."
        )

    if ldl and _is_high(ldl) and hdl and _is_low(hdl):
        insights.append(
            "🔴 Pattern: High LDL + Low HDL — unfavorable lipid profile that "
            "increases cardiovascular risk. Lifestyle changes and possible medication "
            "should be discussed with a doctor."
        )
    elif ldl and _is_high(ldl):
        insights.append(
            "⚠️ High LDL cholesterol — may increase long-term heart and stroke risk. "
            "Diet, exercise, and possibly medication can help manage this."
        )
    elif hdl and _is_low(hdl):
        insights.append(
            "⚠️ Low HDL ('good' cholesterol) — associated with higher cardiovascular risk. "
            "Regular exercise and dietary changes may help raise HDL."
        )

    if tg and _is_high(tg):
        insights.append(
            "⚠️ High triglycerides — associated with metabolic syndrome, diabetes risk, "
            "and cardiovascular disease. Reducing refined carbs and alcohol may help."
        )

def _get_organ_patterns(results: list[LabResult], insights: list[str]):
    crea  = _find(results, "creatinine")
    urea  = _find(results, "urea")
    alt   = _find(results, "alt")
    ast   = _find(results, "ast")
    bili  = _find(results, "bilirubin")
    alb   = _find(results, "albumin")
    tsh   = _find(results, "tsh")
    t4    = _find(results, "t4")
    k     = _find(results, "potassium")
    na    = _find(results, "sodium")
    ca    = _find(results, "calcium")
    vitd  = _find(results, "vitamin_d")
    b12   = _find(results, "vitamin_b12")
    plt   = _find(results, "platelets")

# Kidney
    if crea and urea and _is_high(crea) and _is_high(urea):
        insights.append(
            "🔴 Pattern: High Creatinine + High Urea — may indicate reduced kidney function "
            "(chronic kidney disease or acute kidney injury). "
            "Urgent nephrology evaluation is recommended."
        )
    elif crea and _is_high(crea):
        insights.append(
            "⚠️ High creatinine — kidneys may not be filtering waste efficiently. "
            "Causes include dehydration, kidney disease, or medication effects."
        )

# Liver
    if alt and ast and _is_high(alt) and _is_high(ast):
        if alt.value > 3 * 56 or ast.value > 3 * 40:
            insights.append(
                "🔴 Pattern: Markedly elevated ALT + AST (> 3× upper normal) — "
                "suggests significant liver injury. Urgent medical evaluation needed. "
                "Possible causes: hepatitis, alcohol, medications, or other liver disease."
            )
        else:
            insights.append(
                "⚠️ Pattern: Elevated ALT + AST — may suggest liver inflammation or stress. "
                "Causes include fatty liver, alcohol use, or viral hepatitis."
            )
    elif alt and _is_high(alt):
        insights.append(
            "⚠️ Elevated ALT — liver may be under stress. Common causes include "
            "fatty liver disease, alcohol, or medication effects."
        )

    if bili and _is_high(bili) and alb and _is_low(alb):
        insights.append(
            "🔴 Pattern: High Bilirubin + Low Albumin — may suggest impaired liver synthesis. "
            "This pattern can occur in chronic liver disease. Medical evaluation is important."
        )
    elif bili and _is_high(bili):
        insights.append(
            "⚠️ High bilirubin — may cause jaundice (yellowing of skin/eyes). "
            "Causes include liver disease, bile duct obstruction, or hemolysis."
        )

# Thyroid
    if tsh and _is_high(tsh) and t4 and _is_low(t4):
        insights.append(
            "🔴 Pattern: High TSH + Low Free T4 — classic hypothyroidism (underactive thyroid). "
            "Symptoms may include fatigue, weight gain, and cold sensitivity. "
            "Thyroid hormone replacement therapy is often required."
        )
    elif tsh and _is_low(tsh) and t4 and _is_high(t4):
        insights.append(
            "🔴 Pattern: Low TSH + High Free T4 — suggests hyperthyroidism (overactive thyroid). "
            "Symptoms may include weight loss, rapid heartbeat, and anxiety. "
            "Please consult an endocrinologist."
        )
    elif tsh and _is_high(tsh):
        insights.append(
            "⚠️ High TSH — thyroid may be underactive (hypothyroidism). "
            "A Free T4 test can help confirm. Symptoms: fatigue, cold intolerance, dry skin."
        )
    elif tsh and _is_low(tsh):
        insights.append(
            "⚠️ Low TSH — thyroid may be overactive (hyperthyroidism). "
            "A Free T3/T4 panel can help clarify. Symptoms: palpitations, heat intolerance."
        )

# Electrolytes & Vitamins
    if k and _is_high(k):
        insights.append(
            "🔴 High potassium (hyperkalemia) — can affect heart rhythm. "
            "Causes include kidney disease, certain medications, or dehydration. "
            "Urgent medical evaluation is recommended."
        )
    if k and _is_low(k):
        insights.append(
            "⚠️ Low potassium (hypokalemia) — can cause muscle weakness or heart rhythm issues. "
            "May be related to diuretic use, vomiting, or poor dietary intake."
        )
    if na and _is_low(na):
        insights.append(
            "⚠️ Low sodium (hyponatremia) — may cause confusion, nausea, or fatigue. "
            "Causes include excess water intake, kidney or adrenal issues."
        )
    if ca and _is_low(ca):
        insights.append(
            "⚠️ Low calcium (hypocalcemia) — may affect muscle and nerve function. "
            "Could relate to Vitamin D deficiency, parathyroid issues, or diet."
        )
    if vitd and _is_low(vitd):
        insights.append(
            "⚠️ Low Vitamin D — affects bone strength, immunity, and mood. "
            "Supplementation (after medical advice) and sun exposure can help."
        )
    if b12 and _is_low(b12):
        insights.append(
            "⚠️ Low Vitamin B12 — can cause fatigue, neurological symptoms, and macrocytic anemia. "
            "B12 supplementation or dietary changes are commonly recommended."
        )

# Platelets
    if plt and _is_low(plt):
        if plt.value_normalized is not None and plt.value_normalized < 50000:
            insights.append(
                "🔴 Critically low platelets (< 50,000/µL) — serious bleeding risk. "
                "Seek immediate medical evaluation."
            )
        else:
            insights.append(
                "⚠️ Low platelet count (thrombocytopenia) — may increase bleeding tendency. "
                "Causes include viral illness, immune reactions, or medication effects."
            )
    elif plt and _is_high(plt):
        insights.append(
            "⚠️ High platelet count (thrombocytosis) — may increase clotting risk. "
            "Can occur with iron deficiency, infection, or inflammatory states."
        )

def _get_cbc_individual_patterns(results: list[LabResult], insights: list[str]):
    """Single-test fallback patterns for CBC tests when combined patterns can't trigger."""
    rdw_sd  = _find(results, "rdw_sd")
    rdw     = _find(results, "rdw")
    pdw     = _find(results, "pdw")
    mpv     = _find(results, "mpv")
    hct     = _find(results, "hematocrit")
    hb      = _find(results, "hemoglobin")
    mcv     = _find(results, "mcv")
    mch     = _find(results, "mch")
    mchc    = _find(results, "mchc")
    plt     = _find(results, "platelets")
    wbc     = _find(results, "wbc")
    rbc     = _find(results, "rbc")

    if rdw_sd and _is_high(rdw_sd) and not hb:
        insights.append(
            "⚠️ High RDW-SD — red blood cells vary significantly in size (anisocytosis). "
            "This can occur in iron deficiency, B12/folate deficiency, or early-stage anemia. "
            "Iron studies and B12 levels may help identify the cause."
        )
    if pdw and _is_high(pdw):
        insights.append(
            "⚠️ High PDW — platelet size variation is increased. "
            "Often associated with higher platelet turnover, inflammation, or iron deficiency. "
            "May correlate with MPV findings."
        )
    if mpv and _is_high(mpv):
        insights.append(
            "⚠️ High MPV — platelets are larger than average, which may indicate "
            "increased platelet destruction or production. "
            "Common in immune thrombocytopenia or inflammatory conditions."
        )
    if mpv and _is_low(mpv):
        insights.append(
            "⚠️ Low MPV — platelets are smaller than average, which can be seen in "
            "bone marrow disorders or chronic inflammation."
        )
    if hct and _is_low(hct) and not hb:
        insights.append(
            "⚠️ Low hematocrit — the proportion of red blood cells in your blood is reduced. "
            "This often indicates anemia. Common causes include iron deficiency, "
            "blood loss, or chronic disease. A hemoglobin test can confirm."
        )
    if rbc and _is_low(rbc) and not hb:
        insights.append(
            "⚠️ Low RBC count — your body is producing fewer red blood cells than normal. "
            "This may be due to anemia, blood loss, or nutritional deficiencies."
        )
    if mcv and _is_low(mcv) and not hb:
        insights.append(
            "⚠️ Low MCV — red blood cells are smaller than normal (microcytosis). "
            "This is commonly seen in iron deficiency or thalassemia trait. "
            "Iron studies and hemoglobin electrophoresis may help."
        )
    if mcv and _is_high(mcv) and not hb:
        insights.append(
            "⚠️ High MCV — red blood cells are larger than normal (macrocytosis). "
            "Common causes include B12/folate deficiency, liver disease, or medications. "
            "B12 and folate levels are recommended."
        )
    if mch and _is_low(mch) and not hb:
        insights.append(
            "⚠️ Low MCH — red blood cells contain less hemoglobin than normal (hypochromia). "
            "Often seen with iron deficiency or thalassemia."
        )
    if mchc and _is_low(mchc) and not hb:
        insights.append(
            "⚠️ Low MCHC — reduced hemoglobin concentration in red blood cells. "
            "May indicate iron deficiency anemia or other hemoglobinopathies."
        )
    if wbc and _is_high(wbc) and not (_find(results, "neutrophils_pct") or _find(results, "lymphocytes_pct")):
        insights.append(
            "⚠️ High WBC count (leukocytosis) — may indicate infection, inflammation, "
            "or a stress response. A differential count can help identify the cause."
        )


def generate_insights(results: list[LabResult]) -> list[str]:
    insights: list[str] = []

    _get_anemia_patterns(results, insights)
    _get_infection_patterns(results, insights)
    _get_metabolic_patterns(results, insights)
    _get_organ_patterns(results, insights)
    _get_cbc_individual_patterns(results, insights)

    n_ab = _ab_count(results)
    if n_ab >= 5:
        insights.append(
            "⚠️ Multiple tests are outside reference ranges. "
            "A comprehensive clinical review with your doctor is strongly recommended."
        )
    elif n_ab >= 2 and not insights:
        insights.append(
            "⚠️ Some test results are outside the reference range. "
            "Discuss these findings with your doctor to understand what they mean for your health."
        )

    if not insights:
        insights.append(
            "✅ No specific pattern detected from these results. "
            "Always review individual results with your doctor."
        )

    logger.info("[insights] generated %d insights from %d results (%d abnormal)",
                len(insights), len(results), n_ab)
    return insights
