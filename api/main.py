from dotenv import load_dotenv
load_dotenv()
import os
import logging
import structlog

if not os.getenv("GROQ_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError(
        "No LLM API key configured. Set GROQ_API_KEY or GEMINI_API_KEY in .env"
    )
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, Form, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import asyncio
import secrets
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from core.rag_init import initialize_rag_system
from core.tasks import perform_analysis
from core.celery_app import celery_app
from celery.result import AsyncResult

from core.database import get_db, engine, Base
from core.models import User, Analysis, RefreshToken
from core.redis_client import get_redis
from core.email import send_verification_email, send_password_reset_email
from core.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_user_from_request,
    create_verification_token,
    verify_email_token,
    create_password_reset_token,
    verify_password_reset_token,
    set_auth_cookies,
    clear_auth_cookies,
    SECRET_KEY, ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from services.comparison_service import compare_analyses
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
import uuid
import socket
import redis
from datetime import datetime, timedelta

try:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    google_auth_available = True
except ImportError:
    google_auth_available = False
    GOOGLE_CLIENT_ID = ""

_nonce_store: dict[str, datetime] = {}
_NONCE_TTL_SECONDS = 300

def _purge_expired_nonces():
    now = datetime.utcnow()
    expired = [k for k, v in _nonce_store.items() if now - v > timedelta(seconds=_NONCE_TTL_SECONDS)]
    for k in expired:
        _nonce_store.pop(k, None)

limiter = Limiter(key_func=get_remote_address, default_limits=[])

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "image/png", "image/jpeg", "image/jpg", "image/webp", "image/bmp",
    "image/tiff", "image/tif",
    "application/pdf",
    "image/heic", "image/heif",
}
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp",
    ".tiff", ".tif",
    ".pdf",
    ".heic", ".heif",
}
MAX_TEXT_LENGTH = 50000
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

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
    is_verified: bool

    class Config:
        from_attributes = True

class CompareRequest(BaseModel):
    id1: str
    id2: str

class GoogleLoginRequest(BaseModel):
    credential: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


def _validate_password(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if len(password) > 128:
        return "Password must be at most 128 characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain an uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain a lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain a number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", password):
        return "Password must contain a special character"
    return None

def _validate_file_upload(file: UploadFile, contents: bytes) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="File MIME type is missing or not allowed")
    if ext == ".pdf" and contents[:4] != b"%PDF":
        raise HTTPException(status_code=400, detail="Invalid or corrupted PDF file")

def _check_brute_force(user: User) -> None:
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() // 60)
        raise HTTPException(status_code=429, detail=f"Account locked. Try again in {remaining} minutes.")

def _record_failed_login(db: Session, user: User) -> None:
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
        if not user.locked_until or user.locked_until <= datetime.utcnow():
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
    db.commit()

def _reset_login_attempts(db: Session, user: User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://accounts.google.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "frame-src https://accounts.google.com; "
            "connect-src 'self'"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


CSRF_EXEMPT_PATHS = {"/analyze", "/upload", "/login", "/signup", "/refresh"}

class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        if request.url.path in CSRF_EXEMPT_PATHS:
            return await call_next(request)

        from urllib.parse import urlparse
        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")
        source = origin or referer or ""

        if source:
            netloc = urlparse(source).netloc
            if netloc:
                ok = bool(re.match(r"^(localhost|127\.0\.0\.1)(:\d+)?$", netloc))
                if _frontend_url:
                    parsed = urlparse(_frontend_url)
                    if parsed.netloc:
                        ok = ok or (netloc == parsed.netloc)
                if not ok:
                    return JSONResponse(status_code=403, content={"detail": "CSRF check failed: invalid origin"})
        else:
            x_requested = request.headers.get("X-Requested-With", "")
            if x_requested != "XMLHttpRequest":
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF check failed: missing Origin/Referer and X-Requested-With"},
                )

        return await call_next(request)


def _check_workers_online() -> bool:
    try:
        inspect = celery_app.control.inspect()
        return inspect.ping() is not None
    except Exception:
        return False


def _check_redis_reachable() -> bool:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(redis_url, socket_connect_timeout=3)
        r.ping()
        r.close()
        return True
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[startup] initializing database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("[startup] database tables ready")
    except Exception as exc:
        logger.warning("[startup] could not create tables: %s", exc)

    logger.info("[startup] initializing RAG system...")
    try:
        rag_ok = initialize_rag_system()
        if rag_ok:
            logger.info("[startup] RAG system initialized successfully")
        else:
            logger.warning("[startup] RAG system initialization had issues - falling back to fuzzy matching")
    except Exception as exc:
        logger.error("[startup] initialization failed: %s", exc)

    redis_ok = _check_redis_reachable()
    if redis_ok:
        logger.info("[startup] Redis is reachable")
    else:
        logger.warning("[startup] Redis unreachable — Celery tasks will fail with 503. "
                       "Start Redis or set REDIS_URL in .env.")
    yield


app = FastAPI(title="Medical Report Explainer", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SecurityHeadersMiddleware)

_frontend_url = os.getenv("FRONTEND_URL", "")
_frontend_login_url = (_frontend_url if _frontend_url else "https://medical-ai-lab-analyzer.vercel.app") + "/login"
_allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://medical-ai-lab-analyzer.vercel.app",
]
if _frontend_url and _frontend_url not in _allowed_origins:
    _allowed_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://medical-ai-lab-analyzer\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CSRFMiddleware)


async def _read_and_validate_input(file: UploadFile | None, text: str | None):
    """Validate input and return (file_content, file_filename, text_content)."""
    if file and file.filename == "":
        file = None
    if text and text.strip() == "":
        text = None

    if not file and not text:
        raise HTTPException(status_code=400, detail="Please provide file or text input.")

    if text:
        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(status_code=413, detail=f"Text input too large (max {MAX_TEXT_LENGTH} chars)")
        return None, None, text

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_FILE_SIZE // (1024*1024)}MB)")
    _validate_file_upload(file, contents)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext == ".pdf":
        return contents, file.filename, None

    if ext in (".heic", ".heif"):
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            raise HTTPException(status_code=501, detail="HEIC/HEIF support not available on this server")

    try:
        from PIL import Image
        import io
        Image.open(io.BytesIO(contents)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or corrupted image file")
    return contents, file.filename, None


async def _poll_task_result(task, timeout: int = 300, poll_interval: float = 0.5):
    """Poll a Celery ``AsyncResult`` until ready, then return the data payload."""
    loop = asyncio.get_event_loop()
    elapsed = 0.0

    while elapsed < timeout:
        ready = await loop.run_in_executor(None, task.ready)
        if ready:
            result = await loop.run_in_executor(None, task.get, 1)
            if result.get("status") == "error":
                raise HTTPException(
                    status_code=result.get("code", 500),
                    detail=result.get("detail", "Analysis failed"),
                )
            return result["data"]
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    task.revoke()
    raise HTTPException(status_code=504, detail="Analysis timed out.")


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/signup")
@limiter.limit("3/minute")
async def signup(request: Request, user_in: UserCreate, bg: BackgroundTasks, db: Session = Depends(get_db)):
    password_err = _validate_password(user_in.password)
    if password_err:
        raise HTTPException(status_code=400, detail=password_err)

    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        logger.warning("signup: duplicate email", email=user_in.email)
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed_pw = get_password_hash(user_in.password)
    new_user = User(email=user_in.email, password_hash=hashed_pw, credits=5, is_verified=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    verification_token = create_verification_token(str(new_user.id))
    bg.add_task(send_verification_email, new_user.email, verification_token)

    logger.info("user created (unverified)", email=user_in.email)
    return {"message": "Account created. Please check your email to verify."}


@app.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if not form_data.username or not form_data.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user = db.query(User).filter(User.email == form_data.username).first()

    if user:
        _check_brute_force(user)

    if not user or not verify_password(form_data.password, user.password_hash):
        if user:
            _record_failed_login(db, user)
            logger.warning("failed login attempt", email=form_data.username)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    _reset_login_attempts(db, user)

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email first")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token_str = create_refresh_token(data={"sub": str(user.id)})

    decoded = jwt.decode(refresh_token_str, SECRET_KEY, algorithms=[ALGORITHM])
    db_refresh = RefreshToken(user_id=user.id, token_jti=decoded["jti"], expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    db.add(db_refresh)
    db.commit()

    set_auth_cookies(response, access_token, refresh_token_str)
    logger.info("successful login", email=user.email)
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token_str}


@app.post("/refresh")
@limiter.limit("5/minute")
async def refresh_token(request: Request, response: Response, req: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    stored = db.query(RefreshToken).filter(RefreshToken.token_jti == payload["jti"], RefreshToken.revoked == False).first()
    if not stored or stored.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    stored.revoked = True
    db.commit()

    new_access = create_access_token(data={"sub": payload["sub"]})
    new_refresh = create_refresh_token(data={"sub": payload["sub"]})

    decoded = jwt.decode(new_refresh, SECRET_KEY, algorithms=[ALGORITHM])
    db_refresh = RefreshToken(user_id=payload["sub"], token_jti=decoded["jti"], expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    db.add(db_refresh)
    db.commit()

    set_auth_cookies(response, new_access, new_refresh)
    return {"access_token": new_access, "token_type": "bearer", "refresh_token": new_refresh}


@app.post("/logout")
@limiter.limit("10/minute")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            db.query(RefreshToken).filter(RefreshToken.token_jti == payload["jti"]).update({"revoked": True})
            db.commit()
        except JWTError:
            pass

    access_token = request.cookies.get("access_token")
    if access_token:
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            exp = payload.get("exp", 0)
            now = int(datetime.utcnow().timestamp())
            expires_in = exp - now
            if jti and expires_in > 0:
                r = get_redis()
                if r is not None:
                    r.setex(f"blacklist:{jti}", expires_in, "1")
        except JWTError:
            pass

    clear_auth_cookies(response)
    return {"message": "Logged out"}


@app.get("/me", response_model=UserOut)
@limiter.limit("20/minute")
async def get_me(request: Request, current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/verify-email")
@limiter.limit("10/minute")
async def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    user_id = verify_email_token(token)
    if not user_id:
        return RedirectResponse(url=f"{_frontend_login_url}?verified=fail", status_code=303)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url=f"{_frontend_login_url}?verified=fail", status_code=303)

    if user.is_verified:
        return RedirectResponse(url=f"{_frontend_login_url}?verified=already", status_code=303)

    user.is_verified = True
    db.commit()
    logger.info("email verified", email=user.email)
    return RedirectResponse(url=f"{_frontend_login_url}?verified=success", status_code=303)


@app.post("/auth/google", response_model=Token)
@limiter.limit("5/minute")
async def google_login(request: Request, response: Response, req: GoogleLoginRequest, db: Session = Depends(get_db)):
    if not google_auth_available:
        raise HTTPException(status_code=501, detail="Google authentication is not configured on this server.")
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GOOGLE_CLIENT_ID not set in environment.")

    try:
        idinfo = google_id_token.verify_oauth2_token(req.credential, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google token missing email claim.")
        if not idinfo.get("email_verified"):
            raise HTTPException(status_code=403, detail="Google email not verified.")
    except ValueError as exc:
        logger.warning("invalid Google token", error=str(exc))
        raise HTTPException(status_code=401, detail="Invalid Google credentials.")

    _purge_expired_nonces()
    google_nonce = idinfo.get("nonce")
    if google_nonce:
        if google_nonce not in _nonce_store:
            raise HTTPException(status_code=401, detail="Invalid or expired nonce.")
        del _nonce_store[google_nonce]
    else:
        logger.warning("Google token missing nonce")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        random_pw = secrets.token_hex(32)[:32]
        random_pw_hash = get_password_hash(random_pw)
        user = User(email=email, password_hash=random_pw_hash, credits=5, is_verified=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("created new Google user", email=email)
    else:
        if not user.is_verified:
            user.is_verified = True
            db.commit()
            logger.info("marked existing user as verified via Google", email=email)
        logger.info("existing user logged in via Google", email=email)

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token_str = create_refresh_token(data={"sub": str(user.id)})

    decoded = jwt.decode(refresh_token_str, SECRET_KEY, algorithms=[ALGORITHM])
    db_refresh = RefreshToken(user_id=user.id, token_jti=decoded["jti"], expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    db.add(db_refresh)
    db.commit()

    set_auth_cookies(response, access_token, refresh_token_str)

    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token_str}


@app.get("/auth/nonce")
@limiter.limit("30/minute")
async def get_nonce(request: Request):
    _purge_expired_nonces()
    nonce = str(uuid.uuid4())
    _nonce_store[nonce] = datetime.utcnow()
    return {"nonce": nonce}


@app.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, req: ForgotPasswordRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if user:
        reset_token = create_password_reset_token(str(user.id))
        bg.add_task(send_password_reset_email, user.email, reset_token)
        logger.info("password reset email sent", email=user.email)
    else:
        logger.info("password reset requested for unknown email", email=req.email)
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@app.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, req: ResetPasswordRequest, db: Session = Depends(get_db)):
    password_err = _validate_password(req.new_password)
    if password_err:
        raise HTTPException(status_code=400, detail=password_err)

    user_id = verify_password_reset_token(req.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user.password_hash = get_password_hash(req.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revoked == False).update({"revoked": True})
    db.commit()

    r = get_redis()
    if r is not None:
        r.set(f"pwd_changed:{user.id}", int(datetime.utcnow().timestamp()))

    logger.info("password reset completed", email=user.email)
    return {"message": "Password has been reset successfully."}


@app.get("/history")
@limiter.limit("30/minute")
async def get_history(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = db.query(Analysis).filter(Analysis.user_id == current_user.id).order_by(Analysis.created_at.desc()).all()
    return [
        {"id": a.id, "file_name": a.file_name, "created_at": a.created_at.isoformat() if a.created_at else None, "results_json": a.results_json}
        for a in analyses
    ]


@app.post("/compare")
@limiter.limit("20/minute")
async def compare(request: Request, req: CompareRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a1 = db.query(Analysis).filter(Analysis.id == req.id1, Analysis.user_id == current_user.id).first()
    a2 = db.query(Analysis).filter(Analysis.id == req.id2, Analysis.user_id == current_user.id).first()

    if not a1 or not a2:
        raise HTTPException(status_code=404, detail="Analysis not found")

    comparison = await compare_analyses(a1.results_json, a2.results_json)
    return comparison


@app.post("/analyze")
@limiter.limit("10/minute")
async def analyze(
    request: Request,
    response: Response,
    bg: BackgroundTasks,
    file: UploadFile = None,
    text: str = Form(None),
    gender: str = Form("male"),
    age: int = Form(30),
    db: Session = Depends(get_db)
):
    if age < 1 or age > 150:
        raise HTTPException(status_code=400, detail="Age must be between 1 and 150 years old")
    if gender.lower() not in ("male", "female"):
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

    user = await get_user_from_request(request, db)

    session_id = request.cookies.get("session_id")
    if not user:
        if not session_id:
            session_id = str(uuid.uuid4())
            response.set_cookie(key="session_id", value=session_id, max_age=3600*24*7, httponly=True, samesite="lax")
        free_used = db.query(Analysis).filter(Analysis.user_id == None, Analysis.file_name == session_id).first()
        if free_used:
            raise HTTPException(status_code=403, detail="Free analysis used. Please sign up to continue.")
    else:
        if user.credits <= 0:
            raise HTTPException(status_code=403, detail="Insufficient credits. Please buy more.")

    file_content, file_filename, text_content = await _read_and_validate_input(file, text)

    logger.info("[analyze] enqueuing analysis task (user=%s, gender=%s, age=%d)",
                str(user.id) if user else "anonymous", gender, age)

    try:
        task = perform_analysis.delay(
            file_content=file_content,
            file_filename=file_filename,
            text=text_content,
            gender=gender.lower(),
            age=age,
            user_id=str(user.id) if user else None,
            session_id=session_id,
        )
    except Exception as exc:
        logger.error("[analyze] failed to enqueue Celery task — Redis broker unreachable?", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail="Analysis service temporarily unavailable. Please try again later.",
        )

    return {"task_id": task.id}


@app.get("/status/{task_id}")
@limiter.limit("30/minute")
async def get_task_status(request: Request, task_id: str):
    async_result = AsyncResult(task_id, app=celery_app)
    state = async_result.state

    body: dict = {}
    if state == "PENDING":
        workers_online = _check_workers_online()
        if not workers_online:
            body = {"status": "not_found", "error": "Worker may be offline"}
        else:
            body = {"status": "pending", "progress": "Waiting in queue..."}
    elif state == "STARTED":
        body = {"status": "processing", "progress": "Analyzing your file..."}
    elif state == "SUCCESS":
        result = async_result.get()
        if result.get("status") == "error":
            body = {"status": "failed", "error": result.get("detail", "Analysis failed")}
        else:
            body = {"status": "complete", "result": result.get("data")}
    elif state == "FAILURE":
        body = {"status": "failed", "error": "Analysis failed. Please try again."}
    else:
        body = {"status": state.lower(), "progress": state.lower()}

    resp = JSONResponse(content=body)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.get("/worker/health")
@limiter.limit("10/minute")
async def worker_health(request: Request):
    online = _check_workers_online()
    if online:
        return {"status": "online", "message": "Worker is running"}
    return {"status": "offline", "message": "Worker not running"}


@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)
    index_path = "/app/frontend/dist/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="Frontend not built")
