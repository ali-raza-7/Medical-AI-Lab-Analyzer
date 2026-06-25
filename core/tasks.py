"""Background task definitions for Celery workers"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import OrderedDict
from datetime import datetime

from core.celery_app import celery_app
from core.database import SessionLocal
from core.models import User, Analysis, CreditTransaction
from core.ocr import extract_text_sync
from core.pipeline import process_lab_report
from core.patient_metadata import extract_patient_metadata
from core.utils import sanitize_for_json
from medical.explainer import generate_explanation
from medical.reference_db import get_test_definition
from services.insights_service import LabResult, generate_grouped_insights, generate_clinical_insight

logger = logging.getLogger(__name__)

# Pipeline Cache (per-Celery-worker memory)

CACHE_VERSION = "2"
_pipeline_cache: OrderedDict[str, dict] = OrderedDict()
MAX_PIPELINE_CACHE = 100


def _get_pipeline_cache_key(text: str, gender: str, age: int) -> str:
    normalized_text = " ".join(text.split()).strip().lower()
    key_str = f"{CACHE_VERSION}|{normalized_text}|{gender.lower()}|{age}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _sort_key(test) -> tuple[int, str]:
    status = test.status
    rank = {"high": 0, "low": 0, "unknown": 1, "normal": 2}.get(status, 1)
    return (rank, test.test_name)


# Explanation Generation (async via asyncio.run in Celery worker)

async def _generate_explanations_async(
    resolved_tests, gender: str, age: int,
) -> dict[str, str]:
    """Generate LLM explanations for all abnormal tests in parallel."""
    explanations_dict: dict[str, str] = {}
    explanation_tasks: list[tuple[str, asyncio.Task]] = []

    for test in resolved_tests:
        if test.status in ("high", "low"):
            td = get_test_definition(test.resolved_key) if test.resolved_key else None
            context = td.what_it_measures if td else "Test not recognized from the report text."
            rr = test.reference_range
            lo = rr.low if rr.low is not None else "?"
            hi = rr.high if rr.high is not None else "?"
            expl_range = f"{lo} - {hi} {rr.unit}".strip()

            coro = generate_explanation(
                test.test_name, test.value, expl_range, context, test.status,
                gender=gender, age=age, age_group="adult",
            )
            explanation_tasks.append((test.test_name, coro))

    if explanation_tasks:
        coros = [coro for _, coro in explanation_tasks]
        results_expl = await asyncio.gather(*coros, return_exceptions=True)
        for (test_name, _), expl in zip(explanation_tasks, results_expl):
            if isinstance(expl, Exception):
                logger.error(
                    "explanation generation failed", test_name=test_name, error=str(expl),
                )
                explanations_dict[test_name] = "Explanation failed to generate."
            else:
                explanations_dict[test_name] = expl

    return explanations_dict


def _validate_patient_consistency(response: dict) -> None:
    """Log a warning if patient data diverges across response fields."""
    p = response.get("patient", {})
    pi = response.get("patient_info", {})
    pd = response.get("patient_detected", {})

    if p.get("age") != pi.get("age") or p.get("age") != pd.get("age"):
        logger.warning(
            "[consistency] patient age mismatch: patient=%s, info=%s, detected=%s",
            p.get("age"), pi.get("age"), pd.get("age"),
        )
    if p.get("gender") != pi.get("gender") or p.get("gender") != pd.get("gender"):
        logger.warning(
            "[consistency] patient gender mismatch: patient=%s, info=%s, detected=%s",
            p.get("gender"), pi.get("gender"), pd.get("gender"),
        )


def _build_analyze_response(
    resolved_tests, tracker, detected_gender, detected_age, metadata, explanations_dict,
) -> dict:
    """Build the standardized analysis response dict."""
    lab_results = [
        LabResult(
            test_key=test.resolved_key or "",
            test_name=test.test_name,
            status=test.status,
            value=test.value,
            unit=test.unit,
            value_normalized=test.value if test.reference_range else None,
            unit_normalized=test.unit,
        )
        for test in resolved_tests
    ]
    grouped_insights = generate_grouped_insights(lab_results)
    resolved_tests_sorted = sorted(resolved_tests, key=_sort_key)

    normal_c = sum(1 for t in resolved_tests if t.status == "normal")
    high_c = sum(1 for t in resolved_tests if t.status == "high")
    low_c = sum(1 for t in resolved_tests if t.status == "low")
    unknown_c = sum(1 for t in resolved_tests if t.status == "unknown")
    review_c = sum(1 for t in resolved_tests if t.status == "REVIEW_REQUIRED")

    response = {
        "patient": {"gender": detected_gender, "age": detected_age},
        "patient_info": {
            "age": detected_age,
            "gender": detected_gender,
        },
        "patient_detected": {
            "gender": detected_gender,
            "age": detected_age,
            "gender_confidence": "high" if metadata.get("gender") else "none",
            "age_confidence": "high" if metadata.get("age") else "none",
        },
        "completeness": tracker.to_dict(),
        "summary": {
            "total": len(resolved_tests),
            "normal": normal_c,
            "high": high_c,
            "low": low_c,
            "unknown": unknown_c,
            "review_required": review_c,
        },
        "insights": grouped_insights,
        "results": [
            {
                **t.to_dict(),
                "explanation": explanations_dict.get(t.test_name) or t.to_dict()["explanation"],
                "clinical_insight": (
                    generate_clinical_insight(
                        test_key=t.resolved_key or "",
                        test_name=t.test_name,
                        value=t.value,
                        ref_min=t.reference_range.low if t.reference_range else 0,
                        ref_max=t.reference_range.high if t.reference_range else 0,
                        status=t.status,
                        age=detected_age,
                        gender=detected_gender,
                    )
                    if t.status in ("high", "low") and t.reference_range
                    else None
                ),
            }
            for t in resolved_tests_sorted
        ],
        "disclaimer": "This is not a medical diagnosis.",
    }
    _validate_patient_consistency(response)
    return sanitize_for_json(response)


# CELERY TASK: perform_analysis

@celery_app.task(bind=True, acks_late=True, max_retries=1, default_retry_delay=10)
def perform_analysis(
    self,
    file_content: bytes | None = None,
    file_filename: str | None = None,
    text: str | None = None,
    gender: str = "male",
    age: int = 30,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    """Run the full analysis pipeline in a background Celery worker"""
    db = SessionLocal()
    try:
# Stage 1: OCR extraction
        if file_content:
            logger.info("[task] OCR started (file=%s)", file_filename)
            raw_text = extract_text_sync(file_content)
            logger.info("[task] OCR complete (%d chars)", len(raw_text or ""))
        else:
            raw_text = text
            logger.info("[task] text input (%d chars)", len(raw_text or ""))

        logger.info("[OCR RAW TEXT]:\n%s", raw_text)

        if not raw_text or not raw_text.strip():
            return {"status": "error", "code": 400, "detail": "No text content found in input."}

# Cache check AFTER OCR (key based on actual text, not raw text param)
        cache_key = _get_pipeline_cache_key(raw_text, gender, age)
        if cache_key in _pipeline_cache:
            sanitized = _pipeline_cache[cache_key]
            logger.info("[task] pipeline cache hit, returning cached result")
        else:
# Stage 2: Patient metadata
            logger.info("[task] extracting patient metadata")
            metadata = extract_patient_metadata(raw_text)
            detected_gender = metadata.get("gender") or gender
            detected_age = metadata.get("age") or age
            logger.info("[task] extracted — gender=%s, age=%s", detected_gender, detected_age)

# Stage 3: Pipeline processing
            logger.info("[task] AI pipeline started")
            try:
                resolved_tests, tracker = process_lab_report(
                    raw_text, gender=detected_gender, age=detected_age,
                )
            except AssertionError as exc:
                logger.critical("[task] pipeline integrity check failed: %s", exc)
                return {"status": "error", "code": 500, "detail": "Internal pipeline integrity error."}
            except Exception as exc:
                logger.error("[task] pipeline failed: %s", exc)
                return {"status": "error", "code": 500, "detail": "Report analysis failed."}
            logger.info("[task] AI pipeline complete (%d tests parsed)", tracker.total_parsed)

            if tracker.total_parsed == 0:
                return {"status": "error", "code": 422, "detail": "No lab results found in input."}

# Stage 4: LLM explanations
            logger.info("[task] LLM explanation generation started (%d tests)", sum(1 for t in resolved_tests if t.status in ("high", "low")))
            explanations_dict = asyncio.run(
                _generate_explanations_async(resolved_tests, detected_gender, detected_age),
            )
            logger.info("[task] LLM explanation generation complete")

# Stage 5: Build response dict
            logger.info("[task] building response")
            sanitized = _build_analyze_response(
                resolved_tests, tracker, detected_gender, detected_age,
                metadata, explanations_dict,
            )

# Stage 6: Update per-worker pipeline cache
            _pipeline_cache[cache_key] = sanitized
            _pipeline_cache.move_to_end(cache_key)
            if len(_pipeline_cache) > MAX_PIPELINE_CACHE:
                _pipeline_cache.popitem(last=False)

# Stage 7: Database persistence
        filename = file_filename or "text_input"
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"status": "error", "code": 404, "detail": "User not found."}
            analysis = Analysis(
                user_id=user_id, file_name=filename, results_json=sanitized,
            )
            user.credits -= 1
            db.add(CreditTransaction(
                user_id=user_id, amount=-1, description=f"Analysis: {filename}",
            ))
        else:
            analysis = Analysis(
                user_id=None, file_name=session_id, results_json=sanitized,
            )

        db.add(analysis)
        db.commit()

        return {"status": "success", "data": sanitized}

    except Exception as exc:
        db.rollback()
        logger.error("[task] analysis failed unexpectedly: %s", exc, exc_info=True)
        try:
            raise self.retry(exc=exc)
        except Exception:
            return {
                "status": "error",
                "code": 500,
                "detail": f"Analysis failed after retries: {str(exc)}",
            }
    finally:
        db.close()
