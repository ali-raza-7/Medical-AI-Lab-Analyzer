import logging
import asyncio
from typing import List, Dict, Any
from medical.explainer import generate_explanation, gemini_available, groq_client, GEMINI_MODEL, GROQ_MODEL, gemini_client

logger = logging.getLogger(__name__)

async def compare_analyses(analysis1: Dict[str, Any], analysis2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two analysis results.
    analysis1: older analysis
    analysis2: newer analysis
    """
    results1 = {res['test_name']: res for res in analysis1.get('results', [])}
    results2 = {res['test_name']: res for res in analysis2.get('results', [])}

    improved = []
    worsened = []
    stable = []

    all_tests = set(results1.keys()) | set(results2.keys())

    for test_name in all_tests:
        r1 = results1.get(test_name)
        r2 = results2.get(test_name)

        if not r1 or not r2:
            continue
        
        # Simple logic: if status changed from abnormal to normal, it's improved.
        # If status changed from normal to abnormal, it's worsened.
        # If both abnormal, compare values if possible (requires more complex logic, let's keep it simple for now)
        
        s1 = r1.get('status')
        s2 = r2.get('status')

        if s1 == s2:
            stable.append(test_name)
        elif s1 in ['high', 'low'] and s2 == 'normal':
            improved.append(test_name)
        elif s1 == 'normal' and s2 in ['high', 'low']:
            worsened.append(test_name)
        else:
            stable.append(test_name)

    # AI Summary
    summary = await generate_comparison_summary(analysis1, analysis2, improved, worsened, stable)

    return {
        "improved": improved,
        "worsened": worsened,
        "stable": stable,
        "summary": summary
    }

async def generate_comparison_summary(analysis1, analysis2, improved, worsened, stable) -> str:
    prompt = f"""You are a medical assistant comparing two sets of lab results for a patient.
Old Analysis Date: {analysis1.get('created_at', 'Unknown')}
New Analysis Date: {analysis2.get('created_at', 'Unknown')}

Improved Biomarkers: {', '.join(improved) if improved else 'None'}
Worsened Biomarkers: {', '.join(worsened) if worsened else 'None'}
Stable Biomarkers: {', '.join(stable) if stable else 'None'}

TASK:
Provide a concise summary (3-5 sentences) of the changes between these two reports.
- Highlight significant improvements or concerns.
- Use plain English.
- Do NOT diagnose or recommend specific treatments.
- End with: "Please consult your doctor for a full clinical evaluation."

Generate the comparison summary now:"""

    if gemini_available:
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: gemini_client.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.4,
                        "max_output_tokens": 400,
                    }
                )
            )
            if response.text:
                return response.text
        except Exception as exc:
            logger.error("[comparison] Gemini failed: %s", exc)

    if groq_client:
        try:
            response = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.4,
            )
            result_text = response.choices[0].message.content
            if result_text:
                return result_text
        except Exception as exc:
            logger.error("[comparison] Groq failed: %s", exc)

    return "Comparison summary unavailable. Please review the changes in biomarkers above and consult your doctor."
