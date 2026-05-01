import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from core.config import get_settings
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from memory.memory_manager import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    is_refresh_token_active,
    revoke_refresh_token,
    store_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


def _issue_tokens(user_id: str) -> tuple[str, str]:
    settings = get_settings()
    jti = str(uuid.uuid4())
    refresh_expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    refresh_token = create_refresh_token(user_id, jti)
    store_refresh_token(user_id, jti, refresh_expires.isoformat())
    access_token = create_access_token(user_id)
    return access_token, refresh_token


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return {"user_id": user["user_id"], "email": user["email"], "name": user.get("name", "")}


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = create_user(email=str(body.email), password_hash=hash_password(body.password), name=body.name)
    access_token, refresh_token = _issue_tokens(user["user_id"])
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"user_id": user["user_id"], "email": user["email"], "name": user["name"]},
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    user = get_user_by_email(body.email)
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token, refresh_token = _issue_tokens(user["user_id"])
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"user_id": user["user_id"], "email": user["email"], "name": user.get("name", "")},
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id or not jti:
        raise HTTPException(status_code=401, detail="Invalid refresh payload")

    if not is_refresh_token_active(user_id, jti):
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    revoke_refresh_token(jti)

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token, refresh_token = _issue_tokens(user_id)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"user_id": user["user_id"], "email": user["email"], "name": user.get("name", "")},
    )


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
