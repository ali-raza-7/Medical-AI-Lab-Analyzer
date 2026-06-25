import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalNormalizer:
    def __init__(self, reference_path: str = "medical/lab_reference_dataset.json"):
        self.reference_data = self._load_reference(reference_path)
        self.key_map = self._build_key_map()

    def _load_reference(self, path: str) -> List[Dict[str, Any]]:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load reference data: {e}")
            return []

    def _build_key_map(self) -> Dict[str, str]:
        """Maps common display names and aliases to canonical keys."""
        mapping = {}
        for entry in self.reference_data:
            key = entry['key']
            mapping[key.lower()] = key
            mapping[entry['display_name'].lower()] = key

        # Add common clinical aliases and OCR typos
        aliases = {
            "hgb": "hemoglobin",
            "hb": "hemoglobin",
            "hemoglobn": "hemoglobin",
            "hemglobin": "hemoglobin",
            "hct": "hematocrit",
            "plt": "platelets",
            "wbc count": "wbc",
            "rbc count": "rbc",
            "gluco": "glucose_fasting",
            "fbs": "glucose_fasting",
            "ppbs": "glucose_pp",
            "tsh level": "tsh",
            "anc": "neutrophils_abs",
            "alc": "lymphocytes_abs",
            "crea": "creatinine",
            "bun": "bun",
            "b.u.n": "bun",
            "sugar": "glucose_fasting",
        }
        for alias, key in aliases.items():
            mapping[alias] = key
        return mapping

    def clean_ocr_value(self, raw_value: str) -> Optional[float]:
        """Extracts a numeric value from a noisy OCR string."""
        if raw_value is None: return None
        s = str(raw_value).strip().lower()

        # Specific cleanup for known noise patterns
        s = re.sub(r'\borsl\b', '', s)
        s = re.sub(r'\bmeeacop\b', '', s)
        s = re.sub(r'\ba\b', ' ', s) # handles "6 a"

        # Remove scientific notation noise but keep the structure
        s = s.replace('x10^', 'e')
        s = s.replace('x 10^', 'e')

        # Extract first valid number (float or int)
        match = re.search(r"[-+]?\d*\.\d+|\d+", s)
        if match:
            try:
                val = float(match.group())
                return val
            except ValueError:
                return None
        return None

    def fix_scaling(self, value: float, key: str) -> float:
        """Fixes common scaling errors (e.g., 448% -> 44.8%)."""
        # Common 10x or 100x errors in HGB/HCT/MCV
        scaling_fixes = {
            "hematocrit": (100, 10.0),
            "hemoglobin": (100, 10.0),
            "mchc": (100, 10.0),
            "mcv": (500, 10.0),
        }

        if key in scaling_fixes:
            threshold, divisor = scaling_fixes[key]
            if value >= threshold:
                return value / divisor

        # Percentage scaling
        if "pct" in key or key in ["neutrophils_pct", "lymphocytes_pct", "monocytes_pct", "eosinophils_pct", "basophils_pct"]:
            if value > 100: return value / 10.0

        return value

    def get_canonical_key(self, test_name: str) -> Optional[str]:
        name = test_name.strip().lower()
        # Direct match
        if name in self.key_map:
            return self.key_map[name]

        # Fuzzy match using SequenceMatcher
        best_match = None
        highest_score = 0.0

        for alias, key in self.key_map.items():
            score = SequenceMatcher(None, name, alias).ratio()
            if score > 0.85 and score > highest_score:
                highest_score = score
                best_match = key

        return best_match

    def validate_range(self, value: float, key: str, gender: str = "male", age_group: str = "adult") -> str:
        """Determines if a value is LOW, NORMAL, or HIGH."""
        entry = next((item for item in self.reference_data if item["key"] == key), None)
        if not entry:
            return "UNKNOWN"

        gender_data = entry.get("ranges", {}).get(gender.lower(), {})
        range_data = gender_data.get(age_group.lower()) or gender_data.get("adult")

        if not range_data:
            return "UNKNOWN"

        low = range_data.get("low")
        high = range_data.get("high")

        if low is not None and value < low:
            return "LOW"
        if high is not None and value > high:
            return "HIGH"
        return "NORMAL"

    def safety_check(self, value: float, key: str) -> Optional[str]:
        """Flags medically impossible or dangerous values."""
        safety_bounds = {
            "hemoglobin": (2.0, 25.0),
            "ph_arterial": (6.5, 8.0),
            "potassium": (1.5, 10.0),
            "mchc": (20.0, 50.0),
        }

        if key in safety_bounds:
            low, high = safety_bounds[key]
            if value < low or value > high:
                return f"CRITICAL: Biologically improbable value ({value})"
        return None

    def normalize(self, raw_results: List[Dict[str, Any]], gender: str = "male", age_group: str = "adult") -> List[Dict[str, Any]]:
        normalized = []
        seen_keys = {} # For duplicate removal

        for res in raw_results:
            test_name = res.get("test_name", "")
            raw_val = res.get("value")

            key = self.get_canonical_key(test_name)
            if not key:
                continue

            val = self.clean_ocr_value(str(raw_val))
            if val is None:
                continue

            val = self.fix_scaling(val, key)

            # Clinical safety
            warning = self.safety_check(val, key)

            # Status
            status = self.validate_range(val, key, gender, age_group)

            # Build entry
            entry = next((item for item in self.reference_data if item["key"] == key), {})

            processed = {
                "test_key": key,
                "display_name": entry.get("display_name", key),
                "value": val,
                "unit": entry.get("canonical_unit"),
                "status": status,
                "explanation": entry.get("what_it_measures"),
                "warning": warning
            }

            # Duplicate handling: keep latest (assuming sequential processing)
            seen_keys[key] = processed

        return list(seen_keys.values())

# Single function interface as requested
def normalize_lab_results(raw_results: List[Dict[str, Any]], gender: str = "male", age_group: str = "adult") -> List[Dict[str, Any]]:
    normalizer = MedicalNormalizer()
    return normalizer.normalize(raw_results, gender, age_group)

if __name__ == "__main__":
    # Test case
    raw = [
        {"test_name": "Hemoglobn", "value": "135", "unit": "g/dL"}, # Scaling issue 135 -> 13.5
        {"test_name": "WBC", "value": "6 a", "unit": "k/uL"},       # OCR noise
        {"test_name": "Hematocrit", "value": "448%", "unit": "%"}, # Scaling 448 -> 44.8
        {"test_name": "PLT", "value": "1 orsl", "unit": "10^3"},   # OCR noise
        {"test_name": "MCHC", "value": "234", "unit": "g/dL"},     # Impossible value
    ]
    results = normalize_lab_results(raw)
    print(json.dumps(results, indent=2))
