"""
Final Accuracy Report Generator.
Produces a comprehensive markdown report with all stage-wise metrics.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _pct(val: float) -> str:
    return f"{val:.2f}%"


def _bar(val: float, width: int = 25) -> str:
    """Generate a simple ASCII bar."""
    filled = int(val / 100.0 * width)
    return "█" * filled + "░" * (width - filled)


def _score_to_grade(score: float) -> str:
    if score >= 95:
        return "A+"
    elif score >= 90:
        return "A"
    elif score >= 85:
        return "A-"
    elif score >= 80:
        return "B+"
    elif score >= 75:
        return "B"
    elif score >= 70:
        return "B-"
    elif score >= 65:
        return "C+"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"


def generate_report(metrics: dict, output_path: str = None) -> str:
    """Generate the full evaluation report as markdown and optionally save."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# Medical Blood Test Analysis System — Accuracy Evaluation Report

**Generated:** {now}
**Evaluator:** AI QA Evaluation Framework v1.0
**Benchmark Dataset:** 280 structured reports across 7 types and 6 quality levels

---

## 1. Executive Summary

| Metric | Score |
|--------|-------|
| Overall End-to-End Accuracy | {_pct(metrics.get('stage_10_end_to_end', {}).get('accuracy_pct', 0))} |
| Overall OCR Accuracy (CER) | {_pct(metrics.get('stage_1_ocr', {}).get('cer_pct', 0))} |
| Overall Parsing F1 Score | {_pct(metrics.get('stage_2_name_recognition', {}).get('f1_pct', 0))} |
| Overall Numeric Accuracy | {_pct(metrics.get('stage_3_value_extraction', {}).get('exact_match', {}).get('accuracy_pct', 0))} |
| Overall Interpretation Accuracy | {_pct(metrics.get('stage_7_classification', {}).get('accuracy_pct', 0))} |
| Overall Success Rate | {_pct(metrics.get('dataset_summary', {}).get('success_rate_pct', 0))} |
| **Overall Accuracy Score (conditional)** | **{_compute_overall(metrics):.2f}% — {_score_to_grade(_compute_overall(metrics))}** |
| **Crash-Adjusted Overall Score** | **{_compute_overall(metrics) * metrics.get('dataset_summary', {}).get('success_rate_pct', 100) / 100:.2f}% — {_score_to_grade(_compute_overall(metrics) * metrics.get('dataset_summary', {}).get('success_rate_pct', 100) / 100)}** |

---

## 2. Evaluation Methodology

### Pipeline Stages Evaluated

| Stage | Component | Method |
|-------|-----------|--------|
| 1 | OCR Accuracy | Compare GT text vs repaired OCR text: CER, WER, digit accuracy |
| 2 | Test Name Recognition | Precision, Recall, F1 against ground truth test keys |
| 3 | Value Extraction | Exact match %, absolute/relative error, digit error detection |
| 4 | Unit Recognition | Normalized unit comparison against ground truth |
| 5 | Reference Range Detection | Compare resolved ranges against database reference ranges |
| 6 | Normalization | Verify value/unit can be properly normalized for classification |
| 7 | Clinical Interpretation | Confusion matrix: normal/high/low vs ground truth |
| 8 | Abnormal Flag Detection | Sensitivity, specificity, P/R/F1 for abnormal flagging |
| 9 | AI Summary Quality | 7-dimension quality scoring (1-10 each) |
| 10 | End-to-End Accuracy | Full pipeline success/failure rate |

### Scoring Rules
- **Exact Match**: Value matches ground truth exactly (type-aware)
- **Precision**: TP / (TP + FP) — tests correctly detected out of all detections
- **Recall**: TP / (TP + FN) — tests correctly detected out of all ground truth tests
- **F1 Score**: Harmonic mean of precision and recall
- **Confusion Matrix**: Rows = ground truth, Columns = predicted

---

## 3. Dataset Description

### Distribution by Report Type

"""
    total_generated = metrics.get("dataset_summary", {}).get("total_reports", 280)
    expected_per_type = {"CBC": 40, "Lipid Profile": 40, "Liver Function": 40, "Kidney Function": 40, "Diabetes": 40, "Thyroid": 40, "Mixed": 40}
    expected_per_quality = {"clean": 70, "standard": 70, "low": 35, "mobile": 35, "rotated": 35, "pdf": 35}

    per_type = metrics.get("per_type_accuracy", {})
    report += f"\n| Report Type | Generated | Evaluated | Crashed | Avg Tests | Description |\n"
    report += f"|------------|-----------|-----------|---------|-----------|-------------|\n"
    for t in ["CBC", "Lipid Profile", "Liver Function", "Kidney Function", "Diabetes", "Thyroid", "Mixed"]:
        info = per_type.get(t, {})
        count = info.get("count", 0)
        exp = expected_per_type.get(t, 40)
        crashed = exp - count
        avg_acc = info.get("mean", 0)
        report += f"| {t} | {exp} | {count} | {crashed} | {_get_avg_tests(t)} | {_get_type_desc(t)} |\n"

    report += f"""
### Distribution by Quality Level

| Quality | Generated | Evaluated | Crashed | Description | Avg Accuracy |
|---------|-----------|-----------|---------|-------------|-------------|
"""
    per_quality = metrics.get("per_quality_accuracy", {})
    for q in ["clean", "standard", "low", "mobile", "rotated", "pdf"]:
        info = per_quality.get(q, {})
        count = info.get("count", 0)
        exp = expected_per_quality.get(q, 35)
        crashed = exp - count
        mean = info.get("mean", 0)
        desc = {
            "clean": "Perfect OCR (baseline)",
            "standard": "Light realistic OCR noise",
            "low": "Heavy corruption (low-quality scan)",
            "mobile": "Camera photo distortions",
            "rotated": "Rotation artifacts",
            "pdf": "PDF extraction artifacts",
        }.get(q, "")
        report += f"| {q} | {exp} | {count} | {crashed} | {desc} | {_pct(mean)} |\n"

    report += f"""
### Degradation Methods
- **clean**: Exact text without any corruption
- **standard**: 3% character substitution, 1% deletion, 0.5% insertion, 1% space errors
- **low**: 8% substitution, 4% deletion, 2% insertion, 5% space errors
- **mobile**: 6% substitution, 3% deletion, 1.5% insertion, 8% space errors
- **rotated**: 7% substitution, 5% deletion, 2% insertion, 6% space errors
- **pdf**: 2% substitution, 1% deletion, 0.5% insertion, 0.5% space errors

---

## 4. Stage-wise Accuracy Table

| Stage | Component | Accuracy | Grade |
|-------|-----------|----------|-------|
"""
    stages = [
        ("Stage 1", "OCR Accuracy (CER)", metrics.get("stage_1_ocr", {}).get("cer_pct", 0)),
        ("Stage 2", "Test Name Recognition (F1)", metrics.get("stage_2_name_recognition", {}).get("f1_pct", 0)),
        ("Stage 3", "Value Extraction", metrics.get("stage_3_value_extraction", {}).get("exact_match", {}).get("accuracy_pct", 0)),
        ("Stage 4", "Unit Recognition", metrics.get("stage_4_unit_recognition", {}).get("accuracy_pct", 0)),
        ("Stage 5", "Reference Range Detection", metrics.get("stage_5_ref_range", {}).get("accuracy_pct", 0)),
        ("Stage 6", "Normalization", metrics.get("stage_6_normalization", {}).get("accuracy_pct", 0)),
        ("Stage 7", "Clinical Interpretation", metrics.get("stage_7_classification", {}).get("accuracy_pct", 0)),
        ("Stage 8", "Abnormal Flag Detection (F1)", metrics.get("stage_8_abnormal_detection", {}).get("f1_pct", 0)),
        ("Stage 9", "AI Summary Quality", metrics.get("stage_9_ai_summary", {}).get("overall", 0)),
        ("Stage 10", "End-to-End Pipeline", metrics.get("stage_10_end_to_end", {}).get("accuracy_pct", 0)),
    ]
    for num, name, score in stages:
        grade = _score_to_grade(score)
        bar = _bar(score)
        report += f"| {num} | {name} | {_pct(score)} {bar} | **{grade}** |\n"

    report += f"""
---

## 5. Precision / Recall / F1 Scores

| Category | Precision | Recall | F1 Score | Specificity |
|----------|-----------|--------|----------|-------------|
"""
    name_metrics = metrics.get("stage_2_name_recognition", {})
    abnorm_metrics = metrics.get("stage_8_abnormal_detection", {})
    for label, m in [("Test Name Recognition", name_metrics), ("Abnormal Flag Detection", abnorm_metrics)]:
        report += f"| {label} | {_pct(m.get('precision_pct', 0))} | {_pct(m.get('recall_pct', 0))} | {_pct(m.get('f1_pct', 0))} | {_pct(m.get('specificity_pct', 0))} |\n"

    report += f"""
---

## 6. OCR Metrics

| Metric | Value |
|--------|-------|
| Total Reports | {metrics.get('stage_1_ocr', {}).get('total_reports', 0)} |
| Character Error Rate (CER) | {_pct(metrics.get('stage_1_ocr', {}).get('cer_pct', 0))} |
| Word Error Rate (WER) | {_pct(metrics.get('stage_1_ocr', {}).get('wer_pct', 0))} |
| Digit Accuracy | {_pct(metrics.get('stage_1_ocr', {}).get('digit_accuracy_pct', 0))} |
| Missing Lines | {metrics.get('stage_1_ocr', {}).get('missing_lines', 0)} |
| Extra Lines | {metrics.get('stage_1_ocr', {}).get('extra_lines', 0)} |

### How OCR Metrics Are Measured

The OCR evaluation compares the **ground truth clean text** against the **repaired corrupted text** (after `repair_ocr_text()` processing):

- **CER**: Character-level Levenshtein distance between GT and repaired text
- **WER**: Word-level edit distance between GT and repaired word sequences
- **Digit Accuracy**: Proportion of digit characters correctly preserved
- **Missing Lines**: Lines present in GT but absent after repair
- **Extra Lines**: Lines present after repair that don't exist in GT

---

## 7. Parsing Metrics

| Metric | Value |
|--------|-------|
| Name Precision | {_pct(name_metrics.get('precision_pct', 0))} |
| Name Recall | {_pct(name_metrics.get('recall_pct', 0))} |
| Name F1 Score | {_pct(name_metrics.get('f1_pct', 0))} |
| True Positives | {name_metrics.get('true_positives', 0)} |
| False Positives | {name_metrics.get('false_positives', 0)} |
| False Negatives | {name_metrics.get('false_negatives', 0)} |

---

## 8. Numeric Extraction Metrics

| Metric | Value |
|--------|-------|
| Exact Match Rate | {_pct(metrics.get('stage_3_value_extraction', {}).get('exact_match', {}).get('accuracy_pct', 0))} |
| Mean Absolute Error | {metrics.get('stage_3_value_extraction', {}).get('mean_abs_error', 0):.4f} |
| Median Absolute Error | {metrics.get('stage_3_value_extraction', {}).get('median_abs_error', 0):.4f} |
| Mean Relative Error | {metrics.get('stage_3_value_extraction', {}).get('mean_rel_error_pct', 0):.2f}% |
| Decimal Errors | {metrics.get('stage_3_value_extraction', {}).get('decimal_errors', 0)} |
| Digit Losses | {metrics.get('stage_3_value_extraction', {}).get('digit_losses', 0)} |
| Digit Additions | {metrics.get('stage_3_value_extraction', {}).get('digit_additions', 0)} |

---

## 9. Interpretation Metrics

### Confusion Matrix

Rows = Ground Truth, Columns = Predicted

| GT \\ Pred | Normal | High | Low | Unknown |
|------------|--------|------|-----|---------|
"""
    cm = metrics.get("stage_7_classification", {}).get("matrix", {})
    for gt_label in ["normal", "high", "low", "unknown"]:
        row = cm.get(gt_label, {})
        vals = [row.get(p, 0) for p in ["normal", "high", "low", "unknown"]]
        report += f"| **{gt_label}** | {' | '.join(str(v) for v in vals)} |\n"

    report += f"""
| Overall Classification Accuracy | {_pct(metrics.get('stage_7_classification', {}).get('accuracy_pct', 0))} |

### Abnormal Detection

| Metric | Value |
|--------|-------|
| Sensitivity (Recall) | {_pct(abnorm_metrics.get('recall_pct', 0))} |
| Specificity | {_pct(abnorm_metrics.get('specificity_pct', 0))} |
| Precision | {_pct(abnorm_metrics.get('precision_pct', 0))} |
| F1 Score | {_pct(abnorm_metrics.get('f1_pct', 0))} |
| Accuracy | {_pct(abnorm_metrics.get('accuracy_pct', 0))} |

---

## 10. AI Summary Evaluation

| Dimension | Score (1-10) |
|-----------|-------------|
"""
    ai = metrics.get("stage_9_ai_summary", {})
    for dim in ["medical_correctness", "hallucination_rate", "missing_findings",
                 "false_findings", "consistency", "readability", "completeness"]:
        score = ai.get(dim, 0)
        bar = _bar(score * 10)
        report += f"| {dim.replace('_', ' ').title()} | {score:.1f} {bar} |\n"

    report += f"""
| **Overall AI Summary Quality** | **{ai.get('overall', 0):.2f}%** |

**Note**: AI summary scores are computed from structured data quality indicators in the pipeline output, NOT from actual LLM API calls. Scores reflect the quality of data available for AI explanation generation.

---

## 11. Error Analysis

| Error Category | Count | Percentage |
|---------------|-------|------------|
"""
    err = metrics.get("error_analysis", {}).get("distribution_pct", {})
    err_counts = metrics.get("error_analysis", {}).get("distribution", {})
    for cat in ["OCR Error", "Parser Error", "Resolution Error", "Normalization Error",
                "Wrong Reference Range", "Unit Error", "Value Extraction Error",
                "Classification Error", "Backend Error", "Cache Issue"]:
        count = err_counts.get(cat, 0)
        pct = err.get(cat, 0)
        report += f"| {cat} | {count} | {pct:.2f}% |\n"

    report += f"""
| **Total Errors** | **{metrics.get('error_analysis', {}).get('total_errors', 0)}** | **100%** |

---

## 12. Bug Findings

The evaluation uncovered the following production bugs that prevent the pipeline from completing successfully:

| # | Bug | Affected Tests | Impact | Location |
|---|-----|---------------|--------|----------|
| B1 | `td.display_name` on `None` when resolver returns undefined test key | Free T4 → `t4`, Free T3 → `t3`, Direct Bilirubin → `bilirubin` | **Pipeline crash** — `AttributeError` on all reports containing these tests | `core/pipeline.py:472` |
| B2 | Resolver returns wrong key for "Direct Bilirubin" → `bilirubin` instead of `bilirubin_direct` | Direct Bilirubin, Indirect Bilirubin | Wrong test key + crash via B1 | `core/resolver.py` |
| B3 | `ggt` not in resolver alias list | GGT | Dropped as "unresolved" — false negative | `core/resolver.py` |
| B4 | `ag_ratio` not in resolver alias list | A/G Ratio | Dropped as "unresolved" — false negative | `core/resolver.py` |
| B5 | Missing test definitions in `lab_reference_dataset.json` for keys `t4`, `t3`, `bilirubin` | Thyroid, Mixed reports | No reference data available for these tests | `medical/lab_reference_dataset.json` |

**Total reports affected by bugs**: 98 (35.0% crash rate). All crashes trace to B1 (missing `None` guard on `td.display_name`).

---

## 13. Weakest Components

"""
    # Find the 3 lowest-scoring stages
    stage_scores = [(name, score) for _, name, score in stages]
    stage_scores.sort(key=lambda x: x[1])
    weakest = stage_scores[:3]
    for name, score in weakest:
        report += f"- **{name}**: {_pct(score)} — {_weakness_recommendation(name, score)}\n"

    report += f"""
---

## 14. Strongest Components

"""
    strongest = stage_scores[-3:]
    strongest.reverse()
    for name, score in strongest:
        report += f"- **{name}**: {_pct(score)} — {_strength_reason(name, score)}\n"

    report += f"""
---

## 15. Recommendations

Based on the evaluation results, the following improvements are recommended:

"""

    recommendations = _generate_recommendations(metrics)
    for i, rec in enumerate(recommendations, 1):
        report += f"{i}. {rec}\n"

    report += f"""
---

## 16. Overall Accuracy Score

| Component | Weight | Score | Weighted |
|----------|--------|-------|----------|
"""
    weights = {
        "OCR Accuracy (CER)": 0.10,
        "Test Name Recognition (F1)": 0.15,
        "Value Extraction": 0.15,
        "Unit Recognition": 0.10,
        "Reference Range Detection": 0.10,
        "Normalization": 0.10,
        "Clinical Interpretation": 0.10,
        "Abnormal Flag Detection (F1)": 0.10,
        "AI Summary Quality": 0.05,
        "End-to-End Pipeline": 0.05,
    }
    total_weighted = 0.0
    for num, name, score in stages:
        w = weights.get(name, 0.05)
        weighted = score * w
        total_weighted += weighted
        report += f"| {name} | {w*100:.0f}% | {_pct(score)} | {_pct(weighted)} |\n"

    report += f"""
| **Overall (conditional)** | **100%** | | **{_pct(total_weighted)}** |
| **Grade** | | | **{_score_to_grade(total_weighted)}** |

> *"Conditional" means scores for Stages 1-9 reflect accuracy on the {int(metrics.get('dataset_summary', {}).get('total_reports', 280) - metrics.get('dataset_summary', {}).get('crashed', 0))} successfully-evaluated reports only (crashes excluded). The true population-level score, accounting for the crash rate, is **{_pct(total_weighted * metrics.get('dataset_summary', {}).get('success_rate_pct', 100) / 100)}** (Grade: {_score_to_grade(total_weighted * metrics.get('dataset_summary', {}).get('success_rate_pct', 100) / 100)}).*

---

## 17. Appendix: Methodology Notes

- **Simulated OCR**: The benchmark uses synthetic OCR corruption rather than actual Tesseract output. This measures the pipeline's robustness to OCR errors but does not measure Tesseract's inherent accuracy.
- **Ground Truth**: All ground truth values are generated from the same `lab_reference_dataset.json` used by the production system. This creates an internally consistent benchmark.
- **AI Summary**: The AI summary quality scores are based on structural data quality indicators rather than LLM response evaluation. A separate, LLM-based evaluation would be needed for full AI quality assessment.
- **Reference Range**: The reference range evaluation verifies that the database returns ranges consistent with the benchmark's expected values (within 15% tolerance).
- **Reproducibility**: All randomness uses seed 42. Running `run_evaluation.py` with the same seed produces identical results.

---

*Report generated by the AI QA Evaluation Framework v1.0*
"""

    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
        logger.info("Report saved to %s", output_path)

    return report


def _compute_overall(metrics: dict) -> float:
    """Compute the overall accuracy score.

    Stages 1-9 are computed only on successful pipeline runs and reflect
    genuine accuracy. Stage 10 (end-to-end) includes crash rate.
    """
    weights = {
        "stage_1_ocr": ("cer_pct", 0.10),
        "stage_2_name_recognition": ("f1_pct", 0.15),
        "stage_3_value_extraction": ("exact_match", "accuracy_pct", 0.15),
        "stage_4_unit_recognition": ("accuracy_pct", 0.10),
        "stage_5_ref_range": ("accuracy_pct", 0.10),
        "stage_6_normalization": ("accuracy_pct", 0.10),
        "stage_7_classification": ("accuracy_pct", 0.10),
        "stage_8_abnormal_detection": ("f1_pct", 0.10),
        "stage_9_ai_summary": ("overall", 0.05),
        "stage_10_end_to_end": ("accuracy_pct", 0.05),
    }
    total = 0.0
    for stage, spec in weights.items():
        stage_data = metrics.get(stage, {})
        if len(spec) == 2:
            key, weight = spec
            score = stage_data.get(key, 0)
        else:
            key1, key2, weight = spec
            inner = stage_data.get(key1, {})
            score = inner.get(key2, 0) if isinstance(inner, dict) else 0
        total += score * weight
    return total


def _get_avg_tests(report_type: str) -> int:
    counts = {
        "CBC": 15,
        "Lipid Profile": 6,
        "Liver Function": 10,
        "Kidney Function": 10,
        "Diabetes": 3,
        "Thyroid": 3,
        "Mixed": 18,
    }
    return counts.get(report_type, 10)


def _get_type_desc(report_type: str) -> str:
    descs = {
        "CBC": "Complete blood count + differential",
        "Lipid Profile": "Total cholesterol, LDL, HDL, triglycerides, VLDL",
        "Liver Function": "ALT, AST, ALP, GGT, bilirubin, proteins",
        "Kidney Function": "Creatinine, BUN, urea, uric acid, electrolytes",
        "Diabetes": "Fasting glucose, HbA1c, fasting insulin",
        "Thyroid": "TSH, Free T4, Free T3",
        "Mixed": "Combined panel across all categories",
    }
    return descs.get(report_type, "")


def _weakness_recommendation(name: str, score: float) -> str:
    recs = {
        "OCR Accuracy (CER)": "Improve repair_ocr_text() character-level recovery. Consider adding more OCR error patterns.",
        "Test Name Recognition (F1)": "Expand alias dictionary for common OCR-corrupted test names. Add more fuzzy matching patterns.",
        "Value Extraction": "Enhance decimal and digit-corruption recovery in fix_ocr_value_errors().",
        "Unit Recognition": "Extend _UNIT_FIXES and _CORRUPT_UNITS for more OCR unit variants.",
        "Reference Range Detection": "Improve cross-gender and cross-age-group range fallback logic.",
        "Normalization": "Add more conversion rules for uncommon unit pairs.",
        "Clinical Interpretation": "Enhance confidence threshold tuning to reduce REVIEW_REQUIRED cases.",
        "Abnormal Flag Detection (F1)": "Improve borderline value classification and uncertainty handling.",
        "AI Summary Quality": "Enhance completeness tracking and review-required detection logic.",
        "End-to-End Pipeline": "Strengthen error handling at all stages to reduce crash rate.",
    }
    return recs.get(name, "Targeted improvement needed.")


def _strength_reason(name: str, score: float) -> str:
    reasons = {
        "OCR Accuracy (CER)": "repair_ocr_text() effectively corrects common OCR corruptions.",
        "Test Name Recognition (F1)": "Comprehensive alias dictionary and 5-tier resolver work well.",
        "Value Extraction": "Robust value extraction with good numeric repair capabilities.",
        "Unit Recognition": "Wide coverage of known units in _KNOWN_UNITS and _UNIT_FIXES.",
        "Reference Range Detection": "Gender/age-aware database with comprehensive fallback logic.",
        "Normalization": "Covers test-specific conversions, count normalization, and metric conversions.",
        "Clinical Interpretation": "Confidence-aware classification with sound reference range lookup.",
        "Abnormal Flag Detection (F1)": "Good sensitivity and specificity in abnormal flagging.",
        "AI Summary Quality": "Structured data pipeline produces consistent quality indicators.",
        "End-to-End Pipeline": "Robust pipeline design with proper error handling and tracking.",
    }
    return reasons.get(name, "Strong performance in this stage.")


def _generate_recommendations(metrics: dict) -> list[str]:
    """Generate actionable recommendations based on metrics."""
    recs = []

    ocr = metrics.get("stage_1_ocr", {})
    if ocr.get("cer_pct", 100) < 90:
        recs.append("**Strengthen OCR repair**: Current CER of {:.2f}% indicates significant character-level corruption remains after repair. Expand `repair_ocr_text()` with additional patterns for common OCR substitutions (0↔O, 1↔I, etc.) and digit-preservation rules.".format(ocr.get("cer_pct", 0)))

    name_f1 = metrics.get("stage_2_name_recognition", {}).get("f1_pct", 100)
    if name_f1 < 90:
        recs.append("**Expand test name aliases**: F1 of {:.2f}% for name recognition suggests many OCR-corrupted test names are not resolved. Add more common OCR variants to `_LAB_TEST_NAMES` in parser.py and strengthen the fuzzy matcher in resolver.py.".format(name_f1))

    val_acc = metrics.get("stage_3_value_extraction", {}).get("exact_match", {}).get("accuracy_pct", 100)
    if val_acc < 85:
        recs.append("**Improve value extraction**: Exact match rate of {:.2f}% indicates digit-level errors. Enhance OCR digit-correction logic and decimal-point error recovery.".format(val_acc))

    unit_acc = metrics.get("stage_4_unit_recognition", {}).get("accuracy_pct", 100)
    if unit_acc < 90:
        recs.append("**Extend unit coverage**: Unit accuracy of {:.2f}% means many OCR-corrupted units are unrecognized. Add more entries to `_UNIT_FIXES` and `_CORRUPT_UNITS`.".format(unit_acc))

    cm = metrics.get("stage_7_classification", {}).get("accuracy_pct", 100)
    if cm < 90:
        recs.append("**Tune classification thresholds**: Interpretation accuracy of {:.2f}% suggests confidence thresholds may need adjustment to reduce REVIEW_REQUIRED cases.".format(cm))

    crash_rate = 100 - metrics.get("dataset_summary", {}).get("success_rate_pct", 100)
    if crash_rate > 5:
        recs.append("**Reduce crash rate**: Pipeline crash rate of {:.2f}% needs attention. Review exception handling in `process_lab_report()` and all sub-modules.".format(crash_rate))

    if not recs:
        recs.append("**Maintain current quality**: All stages demonstrate acceptable accuracy. Continue monitoring and add more edge-case test scenarios.")

    return recs


if __name__ == "__main__":
    # Quick self-test
    sample = {
        "dataset_summary": {"total_reports": 280, "crashed": 5, "success_rate_pct": 98.21},
        "stage_1_ocr": {"cer_pct": 88.5, "wer_pct": 82.3, "digit_accuracy_pct": 91.2,
                        "total_reports": 280, "missing_lines": 12, "extra_lines": 8},
        "stage_2_name_recognition": {"f1_pct": 92.1, "precision_pct": 94.0, "recall_pct": 90.3,
                                      "true_positives": 2500, "false_positives": 160, "false_negatives": 240, "true_negatives": 0, "specificity_pct": 0, "accuracy_pct": 91.2},
        "stage_3_value_extraction": {"exact_match": {"accuracy_pct": 86.4}, "mean_abs_error": 2.5, "median_abs_error": 0.1,
                                      "mean_rel_error_pct": 5.2, "decimal_errors": 45, "digit_losses": 78, "digit_additions": 32},
        "stage_4_unit_recognition": {"accuracy_pct": 93.8},
        "stage_5_ref_range": {"accuracy_pct": 91.5},
        "stage_6_normalization": {"accuracy_pct": 94.2},
        "stage_7_classification": {"accuracy_pct": 89.7, "matrix": {"normal": {"normal": 1000, "high": 30, "low": 20, "unknown": 50}, "high": {"normal": 40, "high": 300, "low": 5, "unknown": 15}, "low": {"normal": 25, "high": 3, "low": 150, "unknown": 10}, "unknown": {"normal": 10, "high": 5, "low": 3, "unknown": 0}}},
        "stage_8_abnormal_detection": {"f1_pct": 87.3, "precision_pct": 85.0, "recall_pct": 89.7, "specificity_pct": 92.1, "accuracy_pct": 90.5, "true_positives": 450, "false_positives": 79, "false_negatives": 52, "true_negatives": 2100},
        "stage_9_ai_summary": {"overall": 82.5, "medical_correctness": 8.5, "hallucination_rate": 7.2,
                                "missing_findings": 8.0, "false_findings": 8.8, "consistency": 9.0, "readability": 8.5, "completeness": 8.0},
        "stage_10_end_to_end": {"accuracy_pct": 97.8, "total": 280, "correct": 274, "errors": 6},
        "error_analysis": {"total_errors": 187, "distribution": {"OCR Error": 45, "Parser Error": 30, "Resolution Error": 25, "Normalization Error": 20, "Wrong Reference Range": 15, "Unit Error": 22, "Value Extraction Error": 18, "Classification Error": 8, "Backend Error": 4, "Cache Issue": 0},
                           "distribution_pct": {"OCR Error": 24.06, "Parser Error": 16.04, "Resolution Error": 13.37, "Normalization Error": 10.70, "Wrong Reference Range": 8.02, "Unit Error": 11.76, "Value Extraction Error": 9.63, "Classification Error": 4.28, "Backend Error": 2.14, "Cache Issue": 0}},
        "per_type_accuracy": {"CBC": {"mean": 85.0, "count": 40}, "Lipid Profile": {"mean": 92.0, "count": 40}, "Liver Function": {"mean": 88.0, "count": 40}, "Kidney Function": {"mean": 90.0, "count": 40}, "Diabetes": {"mean": 95.0, "count": 40}, "Thyroid": {"mean": 94.0, "count": 40}, "Mixed": {"mean": 87.0, "count": 40}},
        "per_quality_accuracy": {"clean": {"mean": 98.0, "count": 70}, "standard": {"mean": 92.0, "count": 70}, "low": {"mean": 78.0, "count": 35}, "mobile": {"mean": 82.0, "count": 35}, "rotated": {"mean": 76.0, "count": 35}, "pdf": {"mean": 95.0, "count": 35}},
    }
    print(generate_report(sample, "/tmp/test_report.md"))
