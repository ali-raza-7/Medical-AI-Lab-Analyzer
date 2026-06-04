import logging
import math
from dataclasses import is_dataclass, asdict

logger = logging.getLogger(__name__)

def sanitize_for_json(obj):
    """
    Recursively sanitize objects for JSON serialization.
    Rules:
    - Primitives: None, bool, int pass through.
    - Floats: Handle NaN/Infinity by converting to None (null).
    - dicts/lists/dataclasses: recurse.
    - Unknown types: convert to str().
    """
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            logger.warning("[sanitize] replacing invalid float %f with null", obj)
            return None
        return obj

    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]

    # Handle dataclasses (e.g. ReferenceRange, ResolvedTest)
    if is_dataclass(obj) and not isinstance(obj, type):
        try:
            return sanitize_for_json(asdict(obj))
        except Exception as e:
            logger.warning("[sanitize] failed to convert dataclass %s: %s", type(obj).__name__, e)
            return str(obj)  # safe fallback — never None

    # Unknown type — log + convert to string so frontend never gets an object
    logger.warning(
        "[sanitize] non-serializable type %s in response — converting to string",
        type(obj).__name__,
    )
    return str(obj)
