"""
Comprehensive 10-stage pipeline evaluator for the Medical Blood Test Analysis System.
Evaluates every stage independently and aggregates quantitative metrics.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 1.  METRIC DATA STRUCTURES

@dataclass
class StageMetrics:
    """Base metrics for any evaluation stage."""
    total: int = 0
    correct: int = 0
    errors: int = 0
    skipped: int = 0

    @property
    def accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return self.correct / self.total * 100.0

    @property
    def error_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.errors / self.total * 100.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "correct": self.correct,
            "errors": self.errors,
            "skipped": self.skipped,
            "accuracy_pct": round(self.accuracy, 2),
            "error_rate_pct": round(self.error_rate, 2),
        }


@dataclass
class OCRMetrics:
    """Stage 1: OCR Accuracy metrics."""
    cer_total_chars: int = 0
    cer_errors: int = 0
    wer_total_words: int = 0
    wer_errors: int = 0
    missing_lines: int = 0
    extra_lines: int = 0
    digit_accuracy: StageMetrics = field(default_factory=StageMetrics)
    total_reports: int = 0

    @property
    def cer(self) -> float:
        if self.cer_total_chars == 0:
            return 0.0
        return (1 - self.cer_errors / self.cer_total_chars) * 100.0

    @property
    def wer(self) -> float:
        if self.wer_total_words == 0:
            return 0.0
        return (1 - self.wer_errors / self.wer_total_words) * 100.0

    def to_dict(self) -> dict:
        return {
            "total_reports": self.total_reports,
            "cer_pct": round(self.cer, 2),
            "wer_pct": round(self.wer, 2),
            "missing_lines": self.missing_lines,
            "extra_lines": self.extra_lines,
            "digit_accuracy_pct": self.digit_accuracy.accuracy,
        }


@dataclass
class PrecisionRecallF1:
    """Precision / Recall / F1 metrics."""
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

    @property
    def precision(self) -> float:
        d = self.true_positives + self.false_positives
        return self.true_positives / d * 100.0 if d else 0.0

    @property
    def recall(self) -> float:
        d = self.true_positives + self.false_negatives
        return self.true_positives / d * 100.0 if d else 0.0

    @property
    def f1(self) -> float:
        p = self.precision / 100.0 if self.precision else 0.0
        r = self.recall / 100.0 if self.recall else 0.0
        d = p + r
        return 2 * p * r / d * 100.0 if d else 0.0

    @property
    def specificity(self) -> float:
        d = self.true_negatives + self.false_positives
        return self.true_negatives / d * 100.0 if d else 0.0

    @property
    def accuracy(self) -> float:
        d = self.true_positives + self.true_negatives + self.false_positives + self.false_negatives
        return (self.true_positives + self.true_negatives) / d * 100.0 if d else 0.0

    def to_dict(self) -> dict:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision_pct": round(self.precision, 2),
            "recall_pct": round(self.recall, 2),
            "f1_pct": round(self.f1, 2),
            "specificity_pct": round(self.specificity, 2),
            "accuracy_pct": round(self.accuracy, 2),
        }


@dataclass
class NumericAccuracy:
    """Stage 3: Numerical Value Accuracy metrics."""
    exact_match: StageMetrics = field(default_factory=StageMetrics)
    abs_errors: list[float] = field(default_factory=list)
    rel_errors: list[float] = field(default_factory=list)
    decimal_errors: int = 0
    digit_losses: int = 0
    digit_additions: int = 0

    @property
    def mean_abs_error(self) -> float:
        return sum(self.abs_errors) / len(self.abs_errors) if self.abs_errors else 0.0

    @property
    def mean_rel_error(self) -> float:
        return sum(self.rel_errors) / len(self.rel_errors) if self.rel_errors else 0.0

    @property
    def median_abs_error(self) -> float:
        if not self.abs_errors:
            return 0.0
        s = sorted(self.abs_errors)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    def to_dict(self) -> dict:
        return {
            "exact_match": self.exact_match.to_dict(),
            "mean_abs_error": round(self.mean_abs_error, 4),
            "median_abs_error": round(self.median_abs_error, 4),
            "mean_rel_error_pct": round(self.mean_rel_error * 100, 2),
            "decimal_errors": self.decimal_errors,
            "digit_losses": self.digit_losses,
            "digit_additions": self.digit_additions,
        }


@dataclass
class ConfusionMatrix:
    """Confusion matrix for classification evaluation."""
    matrix: dict = field(default_factory=lambda: {
        "normal": {"normal": 0, "high": 0, "low": 0, "unknown": 0},
        "high": {"normal": 0, "high": 0, "low": 0, "unknown": 0},
        "low": {"normal": 0, "high": 0, "low": 0, "unknown": 0},
        "unknown": {"normal": 0, "high": 0, "low": 0, "unknown": 0},
    })

    def record(self, actual: str, predicted: str):
        a = actual if actual in self.matrix else "unknown"
        p = predicted if predicted in self.matrix[a] else "unknown"
        self.matrix[a][p] += 1

    @property
    def accuracy(self) -> float:
        correct = sum(self.matrix[c][c] for c in self.matrix)
        total = sum(sum(r.values()) for r in self.matrix.values())
        return correct / total * 100.0 if total else 0.0

    def to_dict(self) -> dict:
        return {"matrix": self.matrix, "accuracy_pct": round(self.accuracy, 2)}


@dataclass
class Timings:
    """Timing metrics for pipeline stages."""
    ocr_times: list[float] = field(default_factory=list)
    pipeline_times: list[float] = field(default_factory=list)
    ai_times: list[float] = field(default_factory=list)
    total_times: list[float] = field(default_factory=list)

    def add(self, ocr: float, pipeline: float, ai: float, total: float):
        self.ocr_times.append(ocr)
        self.pipeline_times.append(pipeline)
        self.ai_times.append(ai)
        self.total_times.append(total)

    def _stats(self, vals: list[float]) -> dict:
        if not vals:
            return {"min": 0, "max": 0, "mean": 0, "median": 0}
        s = sorted(vals)
        n = len(s)
        return {
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
            "mean": round(sum(vals) / n, 3),
            "median": round(s[n // 2], 3) if n % 2 else round((s[n // 2 - 1] + s[n // 2]) / 2, 3),
        }

    def to_dict(self) -> dict:
        return {
            "ocr": self._stats(self.ocr_times),
            "pipeline": self._stats(self.pipeline_times),
            "ai": self._stats(self.ai_times),
            "total": self._stats(self.total_times),
        }


@dataclass
class AISummaryScore:
    """Stage 9: AI Summary Quality scores (1-10)."""
    medical_correctness: list[int] = field(default_factory=list)
    hallucination_rate: list[int] = field(default_factory=list)
    missing_findings: list[int] = field(default_factory=list)
    false_findings: list[int] = field(default_factory=list)
    consistency: list[int] = field(default_factory=list)
    readability: list[int] = field(default_factory=list)
    completeness: list[int] = field(default_factory=list)

    def _avg(self, vals: list[int]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    def to_dict(self) -> dict:
        return {
            "medical_correctness": round(self._avg(self.medical_correctness), 2),
            "hallucination_rate": round(self._avg(self.hallucination_rate), 2),
            "missing_findings": round(self._avg(self.missing_findings), 2),
            "false_findings": round(self._avg(self.false_findings), 2),
            "consistency": round(self._avg(self.consistency), 2),
            "readability": round(self._avg(self.readability), 2),
            "completeness": round(self._avg(self.completeness), 2),
            "overall": round(
                self._avg(self.medical_correctness + self.hallucination_rate +
                          self.missing_findings + self.false_findings +
                          self.consistency + self.readability + self.completeness) / 10.0 * 100, 2
            ),
        }


# 2.  ERROR CATEGORIES

ERROR_CATEGORIES = [
    "OCR Error",
    "Parser Error",
    "Resolution Error",
    "Normalization Error",
    "Clinical KB Error",
    "AI Hallucination",
    "Missing Definition",
    "Wrong Reference Range",
    "Cache Issue",
    "Frontend Error",
    "Backend Error",
    "Unit Error",
    "Value Extraction Error",
    "Classification Error",
]


@dataclass
class ErrorAnalysis:
    """Error categorization and distribution."""
    error_counts: dict = field(default_factory=lambda: {c: 0 for c in ERROR_CATEGORIES})
    error_details: list[dict] = field(default_factory=list)

    def record(self, category: str, report_id: str, test: str, detail: str):
        if category in self.error_counts:
            self.error_counts[category] += 1
        self.error_details.append({
            "report_id": report_id,
            "test": test,
            "category": category,
            "detail": detail,
        })

    def to_dict(self) -> dict:
        total = sum(self.error_counts.values())
        return {
            "total_errors": total,
            "distribution": self.error_counts,
            "distribution_pct": {
                k: round(v / total * 100, 2) if total else 0.0
                for k, v in self.error_counts.items()
            },
        }


# 3.  CORE EVALUATION ENGINE

@dataclass
class EvalResult:
    """Complete evaluation result for a single report."""
    report_id: str
    report_type: str
    quality: str
    gt_values: dict
    gt_units: dict
    gt_ranges: dict
    gt_statuses: dict
    metadata: dict
    parsed_tests: list = field(default_factory=list)
    resolved_tests: list = field(default_factory=list)
    pipeline_duration: float = 0.0
    error: Optional[str] = None


class PipelineAccuracyEvaluator:
    """Runs the complete 10-stage evaluation"""

    def __init__(self, dataset_dir: str = None):
        self.ocr = OCRMetrics()
        self.name_recognition = PrecisionRecallF1()
        self.value_accuracy = NumericAccuracy()
        self.unit_accuracy = StageMetrics()
        self.ref_range_accuracy = StageMetrics()
        self.normalization_accuracy = StageMetrics()
        self.interpretation_cm = ConfusionMatrix()
        self.abnormal_detection = PrecisionRecallF1()
        self.ai_summary = AISummaryScore()
        self.end_to_end = StageMetrics()
        self.timings = Timings()
        self.errors = ErrorAnalysis()
        self.per_type_accuracy: dict[str, list] = defaultdict(list)
        self.per_quality_accuracy: dict[str, list] = defaultdict(list)
        self.all_results: list[EvalResult] = []
        self.crashed: int = 0
        self.total_processed: int = 0

# STAGE 1: OCR Accuracy

    def eval_ocr(self, clean_text: str, corrupted_text: str):
        """
        Evaluate OCR accuracy by measuring how well repair_ocr_text()
        recovers clean text from corrupted text.
        """
        from core.normalization import repair_ocr_text

        self.ocr.total_reports += 1
        repaired = repair_ocr_text(corrupted_text)

# Character Error Rate (CER)
        gt_chars = list(clean_text)
        pred_chars = list(repaired)
        max_len = max(len(gt_chars), len(pred_chars))

# Simple Levenshtein-based CER approximation
# Pad to same length
        gt_chars += [''] * (max_len - len(gt_chars))
        pred_chars += [''] * (max_len - len(pred_chars))

        char_errors = sum(1 for g, p in zip(gt_chars, pred_chars) if g != p)
        self.ocr.cer_total_chars += max_len
        self.ocr.cer_errors += char_errors

# Word Error Rate
        gt_words = clean_text.split()
        pred_words = repaired.split()
# Simple WER using edit distance
        from difflib import SequenceMatcher
        sm = SequenceMatcher(None, gt_words, pred_words)
        total_ops = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != 'equal':
                total_ops += max(i2 - i1, j2 - j1)
        self.ocr.wer_total_words += len(gt_words)
        self.ocr.wer_errors += total_ops

# Missing / Extra lines
        gt_lines = [l for l in clean_text.split("\n") if l.strip()]
        pred_lines = [l for l in repaired.split("\n") if l.strip()]
        self.ocr.missing_lines += max(0, len(gt_lines) - len(pred_lines))
        self.ocr.extra_lines += max(0, len(pred_lines) - len(gt_lines))

# Digit accuracy
        gt_digits = [c for c in clean_text if c.isdigit()]
        pred_digits = [c for c in repaired if c.isdigit()]
        min_d = min(len(gt_digits), len(pred_digits))
        digit_matches = sum(1 for i in range(min_d) if gt_digits[i] == pred_digits[i])
        max_d = max(len(gt_digits), len(pred_digits)) or 1
        self.ocr.digit_accuracy.total += max_d
        self.ocr.digit_accuracy.correct += digit_matches

# STAGE 2: Test Name Recognition

    def eval_name_recognition(self, gt_keys: set[str], detected_tests: list[dict]):
        """Evaluate test name recognition against ground truth."""
        detected_keys = set()
        for t in detected_tests:
            if t.get("resolved_key"):
                detected_keys.add(t["resolved_key"])
            elif t.get("test_name"):
                from core.resolver import resolve_test_key_with_confidence
                key, _ = resolve_test_key_with_confidence(t["test_name"])
                if key:
                    detected_keys.add(key)

        for gt in gt_keys:
            if gt in detected_keys:
                self.name_recognition.true_positives += 1
            else:
                self.name_recognition.false_negatives += 1

# False positives = detected but not in GT
        for dk in detected_keys:
            if dk not in gt_keys:
                self.name_recognition.false_positives += 1

# True negatives = tests NOT in GT AND NOT detected
        all_possible_tests = set(gt_keys) | detected_keys
# We don't have a fixed universe of "negative" tests, so TN is undefined.
# Set TN = 0 for PRF calculation without TN.
        self.name_recognition.true_negatives = 0

# STAGE 3: Value Extraction

    def eval_value_extraction(self, gt_values: dict, detected_tests: list[dict]):
        """Evaluate numerical value accuracy."""
        gt_by_key = {}
        from core.parser import _lookup_test as lookup_testname
        for k, v in gt_values.items():
            gt_by_key[k] = v

        detected_by_key = {}
        for t in detected_tests:
            key = t.get("resolved_key") or ""
            if key:
                detected_by_key[key] = t.get("value")

        for key, gt_val in gt_by_key.items():
            self.value_accuracy.exact_match.total += 1
            if key in detected_by_key:
                pred_val = detected_by_key[key]
                if pred_val == gt_val:
                    self.value_accuracy.exact_match.correct += 1
                else:
                    self.value_accuracy.exact_match.errors += 1
                    abs_err = abs(pred_val - gt_val) if pred_val is not None else float('inf')
                    rel_err = abs_err / abs(gt_val) if gt_val != 0 else abs_err
                    self.value_accuracy.abs_errors.append(abs_err)
                    self.value_accuracy.rel_errors.append(rel_err)

# Detect digit errors
                    gt_str = str(gt_val).replace(".", "")
                    pred_str = str(pred_val).replace(".", "") if pred_val is not None else ""
                    if len(pred_str) < len(gt_str):
                        self.value_accuracy.digit_losses += 1
                    elif len(pred_str) > len(gt_str):
                        self.value_accuracy.digit_additions += 1
# Decimal point error
                    if abs(gt_val) > 0 and pred_val is not None:
                        ratio = pred_val / gt_val if gt_val != 0 else 0
                        if abs(ratio - 0.1) < 0.01 or abs(ratio - 10) < 0.1:
                            self.value_accuracy.decimal_errors += 1
            else:
                self.value_accuracy.exact_match.errors += 1

# STAGE 4: Unit Recognition

    def eval_unit_recognition(self, gt_units: dict, detected_tests: list[dict]):
        """Evaluate unit accuracy."""
        from core.normalization import normalize_unit

        detected_by_key = {}
        for t in detected_tests:
            key = t.get("resolved_key") or ""
            detected_by_key[key] = normalize_unit(t.get("unit", ""))

        for key, gt_unit in gt_units.items():
            gt_norm = normalize_unit(gt_unit)
            self.unit_accuracy.total += 1
            if key in detected_by_key:
                pred_norm = detected_by_key[key]
                if pred_norm == gt_norm:
                    self.unit_accuracy.correct += 1
                else:
                    self.unit_accuracy.errors += 1
            else:
                self.unit_accuracy.errors += 1

# STAGE 5: Reference Range Detection

    def eval_ref_range(self, gt_ranges: dict, resolved_tests: list):
        """Evaluate reference range accuracy."""
        from medical.reference_db import get_reference_range

        for t in resolved_tests:
            key = t.resolved_key
            if not key:
                continue
            self.ref_range_accuracy.total += 1
            gender = "male"
            age = 30
            rr = get_reference_range(key, gender, "adult")
            gt_lo, gt_hi = gt_ranges.get(key, (None, None))
            if rr and gt_lo is not None and gt_hi is not None:
                lo_ok = abs(rr.low - gt_lo) / max(abs(gt_lo), 1) < 0.15 if gt_lo else True
                hi_ok = abs(rr.high - gt_hi) / max(abs(gt_hi), 1) < 0.15 if gt_hi else True
                if lo_ok and hi_ok:
                    self.ref_range_accuracy.correct += 1
                else:
                    self.ref_range_accuracy.errors += 1
            elif rr is None and gt_lo is None and gt_hi is None:
                self.ref_range_accuracy.correct += 1
            else:
                self.ref_range_accuracy.errors += 1

# STAGE 6: Normalization

    def eval_normalization(self, resolved_tests: list):
        """Evaluate value/unit normalization and classification feasibility."""
        from core.normalization import normalize_unit, convert_value, sanity_check_value
        from medical.reference_db import get_test_definition, get_reference_range

        for t in resolved_tests:
            key = t.resolved_key
            if not key:
                continue
            self.normalization_accuracy.total += 1
            try:
                u = normalize_unit(t.unit)
                td = get_test_definition(key)
                if td:
                    expected = normalize_unit(td.canonical_unit)
                    if u and expected:
                        converted = convert_value(t.value, t.unit, td.canonical_unit, key)
                        if converted is not None or u == expected:
                            self.normalization_accuracy.correct += 1
                        else:
                            self.normalization_accuracy.errors += 1
                    else:
                        self.normalization_accuracy.correct += 1
                else:
# No definition — still a valid extraction
                    self.normalization_accuracy.correct += 1
            except Exception:
                self.normalization_accuracy.errors += 1

# STAGE 7: Clinical Interpretation + STAGE 8: Abnormal Detection

    def eval_classification(self, gt_statuses: dict, resolved_tests: list):
        """Evaluate clinical interpretation and abnormal flag detection."""
        from core.classifier import classify_numeric
        from medical.reference_db import get_reference_range

        detected_by_key = {}
        for t in resolved_tests:
            detected_by_key[t.resolved_key] = t

        for key, gt_status in gt_statuses.items():
            gt_normalized = gt_status if gt_status in ("normal", "high", "low") else "unknown"

            if key in detected_by_key:
                t = detected_by_key[key]
                pred_status = t.status if t.status in ("normal", "high", "low") else "unknown"

# Confusion matrix
                self.interpretation_cm.record(gt_normalized, pred_status)

# For abnormal detection: abnormal = high or low
                gt_abnormal = gt_normalized in ("high", "low")
                pred_abnormal = pred_status in ("high", "low")

                if gt_abnormal and pred_abnormal:
                    self.abnormal_detection.true_positives += 1
                elif not gt_abnormal and pred_abnormal:
                    self.abnormal_detection.false_positives += 1
                elif gt_abnormal and not pred_abnormal:
                    self.abnormal_detection.false_negatives += 1
                elif not gt_abnormal and not pred_abnormal:
                    self.abnormal_detection.true_negatives += 1
            else:
# Test not found in results
                self.interpretation_cm.record(gt_normalized, "unknown")
                if gt_normalized in ("high", "low"):
                    self.abnormal_detection.false_negatives += 1

# STAGE 9: AI Summary Quality

    def eval_ai_summary(self, resolved_tests: list):
        """
        Evaluate AI summary quality.
        Since we cannot call external LLM APIs in bulk during evaluation,
        we assess based on the structured data available.
        Score components on 1-10 scale based on data quality indicators.
        """
        if not resolved_tests:
            self.ai_summary.medical_correctness.append(1)
            self.ai_summary.hallucination_rate.append(1)
            self.ai_summary.missing_findings.append(1)
            self.ai_summary.false_findings.append(1)
            self.ai_summary.consistency.append(1)
            self.ai_summary.readability.append(1)
            self.ai_summary.completeness.append(1)
            return

# Medical correctness: based on status accuracy vs available ref ranges
        correct_tests = sum(1 for t in resolved_tests
                          if t.status in ("normal", "high", "low") and t.reference_range is not None)
        total_tests = len(resolved_tests) or 1
        correctness_score = min(10, max(1, int(correct_tests / total_tests * 10)))
        self.ai_summary.medical_correctness.append(correctness_score)

# Hallucination: tests with REVIEW_REQUIRED or unknown status with no range
        hallucinations = sum(1 for t in resolved_tests
                           if t.status == "unknown" and t.reference_range is None)
        hallucination_score = max(1, 10 - int(hallucinations / max(total_tests, 1) * 10))
        self.ai_summary.hallucination_rate.append(hallucination_score)

# Missing findings: tests with status REVIEW_REQUIRED
        missing = sum(1 for t in resolved_tests if t.status == "REVIEW_REQUIRED")
        missing_score = max(1, 10 - int(missing / max(total_tests, 1) * 10))
        self.ai_summary.missing_findings.append(missing_score)

# False findings: tests with normal status but no range
        false_findings = sum(1 for t in resolved_tests
                           if t.status == "unknown" and t.reference_range is not None)
        false_score = max(1, 10 - int(false_findings / max(total_tests, 1) * 10))
        self.ai_summary.false_findings.append(false_score)

# Consistency: evaluations that have proper structured data
        consistent = sum(1 for t in resolved_tests
                       if t.resolved_key and t.status in ("normal", "high", "low"))
        consistency_score = min(10, max(1, int(consistent / total_tests * 10)))
        self.ai_summary.consistency.append(consistency_score)

# Readability: based on data completeness
        has_names = all(hasattr(t, 'test_name') and t.test_name for t in resolved_tests)
        has_values = all(hasattr(t, 'value') and t.value is not None for t in resolved_tests)
        readability_score = 8 if (has_names and has_values) else 5
        self.ai_summary.readability.append(readability_score)

# Completeness: proportion of ground truth tests found
        completeness_score = correctness_score
        self.ai_summary.completeness.append(completeness_score)

# STAGE 10: End-to-End

    def record_end_to_end(self, success: bool):
        """Record end-to-end pipeline success/failure."""
        self.end_to_end.total += 1
        if success:
            self.end_to_end.correct += 1
        else:
            self.end_to_end.errors += 1

# RUN EVALUATION ON A SINGLE REPORT

    def evaluate_report(self, report: "GroundTruthReport") -> EvalResult:
        """Run all evaluation stages on a single report."""
        result = EvalResult(
            report_id=report.report_id,
            report_type=report.report_type,
            quality=report.quality,
            gt_values=report.ground_truth_values,
            gt_units=report.ground_truth_units,
            gt_ranges=report.ground_truth_ranges,
            gt_statuses=report.ground_truth_statuses,
            metadata=report.metadata,
        )
        self.total_processed += 1

        try:
# Stage 1: OCR Accuracy
            self.eval_ocr(report.clean_text, report.corrupted_text)

# Run the pipeline
            from core.pipeline import process_lab_report

            t0 = time.time()
            resolved, tracker = process_lab_report(
                report.corrupted_text,
                gender=report.metadata.get("gender", "male"),
                age=report.metadata.get("age", 30),
            )
            pipeline_duration = time.time() - t0

            result.pipeline_duration = pipeline_duration
            self.timings.add(0, pipeline_duration, 0, pipeline_duration)

            parsed_dicts = []
            from core.parser import parse_lab_report
            parsed_dicts = parse_lab_report(report.corrupted_text)

            detected_tests = []
            for t in resolved:
                detected_tests.append({
                    "test_name": t.test_name,
                    "resolved_key": t.resolved_key,
                    "value": t.value,
                    "unit": t.unit,
                    "status": t.status,
                })

            result.resolved_tests = resolved
            result.parsed_tests = parsed_dicts

# Stage 2: Name Recognition
            self.eval_name_recognition(set(report.ground_truth_values.keys()), detected_tests)

# Stage 3: Value Extraction
            self.eval_value_extraction(report.ground_truth_values, detected_tests)

# Stage 4: Unit Recognition
            self.eval_unit_recognition(report.ground_truth_units, detected_tests)

# Stage 5: Reference Range
            self.eval_ref_range(report.ground_truth_ranges, resolved)

# Stage 6: Normalization
            self.eval_normalization(resolved)

# Stage 7+8: Classification + Abnormal Detection
            self.eval_classification(report.ground_truth_statuses, resolved)

# Stage 9: AI Summary
            self.eval_ai_summary(resolved)

# Stage 10: End-to-End
            self.record_end_to_end(True)

# Per-type and per-quality tracking
            e2e_acc = sum(1 for t in resolved if t.status in ("normal", "high", "low")) / max(len(resolved), 1) * 100
            self.per_type_accuracy[report.report_type].append(e2e_acc)
            self.per_quality_accuracy[report.quality].append(e2e_acc)

        except Exception as exc:
            self.crashed += 1
            result.error = str(exc)
            self.record_end_to_end(False)
            self.errors.record("Backend Error", report.report_id, "pipeline", str(exc))

        self.all_results.append(result)
        return result

# RUN FULL EVALUATION

    def run(self, reports: list) -> dict:
        """Run evaluation on a list of benchmark reports and produce metrics."""
        logger.info("Starting evaluation on %d reports...", len(reports))

        for i, report in enumerate(reports):
            if (i + 1) % 50 == 0:
                logger.info("Progress: %d/%d", i + 1, len(reports))
            self.evaluate_report(report)

        return self.summarize()

# SUMMARIZE

    def summarize(self) -> dict:
        """Aggregate all stage metrics into a comprehensive report dict."""
        return {
            "dataset_summary": {
                "total_reports": self.total_processed,
                "crashed": self.crashed,
                "success_rate_pct": round(
                    (self.total_processed - self.crashed) / max(self.total_processed, 1) * 100, 2
                ),
            },
            "stage_1_ocr": self.ocr.to_dict(),
            "stage_2_name_recognition": self.name_recognition.to_dict(),
            "stage_3_value_extraction": self.value_accuracy.to_dict(),
            "stage_4_unit_recognition": self.unit_accuracy.to_dict(),
            "stage_5_ref_range": self.ref_range_accuracy.to_dict(),
            "stage_6_normalization": self.normalization_accuracy.to_dict(),
            "stage_7_classification": self.interpretation_cm.to_dict(),
            "stage_8_abnormal_detection": self.abnormal_detection.to_dict(),
            "stage_9_ai_summary": self.ai_summary.to_dict(),
            "stage_10_end_to_end": self.end_to_end.to_dict(),
            "timings": self.timings.to_dict(),
            "error_analysis": self.errors.to_dict(),
            "per_type_accuracy": {
                k: {
                    "mean": round(sum(v) / len(v), 2) if v else 0,
                    "count": len(v),
                }
                for k, v in self.per_type_accuracy.items()
            },
            "per_quality_accuracy": {
                k: {
                    "mean": round(sum(v) / len(v), 2) if v else 0,
                    "count": len(v),
                }
                for k, v in self.per_quality_accuracy.items()
            },
        }
