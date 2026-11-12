from datetime import datetime, timezone
import hmac
import os
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.security import (
    AuthenticatedUser,
    create_session_tokens,
    hash_password,
    verify_password,
)
from db.database import AuthSession, User
from models.auth import LoginRequest, MessageResponse, RegisterRequest, TokenResponse


def verify_teacher_registration_key(registration_key: str | None) -> None:
    configured_key = os.getenv("TEACHER_REGISTRATION_KEY", "").strip()
    if not configured_key:
        return
    if len(configured_key.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TEACHER_REGISTRATION_KEY must contain at least 32 bytes when set",
        )
    if not registration_key or not hmac.compare_digest(registration_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing teacher registration key",
        )


def register_user(
    db: Session,
    payload: RegisterRequest,
    role: Literal["student", "teacher"],
) -> User:
    email = str(payload.email).lower().strip()
    existing_user = (
        db.query(User)
        .filter(func.lower(User.email) == email)
        .first()
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        name=payload.name,
        email=email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=role,
        status="active",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc
    db.refresh(user)
    return user


def authenticate_user(
    db: Session,
    payload: LoginRequest,
    required_role: Literal["student", "teacher"],
) -> TokenResponse:
    email = str(payload.email).lower().strip()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if (
        user is None
        or user.status != "active"
        or user.role != required_role
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email, password, or role credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return create_session_tokens(db, user)


def logout_session(db: Session, current: AuthenticatedUser) -> MessageResponse:
    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.id == current.session_id,
            AuthSession.user_id == current.user.id,
            AuthSession.revoked_at.is_(None),
        )
        .first()
    )
    if session is not None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return MessageResponse(message=f"{current.user.role.title()} session logged out successfully")
