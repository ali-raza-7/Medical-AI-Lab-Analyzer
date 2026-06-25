from __future__ import annotations

import json
import os
import logging
from dataclasses import dataclass
from typing import Literal, Optional
import re
logger = logging.getLogger(__name__)

Gender = Literal["male", "female"]
AgeGroup = Literal["child", "teen", "adult", "elderly"]


@dataclass(frozen=True)
class ReferenceRange:
    low: float
    high: float
    unit: str
    description: str


@dataclass(frozen=True)
class TestDefinition:
    key: str
    display_name: str
    canonical_unit: str
    ranges: dict[str, dict[str, ReferenceRange]]
    what_it_measures: str


class LabReferenceDB:
    """Singleton-like loader for the laboratory reference dataset."""
    _instance = None
    _tests: dict[str, TestDefinition] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LabReferenceDB, cls).__new__(cls)
            cls._instance._load_data()
        return cls._instance

    def _load_data(self):
# Determine path to JSON relative to this file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, "medical", "lab_reference_dataset.json")

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                for entry in data:
                    key = entry["key"]

# Convert raw JSON ranges to ReferenceRange objects
                    ranges = {}
                    for gender, groups in entry.get("ranges", {}).items():
                        ranges[gender] = {}
                        for age_group, limits in groups.items():
                            ranges[gender][age_group] = ReferenceRange(
                                low=float(limits["low"]) if limits.get("low") is not None else 0.0,
                                high=float(limits["high"]) if limits.get("high") is not None else 999999.0,
                                unit=entry["canonical_unit"],
                                description=f"{age_group.capitalize()} {gender}"
                            )

                    self._tests[key] = TestDefinition(
                        key=key,
                        display_name=entry["display_name"],
                        canonical_unit=entry["canonical_unit"],
                        ranges=ranges,
                        what_it_measures=entry["what_it_measures"]
                    )
            logger.info(f"Loaded {len(self._tests)} tests from {json_path}")
        except Exception as e:
            logger.error(f"Failed to load reference dataset: {e}")
# Minimal fallback to avoid total crash
            self._tests = {}

    def get_test(self, key: str) -> Optional[TestDefinition]:
        return self._tests.get(key)

    def get_all_tests(self) -> dict[str, TestDefinition]:
        return self._tests


_db = LabReferenceDB()

# Backward Compatibility Layer
TESTS = _db.get_all_tests()

def get_test_definition(key: str) -> Optional[TestDefinition]:
    """Public API to get test metadata."""
# Standardize incoming keys (e.g. pluralization fix)
    if key == "neutrophil_abs": key = "neutrophils_abs"
    return _db.get_test(key)


def get_reference_range(key: str, gender: str, age_group: str) -> Optional[ReferenceRange]:
    """Public API to get a specific reference range."""
    td = get_test_definition(key)
    if not td:
        return None

    g = gender.lower() if gender.lower() in ("male", "female") else "male"
    ag = age_group.lower() if age_group.lower() in ("child", "teen", "adult", "elderly") else "adult"

    by_gender = td.ranges.get(g)
    if not by_gender:
# Fallback: try the other gender's ranges before giving up
        fallback_gender = "female" if g == "male" else "male"
        by_gender = td.ranges.get(fallback_gender)
        if not by_gender:
            return None
        logger.debug(
            "[reference_db] gender %r not found for %r — falling back to %r",
            g, key, fallback_gender,
        )

    return by_gender.get(ag) or by_gender.get("adult")
