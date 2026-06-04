import asyncio
from types import SimpleNamespace

import pytest

import medical.explainer as explainer


def test_gemini_success(monkeypatch):
    # Gemini available and returns text -> used as primary
    def fake_generate_content(prompt, generation_config=None):
        return SimpleNamespace(text="Gemini explanation")

    monkeypatch.setattr(explainer, "gemini_available", True)
    monkeypatch.setattr(explainer, "gemini_client", SimpleNamespace(generate_content=fake_generate_content))
    monkeypatch.setattr(explainer, "groq_client", None)

    res = asyncio.run(explainer.generate_explanation("Hemoglobin", 10.5, "12-16", "Measures blood", "low"))
    assert "Gemini explanation" in res


def test_gemini_failure_fallback_groq(monkeypatch):
    # Gemini raises an exception -> fallback to Groq via _generate_with_groq
    def bad_generate(prompt, generation_config=None):
        raise RuntimeError("API error")

    monkeypatch.setattr(explainer, "gemini_available", True)
    monkeypatch.setattr(explainer, "gemini_client", SimpleNamespace(generate_content=bad_generate))

    async def fake_groq(prompt, test):
        return "Groq explanation"

    monkeypatch.setattr(explainer, "_generate_with_groq", fake_groq)

    res = asyncio.run(explainer.generate_explanation("Glucose", 140, "70-99", "Measures sugar", "high"))
    assert "Groq explanation" in res
