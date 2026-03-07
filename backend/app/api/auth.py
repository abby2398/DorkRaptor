"""
Auth endpoints: register, login, Google OAuth, me
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.auth import hash_password, verify_password, create_access_token, get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    # ID token from Google Sign-In
    id_token: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _ensure_first_admin(db: AsyncSession) -> bool:
    """Returns True if no users exist yet (first registration becomes admin)."""
    count = await db.scalar(select(func.count(User.id)))
    return (count or 0) == 0


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    is_first = await _ensure_first_admin(db)

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role="admin" if is_first else "user",
        provider="local",
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), user.role)
    return {"access_token": token, "user": user.to_dict()}


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(str(user.id), user.role)
    return {"access_token": token, "user": user.to_dict()}


@router.post("/google", response_model=AuthResponse)
async def google_auth(data: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Verify Google ID token and sign in / register user."""
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        id_info = google_id_token.verify_oauth2_token(
            data.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    google_sub = id_info["sub"]
    email = id_info.get("email", "")
    full_name = id_info.get("name")
    avatar_url = id_info.get("picture")

    # Find by provider_id first, then email
    result = await db.execute(select(User).where(User.provider_id == google_sub))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user:
        # Update OAuth fields
        user.provider = "google"
        user.provider_id = google_sub
        if avatar_url:
            user.avatar_url = avatar_url
        user.last_login = datetime.now(timezone.utc)
    else:
        is_first = await _ensure_first_admin(db)
        user = User(
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            provider="google",
            provider_id=google_sub,
            role="admin" if is_first else "user",
            is_verified=True,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), user.role)
    return {"access_token": token, "user": user.to_dict()}


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return current_user.to_dict()
