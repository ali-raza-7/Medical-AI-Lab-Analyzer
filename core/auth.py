import os
import uuid
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, RefreshToken
from .redis_client import get_redis
from fastapi.security.utils import get_authorization_scheme_param

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. "
        "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
    )
if SECRET_KEY in ("your-secret-key-change-it-in-production", "<generate-a-random-64-char-string>"):
    raise RuntimeError(
        "SECRET_KEY is using a known placeholder value. "
        "Generate a strong random key and set it in .env: "
        "python -c 'import secrets; print(secrets.token_hex(32))'"
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password[:72])

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "jti": str(uuid.uuid4()), "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "jti": str(uuid.uuid4()), "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_verification_token(user_id: str) -> str:
    return create_access_token(
        data={"sub": user_id, "purpose": "email_verify"},
        expires_delta=timedelta(hours=24),
    )

def verify_email_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "email_verify":
            return None
        return payload.get("sub")
    except JWTError:
        return None

def create_password_reset_token(user_id: str) -> str:
    return create_access_token(
        data={"sub": user_id, "purpose": "password_reset"},
        expires_delta=timedelta(hours=1),
    )


def verify_password_reset_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "password_reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None

def _cookie_secure() -> bool:
    """Use secure cookies only when not in local development."""
    val = os.getenv("COOKIE_SECURE", "").strip().lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    _frontend = os.getenv("FRONTEND_URL", "")
    if _frontend and _frontend.startswith("https://"):
        return True
    return False

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    secure = _cookie_secure()
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )

def clear_auth_cookies(response: Response):
    secure = _cookie_secure()
    response.set_cookie(key="access_token", value="", httponly=True, secure=secure, samesite="lax", max_age=0, path="/")
    response.set_cookie(key="refresh_token", value="", httponly=True, secure=secure, samesite="lax", max_age=0, path="/")

def _extract_token_from_request(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if token:
        return token
    authorization = request.headers.get("Authorization")
    if authorization:
        scheme, param = get_authorization_scheme_param(authorization)
        if scheme.lower() == "bearer":
            return param
    return None

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = _extract_token_from_request(request)
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        jti: str = payload.get("jti")
        iat: int = payload.get("iat", 0)
        if jti is None:
            raise credentials_exception
    except JWTError as exc:
        logger.warning("[auth] token validation failed: %s", exc)
        raise credentials_exception

    r = get_redis()
    if r is not None:
        if r.exists(f"blacklist:{jti}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )
        pwd_changed_at = r.get(f"pwd_changed:{user_id}")
        if pwd_changed_at and iat < int(pwd_changed_at):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password was reset. Please login again.",
            )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    return user

async def get_user_from_request(request: Request, db: Session):
    token = _extract_token_from_request(request)
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        jti: str = payload.get("jti")
        iat: int = payload.get("iat", 0)
    except JWTError as exc:
        logger.warning("[auth] JWT validation error: %s", exc)
        return None

    r = get_redis()
    if r is not None:
        if r.exists(f"blacklist:{jti}"):
            return None
        pwd_changed_at = r.get(f"pwd_changed:{user_id}")
        if pwd_changed_at and iat < int(pwd_changed_at):
            return None

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    return user
