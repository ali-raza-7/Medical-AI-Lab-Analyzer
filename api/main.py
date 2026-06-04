from dotenv import load_dotenv
load_dotenv()  # Must be at module level — loads .env before Groq client is created
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, Form, HTTPException, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from core.ocr import extract_text
from core.pipeline import process_lab_report
from medical.explainer import generate_explanation
from services.insights_service import LabResult, generate_grouped_insights
from medical.reference_db import get_test_definition
from core.patient_metadata import extract_patient_metadata
from core.utils import sanitize_for_json
# RAG LAYER: Initialize semantic retrieval system
from core.rag_init import initialize_rag_system
from collections import OrderedDict

# DB and Auth
from core.database import engine, Base, get_db
from core.models import User, Analysis, CreditTransaction
from core.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    get_user_from_request
)
from services.comparison_service import compare_analyses
from pydantic import BaseModel, EmailStr
import uuid
import os

# Google OAuth
try:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    google_auth_available = True
except ImportError:
    google_auth_available = False
    GOOGLE_CLIENT_ID = ""

# ──────────────────────────────────────────────────────────────────────────────
# SCHEMAS
# ──────────────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    credits: int

    class Config:
        from_attributes = True

class CompareRequest(BaseModel):
    id1: str
    id2: str

class GoogleLoginRequest(BaseModel):
    credential: str

# ──────────────────────────────────────────────────────────────────────────────
# LIFESPAN & INITIALIZATION
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG system on startup and create tables."""
    logger.info("[startup] initializing database and RAG system...")
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("[startup] database tables created")
        
        rag_ok = initialize_rag_system()
        if rag_ok:
            logger.info("[startup] RAG system initialized successfully")
        else:
            logger.warning("[startup] RAG system initialization had issues - falling back to fuzzy matching")
    except Exception as exc:
        logger.error("[startup] RAG system initialization failed: %s - continuing with fuzzy matching", exc)
    yield


app = FastAPI(title="Medical Report Explainer", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sort_key(test) -> tuple[int, str]:
    """Sort by status (abnormal first) then by name."""
    status = test.status
    rank = {"high": 0, "low": 0, "unknown": 1, "normal": 2}.get(status, 1)
    return (rank, test.test_name)


# ──────────────────────────────────────────────────────────────────────────────
# PIPELINE CACHING
# ──────────────────────────────────────────────────────────────────────────────

_pipeline_cache: OrderedDict[str, dict] = OrderedDict()
MAX_PIPELINE_CACHE = 100

def _normalize_cache_text(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def _get_pipeline_cache_key(text: str, gender: str, age: int) -> str:
    import hashlib
    normalized_text = _normalize_cache_text(text)
    key_str = f"{normalized_text}|{gender.lower()}|{age}"
    return hashlib.md5(key_str.encode()).hexdigest()

# ──────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ──────────────────────────────────────────────────────────────────────────────

async def _get_input_text(file: UploadFile | None, text: str | None) -> str:
    """Handle text extraction from file or raw text input."""
    logger.info("[_get_input_text] Received - file: %s, text length: %d", 
                file.filename if file else None, len(text) if text else 0)
    
    if file and file.filename == "":
        file = None
    if text and text.strip() == "":
        text = None

    if not file and not text:
        logger.warning("[_get_input_text] No input provided (both file and text are None/empty)")
        raise HTTPException(
            status_code=400,
            detail="Please provide file or text input."
        )

    try:
        if text:
            logger.info("[_get_input_text] Using manual text input (%d chars) — skipping OCR", len(text))
            raw_text = text
        elif file:
            logger.info("[_get_input_text] Using OCR from file: %s", file.filename)
            raw_text = await extract_text(file)
        else:
            # Should not reach here (caught above), but guard anyway
            raw_text = None
        
        if not raw_text or not raw_text.strip():
            logger.warning("[_get_input_text] Raw text is empty after processing")
            raise ValueError("No text content found")
        
        logger.info("[_get_input_text] Success: %d chars extracted", len(raw_text))
        return raw_text
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[_get_input_text] extraction failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Invalid image file or OCR extraction failed."
        )

async def _generate_explanations_async(resolved_tests, gender: str, age: int):
    """Generate LLM explanations for abnormal results in parallel."""
    explanations_dict = {}
    explanation_tasks = []
    
    for test in resolved_tests:
        if test.status in ("high", "low"):
            td = get_test_definition(test.resolved_key) if test.resolved_key else None
            context = td.what_it_measures if td else "Test not recognized from the report text."
            rr = test.reference_range
            lo = rr.low if rr.low is not None else "?"
            hi = rr.high if rr.high is not None else "?"
            expl_range = f"{lo} - {hi} {rr.unit}".strip()

            coro = generate_explanation(
                test.test_name,
                test.value,
                expl_range,
                context,
                test.status,
                gender=gender,
                age=age,
                age_group="adult",
            )
            explanation_tasks.append((test.test_name, coro))

    if explanation_tasks:
        coros = [coro for _, coro in explanation_tasks]
        results_expl = await asyncio.gather(*coros, return_exceptions=True)
        for (test_name, _), expl in zip(explanation_tasks, results_expl):
            if isinstance(expl, Exception):
                logger.error("[analyze] Explanation generation failed for %r: %s", test_name, expl)
                explanations_dict[test_name] = "Explanation failed to generate."
            else:
                explanations_dict[test_name] = expl
                
    return explanations_dict

def _build_analyze_response(
    resolved_tests, 
    tracker, 
    detected_gender: str, 
    detected_age: int, 
    metadata: dict, 
    explanations_dict: dict
) -> dict:
    """Construct and sort the final JSON-serializable response."""
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
        "patient": {
            "gender": detected_gender,
            "age": detected_age,
        },
        "patient_detected": {
            "gender": metadata.get("gender"),
            "age": metadata.get("age"),
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
                "explanation": explanations_dict.get(t.test_name) or t.to_dict()["explanation"]
            }
            for t in resolved_tests_sorted
        ],
        "disclaimer": "This is not a medical diagnosis.",
    }
    return sanitize_for_json(response)


@app.post("/signup", response_model=UserOut)
async def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    # Validate email
    if not user_in.email or not user_in.email.strip():
        raise HTTPException(status_code=400, detail="Email cannot be empty")
    if "@" not in user_in.email or "." not in user_in.email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Validate password
    if not user_in.password or len(user_in.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = get_password_hash(user_in.password)
    new_user = User(email=user_in.email, password_hash=hashed_pw, credits=5)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info("[signup] New user created: %s", user_in.email)
    return new_user

@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Validate input
    if not form_data.username or not form_data.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        logger.warning("[login] Failed login attempt: user not found for email %s", form_data.username)
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not verify_password(form_data.password, user.password_hash):
        logger.warning("[login] Failed login attempt: wrong password for user %s", form_data.username)
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    logger.info("[login] Successful login for user %s", user.email)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/auth/google", response_model=Token)
async def google_login(req: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Verify a Google ID token and return a JWT for the user."""
    if not google_auth_available:
        raise HTTPException(status_code=501, detail="Google authentication is not configured on this server.")
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GOOGLE_CLIENT_ID not set in environment.")

    try:
        idinfo = google_id_token.verify_oauth2_token(
            req.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        email = idinfo.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google token missing email claim.")
    except ValueError as exc:
        logger.warning("[auth/google] Invalid Google token: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid Google credentials.")

    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Create new user with a random password hash (they login via Google)
        random_pw_hash = get_password_hash(str(uuid.uuid4()))
        user = User(email=email, password_hash=random_pw_hash, credits=5)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("[auth/google] Created new Google user: %s", email)
    else:
        logger.info("[auth/google] Existing user logged in via Google: %s", email)

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/history")
async def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = db.query(Analysis).filter(Analysis.user_id == current_user.id).order_by(Analysis.created_at.desc()).all()
    # Explicitly serialize to list of dicts to avoid ORM serialization issues
    return [
        {
            "id": a.id,
            "file_name": a.file_name,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "results_json": a.results_json,
        }
        for a in analyses
    ]

@app.post("/compare")
async def compare(req: CompareRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a1 = db.query(Analysis).filter(Analysis.id == req.id1, Analysis.user_id == current_user.id).first()
    a2 = db.query(Analysis).filter(Analysis.id == req.id2, Analysis.user_id == current_user.id).first()
    
    if not a1 or not a2:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    comparison = await compare_analyses(a1.results_json, a2.results_json)
    return comparison

@app.post("/analyze")
async def analyze(
    request: Request,
    response: Response,
    file: UploadFile = None,
    text: str = Form(None),
    gender: str = Form("male"),
    age: int = Form(30),
    db: Session = Depends(get_db)
):
    logger.info("[analyze] request start: gender=%s age=%d file=%s text_length=%d", 
                gender, age, 
                f"UploadFile({getattr(file, 'filename', 'unknown')})" if file else "None",
                len(text) if text else 0)
    
    # Validate age
    if age < 1 or age > 150:
        logger.warning("[analyze] Invalid age provided: %d", age)
        raise HTTPException(status_code=400, detail="Age must be between 1 and 150 years old")
    
    # Validate gender
    if gender.lower() not in ("male", "female"):
        logger.warning("[analyze] Invalid gender provided: %s", gender)
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

    # Auth and Credit Check
    user = await get_user_from_request(request, db)
    
    # Anonymous flow
    session_id = request.cookies.get("session_id")
    if not user:
        logger.info("[analyze] anonymous user detected")
        if not session_id:
            session_id = str(uuid.uuid4())
            response.set_cookie(key="session_id", value=session_id, max_age=3600*24*7, httponly=True)
            logger.info("[analyze] new session_id created: %s", session_id)
        
        # Check if this session has already used its free analysis
        free_used = db.query(Analysis).filter(Analysis.user_id == None, Analysis.file_name == session_id).first()
        if free_used:
            logger.warning("[analyze] 403 Forbidden: free limit reached for session %s", session_id)
            raise HTTPException(status_code=403, detail="Free analysis used. Please sign up to continue.")
    else:
        logger.info("[analyze] authenticated user: %s (credits: %d)", user.email, user.credits)
        if user.credits <= 0:
            logger.warning("[analyze] 403 Forbidden: insufficient credits for user %s", user.email)
            raise HTTPException(status_code=403, detail="Insufficient credits. Please buy more.")

    raw_text = await _get_input_text(file, text)

    # Try to auto-detect patient metadata from raw OCR text
    metadata = extract_patient_metadata(raw_text)
    logger.info("[analyze] detected metadata: %s", metadata)
    detected_gender = metadata.get("gender") or gender
    detected_age = metadata.get("age") or age

    # Check cache (use detected values for cache key)
    cache_key = _get_pipeline_cache_key(raw_text, detected_gender, detected_age)
    if cache_key in _pipeline_cache:
        logger.info("[analyze] cache hit for request")
        sanitized = _pipeline_cache[cache_key]
    else:
        try:
            logger.info("[analyze] ===== PIPELINE DEBUG TRACE =====")
            logger.info("[analyze] 1. RAW TEXT: %d chars", len(raw_text))
            logger.info("[analyze] RAW TEXT PREVIEW: %s", raw_text[:200] if len(raw_text) > 200 else raw_text)
            
            resolved_tests, tracker = process_lab_report(raw_text, gender=detected_gender, age=detected_age)
            
            logger.info("[analyze] 2. PARSED TESTS: %d total_parsed (from tracker)", tracker.total_parsed)
            logger.info("[analyze] 3. RESOLVED TESTS: %d resolved, %d unresolved, %d garbage_filtered", 
                       tracker.resolved, tracker.unresolved, tracker.garbage_filtered)
            logger.info("[analyze] 4. FINAL OUTPUT: %d tests in resolved_tests list", len(resolved_tests))
            logger.info("[analyze] 5. TEST DETAILS:")
            for idx, test in enumerate(resolved_tests, 1):
                logger.info("[analyze]    %d. %s (key=%s, status=%s, confidence=%.2f)", 
                           idx, test.test_name, test.resolved_key, test.status, test.confidence)
            logger.info("[analyze] ===== END PIPELINE TRACE =====")
        except AssertionError as exc:
            logger.critical("[analyze] Pipeline integrity check failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Internal pipeline integrity error."
            )
        except Exception as exc:
            logger.error("[analyze] Pipeline failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Report analysis failed."
            )

        if tracker.total_parsed == 0:
            raise HTTPException(
                status_code=422,
                detail="No lab results found in input."
            )

        explanations_dict = await _generate_explanations_async(resolved_tests, detected_gender, detected_age)
        
        sanitized = _build_analyze_response(
            resolved_tests, tracker, detected_gender, detected_age, metadata, explanations_dict
        )

        # Store in cache
        _pipeline_cache[cache_key] = sanitized
        _pipeline_cache.move_to_end(cache_key)
        if len(_pipeline_cache) > MAX_PIPELINE_CACHE:
            _pipeline_cache.popitem(last=False)

    # Save to history and deduct credits
    filename = file.filename if (file and file.filename) else "text_input"
    if not user:
        # Use session_id as placeholder for file_name to track free use
        analysis = Analysis(user_id=None, file_name=session_id, results_json=sanitized)
    else:
        analysis = Analysis(user_id=user.id, file_name=filename, results_json=sanitized)
        user.credits -= 1
        db.add(CreditTransaction(user_id=user.id, amount=-1, description=f"Analysis: {filename}"))
    
    db.add(analysis)
    db.commit()

    logger.info("[analyze] Request successfully processed.")
    return sanitized
