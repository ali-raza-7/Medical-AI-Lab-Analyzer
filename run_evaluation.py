# /usr/bin/env python3
"""
Medical Blood Test Analysis System — Full Accuracy Evaluation Runner.

Usage:
  python run_evaluation.py                        # Run with 280 reports
  python run_evaluation.py --scale 500            # Scale to ~500 reports
  python run_evaluation.py --report report.md     # Save report to file
  python run_evaluation.py --save-dataset /tmp/   # Save benchmark dataset
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("run_eval")

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description="Run full accuracy evaluation on the Medical Blood Test Analysis System"
    )
    parser.add_argument("--scale", type=int, default=280,
                        help="Target number of benchmark reports (default: 280)")
    parser.add_argument("--report", type=str, default=None,
                        help="Path to save the final markdown report")
    parser.add_argument("--json", type=str, default=None,
                        help="Path to save raw metrics as JSON")
    parser.add_argument("--save-dataset", type=str, default=None,
                        help="Directory to save the benchmark dataset")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("MEDICAL BLOOD TEST ANALYSIS SYSTEM — ACCURACY EVALUATION")
    logger.info("=" * 70)

# Phase 1: Generate Benchmark Dataset
    logger.info("Phase 1: Generating benchmark dataset...")
    t0 = time.time()

# Scale: we can adjust by increasing reports per quality level
    from eval_framework.benchmark import generate_dataset
    reports = generate_dataset(output_dir=args.save_dataset)
    
    logger.info("Generated %d benchmark reports in %.2fs", len(reports), time.time() - t0)

# Phase 2: Run Evaluation
    logger.info("Phase 2: Running evaluation...")
    t1 = time.time()

    from eval_framework.evaluator import PipelineAccuracyEvaluator
    evaluator = PipelineAccuracyEvaluator()
    metrics = evaluator.run(reports)

    elapsed = time.time() - t1
    logger.info("Evaluation completed in %.2fs", elapsed)

# Phase 3: Generate Report
    logger.info("Phase 3: Generating report...")

    from eval_framework.report import generate_report
    report_path = args.report or os.path.join(
        os.path.dirname(__file__), "accuracy_report.md"
    )
    report_md = generate_report(metrics, output_path=report_path)

# Save raw JSON metrics
    if args.json:
        with open(args.json, "w") as f:
            json.dump(metrics, f, indent=2, default=str)
        logger.info("Raw metrics saved to %s", args.json)
    else:
        json_path = report_path.replace(".md", ".json") if report_path.endswith(".md") else "/tmp/eval_metrics.json"
        with open(json_path, "w") as f:
            json.dump(metrics, f, indent=2, default=str)
        logger.info("Raw metrics saved to %s", json_path)

# Phase 4: Print Summary
    ds = metrics.get("dataset_summary", {})
    e2e = metrics.get("stage_10_end_to_end", {})
    ocr = metrics.get("stage_1_ocr", {})
    name = metrics.get("stage_2_name_recognition", {})
    vals = metrics.get("stage_3_value_extraction", {})
    unit = metrics.get("stage_4_unit_recognition", {})
    interp = metrics.get("stage_7_classification", {})
    abnorm = metrics.get("stage_8_abnormal_detection", {})
    timing = metrics.get("timings", {})

    print()
    print("=" * 70)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Dataset:        {ds.get('total_reports', 0)} reports across 7 types × 6 qualities")
    print(f"  Crashes:        {ds.get('crashed', 0)} ({100 - ds.get('success_rate_pct', 0):.1f}%)")
    print(f"  Total Time:     {elapsed:.1f}s")
    print()
    print("  Stage 1  OCR Accuracy (CER):        {:.2f}%".format(ocr.get("cer_pct", 0)))
    print("  Stage 2  Name Recognition (F1):     {:.2f}%".format(name.get("f1_pct", 0)))
    print("  Stage 3  Value Extraction:          {:.2f}%".format(vals.get("exact_match", {}).get("accuracy_pct", 0)))
    print("  Stage 4  Unit Recognition:          {:.2f}%".format(unit.get("accuracy_pct", 0)))
    print("  Stage 5  Ref Range:                 {:.2f}%".format(metrics.get("stage_5_ref_range", {}).get("accuracy_pct", 0)))
    print("  Stage 6  Normalization:             {:.2f}%".format(metrics.get("stage_6_normalization", {}).get("accuracy_pct", 0)))
    print("  Stage 7  Interpretation:            {:.2f}%".format(interp.get("accuracy_pct", 0)))
    print("  Stage 8  Abnormal Detection (F1):   {:.2f}%".format(abnorm.get("f1_pct", 0)))
    print("  Stage 9  AI Summary Quality:        {:.2f}%".format(metrics.get("stage_9_ai_summary", {}).get("overall", 0)))
    print("  Stage 10 End-to-End:                {:.2f}%".format(e2e.get("accuracy_pct", 0)))
    print()
    print(f"  Report saved to: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
