from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import User, AuthToken

logger = logging.getLogger(__name__)
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$")
        return hash_password(password, salt) == stored
    except ValueError:
        return False


def _cleanup_expired_tokens(db: Session) -> None:
    db.query(AuthToken).filter(AuthToken.expires_at < datetime.utcnow()).delete()
    db.commit()


def create_token(db: Session, user_id: int) -> str:
    _cleanup_expired_tokens(db)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    auth_token = AuthToken(token=token, user_id=user_id, expires_at=expires_at)
    db.add(auth_token)
    db.commit()
    return token


def _get_user_id_from_token(db: Session, token: str) -> Optional[int]:
    auth_token = db.query(AuthToken).filter(AuthToken.token == token).first()
    if auth_token is None:
        return None
    if auth_token.is_expired():
        db.delete(auth_token)
        db.commit()
        return None
    return auth_token.user_id


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    user_id = _get_user_id_from_token(db, token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UpdateUserRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=6)


@auth_router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    from src.models.playlist import Playlist as PlaylistModel

    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    password_hash = hash_password(req.password)
    user = User(username=req.username, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)

    liked_playlist = PlaylistModel(user_id=user.id, name="我喜欢的音乐", is_system=True)
    db.add(liked_playlist)
    db.commit()

    token = create_token(db, user.id)
    logger.info(f"[AUTH] User registered: {user.username}")
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id, username=user.username, created_at=user.created_at
        ),
    )


@auth_router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == req.username).first()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(db, user.id)
    logger.info(f"[AUTH] User logged in: {user.username}")
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id, username=user.username, created_at=user.created_at
        ),
    )


class LogoutResponse(BaseModel):
    ok: bool = True
    message: str = "Logged out"


@auth_router.post("/logout", response_model=LogoutResponse)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    token = credentials.credentials
    auth_token = db.query(AuthToken).filter(AuthToken.token == token).first()
    if auth_token is not None:
        db.delete(auth_token)
        db.commit()
    return LogoutResponse()


@auth_router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        created_at=current_user.created_at,
    )


@auth_router.put("/me", response_model=UserResponse)
def update_me(
    req: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    if req.username is not None:
        existing = (
            db.query(User)
            .filter(User.username == req.username, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = req.username

    if req.password is not None:
        current_user.password_hash = hash_password(req.password)

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    logger.info(f"[AUTH] User updated: {current_user.username}")
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        created_at=current_user.created_at,
    )
