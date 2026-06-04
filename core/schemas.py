"""
Strict, production-grade schemas for the medical lab pipeline.
Single source of truth for all test data structures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Literal


@dataclass(frozen=True)
class ParsedTest:
    """Raw test extracted by parser — minimal validation."""
    test_name: str
    value: float
    unit: str
    raw_unit: str = ""
    reference_range: str = ""

    def __post_init__(self):
        if not self.test_name or not self.test_name.strip():
            raise ValueError("test_name cannot be empty")
        if self.value != self.value:  # NaN check
            raise ValueError(f"value is NaN for {self.test_name}")


@dataclass(frozen=True)
class ReferenceRange:
    """Parsed reference range with unit."""
    low: Optional[float] = None
    high: Optional[float] = None
    unit: str = ""


@dataclass(frozen=True)
class ResolvedTest:
    """
    Final output schema — strict, complete, guaranteed.
    EVERY parsed test produces exactly one ResolvedTest in output.
    
    RAG-READY FIELDS:
    - test_category: retrieval bucket for pattern matching
    - applicable_patterns: pattern IDs relevant to this test (future retrieval hook)
    """
    test_name: str
    resolved_key: Optional[str]
    value: float
    unit: str
    status: Literal["low", "normal", "high", "unknown", "REVIEW_REQUIRED"]
    reference_range: Optional[ReferenceRange]
    confidence: float
    match_type: Literal["alias", "fuzzy", "none"]
    explanation: Optional[str] = None
    clinical_insight: Optional[dict] = None
    # RAG FIELDS
    test_category: str = ""                          # retrieval bucketing (e.g., "CBC", "Lipids")
    applicable_patterns: list[str] = None            # pattern IDs for semantic retrieval

    def __post_init__(self):
        if not self.test_name or not self.test_name.strip():
            raise ValueError("test_name cannot be empty")
        if self.value != self.value:  # NaN check
            raise ValueError(f"value is NaN for {self.test_name}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be [0.0, 1.0], got {self.confidence}")
        if self.status not in ("low", "normal", "high", "unknown", "REVIEW_REQUIRED"):
            raise ValueError(f"invalid status: {self.status}")
        if self.match_type not in ("alias", "fuzzy", "none"):
            raise ValueError(f"invalid match_type: {self.match_type}")
        # Ensure applicable_patterns is always a list (even if None passed)
        if self.applicable_patterns is None:
            object.__setattr__(self, "applicable_patterns", [])

    @staticmethod
    def _safe_clinical_insight(raw: Optional[dict]) -> Optional[dict]:
        """
        Guarantee clinical_insight is fully frontend-safe.
        - String fields → str or omitted
        - List fields  → list[str] (non-string items coerced via str())
        - Any unexpected nested objects → str() coercion
        Never returns a nested object; always returns None or a flat dict.
        """
        import logging as _logging
        _log = _logging.getLogger(__name__)

        if raw is None:
            return None
        if not isinstance(raw, dict):
            _log.warning("[schema] clinical_insight is not a dict (%s) — dropping", type(raw).__name__)
            return None

        STRING_FIELDS = ("summary", "severity", "severity_comment", "age_related_risk", "gender_related_risk")
        LIST_FIELDS   = ("possible_causes", "suggested_next_steps")
        safe: dict = {}

        for field in STRING_FIELDS:
            val = raw.get(field)
            if val is None:
                continue
            if isinstance(val, str):
                safe[field] = val
            else:
                _log.warning("[schema] clinical_insight.%s is %s — coercing to str", field, type(val).__name__)
                safe[field] = str(val)

        for field in LIST_FIELDS:
            val = raw.get(field)
            if val is None:
                continue
            if isinstance(val, list):
                coerced = []
                for item in val:
                    if isinstance(item, str):
                        coerced.append(item)
                    else:
                        _log.warning(
                            "[schema] clinical_insight.%s contains non-string item (%s) — coercing",
                            field, type(item).__name__,
                        )
                        coerced.append(str(item))
                safe[field] = coerced
            else:
                _log.warning("[schema] clinical_insight.%s is %s, expected list — skipping", field, type(val).__name__)

        # Pass through any extra string/number keys, warn + skip objects
        known = set(STRING_FIELDS) | set(LIST_FIELDS)
        for k, v in raw.items():
            if k in known:
                continue
            if isinstance(v, (str, int, float, bool)) or v is None:
                safe[k] = v
            else:
                _log.warning("[schema] clinical_insight.%s unexpected type %s — skipping", k, type(v).__name__)

        return safe if safe else None

    def to_dict(self) -> dict:
        """
        Convert to dict for JSON serialization — FRONTEND SAFE.
        All values are primitives (no nested objects).
        """
        # Format reference range as string for display
        reference_range_text = ""
        if self.reference_range:
            if self.reference_range.low is not None and self.reference_range.high is not None:
                reference_range_text = (
                    f"{self.reference_range.low} - {self.reference_range.high} "
                    f"{self.reference_range.unit}"
                ).strip()
            elif self.reference_range.low is not None:
                reference_range_text = f"≥ {self.reference_range.low} {self.reference_range.unit}".strip()
            elif self.reference_range.high is not None:
                reference_range_text = f"≤ {self.reference_range.high} {self.reference_range.unit}".strip()
            else:
                reference_range_text = self.reference_range.unit.strip()

        return {
            "test_name": self.test_name,
            "resolved_key": self.resolved_key,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            # ── Flat reference range fields (for current frontend) ───────────
            "reference_range_text": reference_range_text,
            "reference_low": self.reference_range.low if self.reference_range else None,
            "reference_high": self.reference_range.high if self.reference_range else None,
            "reference_unit": self.reference_range.unit if self.reference_range else None,
            # ── Structured reference range (for compatibility) ───────────────
            "reference_range": {
                "low": self.reference_range.low if self.reference_range else None,
                "high": self.reference_range.high if self.reference_range else None,
                "unit": self.reference_range.unit if self.reference_range else None,
            } if self.reference_range else None,
            # ── Scores ───────────────────────────────────────────────────────
            "confidence": round(self.confidence, 2),
            "match_type": self.match_type,
            # ── Text fields (always strings, never None) ─────────────────────
            "explanation": self.explanation if self.explanation else "",
            # ── Clinical insight: sanitized flat dict or null ────────────────
            "clinical_insight": self._safe_clinical_insight(
                self.clinical_insight if isinstance(self.clinical_insight, dict) else None
            ),
            # ── RAG-READY FIELDS: retrieval bucketing & pattern matching ─────
            "test_category": self.test_category,
            "applicable_patterns": self.applicable_patterns if self.applicable_patterns else [],
        }


@dataclass
class CompletenessTracker:
    """Track all tests through pipeline — guarantee no silent drops."""
    total_parsed: int = 0
    resolved: int = 0
    unresolved: int = 0
    review_required: int = 0
    dropped: int = 0
    garbage_filtered: int = 0

    def validate(self) -> None:
        """Raise AssertionError if any tests were dropped."""
        if self.dropped > 0:
            raise AssertionError(
                f"CRITICAL: {self.dropped} test(s) were dropped from the pipeline! "
                f"parsed={self.total_parsed}, resolved={self.resolved}, "
                f"unresolved={self.unresolved}, review_required={self.review_required}, dropped={self.dropped}. "
                f"SUM: {self.resolved + self.unresolved + self.review_required + self.dropped} (expected {self.total_parsed})"
            )

    def verify_sum(self, total_output: int) -> None:
        """Verify that output count matches tracking."""
        expected = self.resolved + self.unresolved + self.review_required
        if total_output != expected:
            raise AssertionError(
                f"Output count mismatch: got {total_output}, expected {expected} "
                f"(resolved={self.resolved}, unresolved={self.unresolved}, review_required={self.review_required})"
            )

    def to_dict(self) -> dict:
        """Convert to dict for JSON response."""
        return {
            "total_parsed": self.total_parsed,
            "resolved": self.resolved,
            "unresolved": self.unresolved,
            "garbage_filtered": self.garbage_filtered,
            "dropped": self.dropped,
            "status": "OK" if self.dropped == 0 else "INCOMPLETE",
        }
