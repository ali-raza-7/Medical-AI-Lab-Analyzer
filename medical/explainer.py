"""Multi-LLM explanation generator with Gemini (primary) and Groq (fallback)"""
from __future__ import annotations

import logging
import os
import asyncio
import hashlib
from functools import lru_cache
from dotenv import load_dotenv
from groq import AsyncGroq

# Load .env FIRST — must happen before os.getenv()
load_dotenv()

logger = logging.getLogger(__name__)

# Startup validation: at least one LLM API key must be configured
if not os.getenv("GROQ_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    logging.warning(
        "No LLM API key configured — LLM explanation features disabled. Set GROQ_API_KEY or GEMINI_API_KEY in env."
    )

# EXPLANATION CACHE

_explanation_cache: dict[str, str] = {}  # Cache of generated explanations
MAX_CACHE_SIZE = 500  # Limit cache to prevent memory bloat

def _make_cache_key(test: str, value: float, status: str, ref_range: str, gender: str = "", age: int | None = None) -> str:
    """Create cache key from explanation parameters."""
    age_part = str(age) if age is not None else ""
    key_str = f"{test}|{value}|{status}|{ref_range}|{gender}|{age_part}"
    return hashlib.md5(key_str.encode()).hexdigest()[:16]

def _get_cached_explanation(test: str, value: float, status: str, ref_range: str, gender: str = "", age: int | None = None) -> str | None:
    """Retrieve cached explanation if available."""
    key = _make_cache_key(test, value, status, ref_range, gender, age)
    result = _explanation_cache.get(key)
    if result:
        logger.debug("[cache] HIT for %r (key=%s)", test, key)
    else:
        logger.debug("[cache] MISS for %r (key=%s)", test, key)
    return result

def _cache_explanation(test: str, value: float, status: str, ref_range: str, explanation: str, gender: str = "", age: int | None = None) -> None:
    """Store explanation in cache."""
# Simple eviction: clear cache if too large
    if len(_explanation_cache) >= MAX_CACHE_SIZE:
        _explanation_cache.clear()
        logger.debug("[cache] cleared explanation cache (size limit reached)")

    key = _make_cache_key(test, value, status, ref_range, gender, age)
    _explanation_cache[key] = explanation
    logger.debug("[cache] STORED explanation for %r (key=%s, size=%d)", test, key, len(_explanation_cache))

# GEMINI CLIENT INITIALIZATION

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = "gemini-1.5-flash"  # Lightweight, fast model

gemini_client = None
gemini_available = False

if not GEMINI_API_KEY:
    logger.debug("[explainer] GEMINI_API_KEY not configured. Gemini unavailable.")
elif GEMINI_API_KEY == "AIzaSyBx385G468qEGRh1JH2ufGac_Tkvc_QsHI":
    logger.debug("[explainer] GEMINI_API_KEY placeholder detected. Gemini unavailable.")
    GEMINI_API_KEY = ""
else:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_client = genai.GenerativeModel(GEMINI_MODEL)
        gemini_available = True
        logger.info(
            "[explainer] Gemini client initialized — model=%s, key=%s...",
            GEMINI_MODEL, GEMINI_API_KEY[:8]
        )
    except ImportError:
        logger.debug(
            "[explainer] google-generativeai not installed. "
            "Gemini unavailable. Run: pip install google-generativeai"
        )
        gemini_available = False
    except Exception as exc:
        logger.error("[explainer] Failed to initialize Gemini client: %s", exc)
        gemini_available = False

# GROQ CLIENT INITIALIZATION (FALLBACK)

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = "llama-3.3-70b-versatile"

groq_client: AsyncGroq | None = None

if not GROQ_API_KEY:
    logger.debug(
        "[explainer] GROQ_API_KEY not configured. Groq fallback unavailable. "
        "To enable Groq, add GROQ_API_KEY to .env"
    )
elif GROQ_API_KEY == "your_groq_api_key_here":
    logger.debug(
        "[explainer] GROQ_API_KEY has placeholder value. "
        "Please configure your actual API key in .env to enable Groq."
    )
    GROQ_API_KEY = ""
else:
    try:
        groq_client = AsyncGroq(api_key=GROQ_API_KEY)
        logger.info("[explainer] Groq client initialized — model=%s", GROQ_MODEL)
    except Exception as exc:
        logger.error("[explainer] Failed to initialize Groq client: %s", exc)
        groq_client = None


# UNIFIED EXPLANATION GENERATION

async def generate_explanation(
    test: str,
    value: float,
    ref_range: str,
    context: str,
    status: str,
    *,
    gender: str = "",
    age: int | None = None,
    age_group: str = "",
) -> str:
    """Generate medical explanation using Gemini (primary) or Groq (fallback)"""

# CHECK CACHE FIRST
    cached = _get_cached_explanation(test, value, status, ref_range, gender=gender, age=age)
    if cached:
        logger.debug("[cache] cache hit for test=%r", test)
        return cached

# Build the prompt (shared between APIs)
    prompt = _build_prompt(test, value, ref_range, context, status, gender, age, age_group)

# Tier 1: Try Gemini
    if gemini_available:
        logger.info("[explainer] Attempting Gemini generation for test=%r", test)
        result = await _generate_with_gemini(prompt, test)
        if result:
            _cache_explanation(test, value, status, ref_range, result, gender=gender, age=age)
            return result

# Tier 2: Fallback to Groq
    if groq_client:
        logger.info("[explainer] Attempting Groq generation for test=%r", test)
        result = await _generate_with_groq(prompt, test)
        if result:
            _cache_explanation(test, value, status, ref_range, result, gender=gender, age=age)
            return result

# Tier 3: Structured text fallback
    logger.warning("[explainer] All LLM APIs unavailable, using fallback text")
    fallback_result = _fallback(test, value, ref_range, context, status, age_group,
                     note="⚠ Explanation service temporarily unavailable.")
    _cache_explanation(test, value, status, ref_range, fallback_result, gender=gender, age=age)
    return fallback_result


# GEMINI GENERATION

async def _generate_with_gemini(prompt: str, test: str) -> str | None:
    """Call Gemini API for explanation generation."""
    try:
# Run blocking Gemini call in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: gemini_client.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.4,
                    "max_output_tokens": 300,
                }
            )
        )

        if response.text:
            logger.info(
                "[explainer] Gemini success — test=%r, chars=%d",
                test, len(response.text)
            )
            return response.text
        else:
            logger.warning("[explainer] Gemini returned empty response for test=%r", test)
            return None

    except Exception as exc:
        logger.error(
            "[explainer] Gemini API error for test=%r — %s: %s",
            test, type(exc).__name__, exc
        )
        return None


# GROQ GENERATION (FALLBACK)

async def _generate_with_groq(prompt: str, test: str) -> str | None:
    """Call Groq API for explanation generation (fallback)."""
    if not groq_client:
        logger.warning("[explainer] Groq client not available")
        return None

    try:
        response = await groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.4,
        )

        result_text = response.choices[0].message.content
        if result_text:
            logger.info(
                "[explainer] Groq success — test=%r, tokens=%s",
                test, getattr(response.usage, "total_tokens", "?")
            )
            return result_text
        else:
            logger.warning("[explainer] Groq returned empty response for test=%r", test)
            return None

    except Exception as exc:
        logger.error(
            "[explainer] Groq API error for test=%r — %s: %s",
            test, type(exc).__name__, exc
        )
        return None


# PROMPT ENGINEERING

def _build_prompt(
    test: str,
    value: float,
    ref_range: str,
    context: str,
    status: str,
    gender: str,
    age: int | None,
    age_group: str,
) -> str:
    """Build medical explanation prompt for LLM."""
    return f"""You are a medical assistant explaining lab results to patients.

TASK:
Explain this lab test result in plain English (3-5 sentences).
- Use simple words
- Do NOT diagnose the patient
- Do NOT make medical recommendations
- Base your explanation only on the provided data
- Be accurate and grounded

TEST INFORMATION:
- Test Name: {test}
- Patient Value: {value}
- Normal Range: {ref_range}
- Status: {status} (compared to normal range)
- What it Measures: {context}
- Patient Gender: {gender if gender else "not specified"}
- Patient Age: {age if age else "not specified"}
- Age Group: {age_group if age_group else "not specified"}

RESPONSE FORMAT:
Include these 4 points:
1. What this test measures (1 sentence)
2. What your result means relative to normal (1 sentence)
3. One possible general reason for this result (1 sentence)
4. General next step (consult doctor for diagnosis)

Remember: You are NOT diagnosing. You are EXPLAINING the numbers.
End with: "Please consult your doctor for medical advice."

Generate the explanation now:"""


# FALLBACK TEXT GENERATION

def _fallback(
    test: str,
    value: float,
    ref_range: str,
    context: str,
    status: str,
    age_group: str,
    note: str = "",
) -> str:
    """Structured text fallback when all LLM APIs are unavailable."""
    status_msg = {
        "low":     "Your value is BELOW the normal range.",
        "high":    "Your value is ABOVE the normal range.",
        "normal":  "Your value is within the normal range.",
        "unknown": "Status could not be determined.",
    }.get(status, "")

    age_note = (
        f"Note: Reference ranges can differ for {age_group} patients."
        if age_group else ""
    )

    lines = [
        f"Test: {test}",
        f"Your Value: {value}",
        f"Normal Range: {ref_range}",
        status_msg,
        context,
        age_note,
        note,
        "Please consult your doctor.",
    ]
    return "\n".join(line for line in lines if line)
