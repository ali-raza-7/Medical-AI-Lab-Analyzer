"""
Standalone Groq API key verification script.

Run this BEFORE starting the backend to confirm your key works:
    ./myenv/bin/python test_groq_key.py

Exit codes:
    0 = API key valid and working
    1 = API key missing, placeholder, or rejected by Groq
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[1] ✓ python-dotenv loaded .env successfully")
except ImportError:
    print("[1] ✗ python-dotenv not installed — run: pip install python-dotenv")
    sys.exit(1)

api_key = os.getenv("GROQ_API_KEY", "").strip()

if not api_key:
    print("[2] ✗ GROQ_API_KEY is missing from .env")
    print("    → Add this line to your .env file:")
    print("      GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    sys.exit(1)

if api_key == "your_groq_api_key_here":
    print("[2] ✗ GROQ_API_KEY is still the placeholder value!")
    print("    → Get your real key from: https://console.groq.com/keys")
    print("    → Replace the placeholder in .env with your actual key")
    sys.exit(1)

if not api_key.startswith("gsk_"):
    print(f"[2] ⚠ GROQ_API_KEY does not start with 'gsk_' — may be invalid")
    print(f"    → Value starts with: {api_key[:10]}...")
else:
    print(f"[2] ✓ GROQ_API_KEY found — starts with: {api_key[:8]}... (length: {len(api_key)})")

try:
    from groq import Groq
    client = Groq(api_key=api_key)
    print("[3] ✓ Groq client initialized")
except ImportError:
    print("[3] ✗ groq package not installed — run: pip install groq")
    sys.exit(1)
except Exception as e:
    print(f"[3] ✗ Groq client initialization failed: {e}")
    sys.exit(1)

print("[4] Making test API call to Groq (model: llama-3.3-70b-versatile)...")
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": "Say exactly: GROQ_API_WORKING. Nothing else."
        }],
        max_tokens=20,
        temperature=0,
    )
    reply = response.choices[0].message.content.strip()
    tokens = getattr(response.usage, "total_tokens", "?")
    print(f"[4] ✓ API call successful!")
    print(f"    → Response: {reply}")
    print(f"    → Tokens used: {tokens}")
    print(f"    → Model: {response.model}")

except Exception as e:
    print(f"[4] ✗ API call FAILED: {type(e).__name__}: {e}")
    print()
    err_str = str(e).lower()
    if "401" in err_str or "invalid" in err_str or "authentication" in err_str:
        print("    → CAUSE: Invalid API key. Check your key at https://console.groq.com/keys")
    elif "429" in err_str or "rate" in err_str:
        print("    → CAUSE: Rate limit hit. Wait a moment and try again.")
    elif "404" in err_str or "model" in err_str:
        print("    → CAUSE: Model not found. Check model name spelling.")
    elif "connection" in err_str or "timeout" in err_str:
        print("    → CAUSE: Network error. Check your internet connection.")
    else:
        print("    → Check https://console.groq.com for service status")
    sys.exit(1)

print()
print("=" * 55)
print("  ✅ ALL CHECKS PASSED — Groq API is working correctly!")
print("=" * 55)
print()
print("You can now start the backend:")
print("  ./myenv/bin/python -m uvicorn main:app --reload")
print()
print("And the frontend:")
print("  ./myenv/bin/streamlit run app.py")
