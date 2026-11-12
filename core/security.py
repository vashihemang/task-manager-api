import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from dotenv import load_dotenv

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from pwdlib.exceptions import HasherNotAvailable
from sqlalchemy.orm import Session

from core.config import get_db
from db.database import AuthSession, User
from models.auth import TokenResponse

try:
    password_hasher = PasswordHash.recommended()
except HasherNotAvailable:
    password_hasher = None

bearer_scheme = HTTPBearer(auto_error=False)

load_dotenv()


@dataclass(frozen=True)
class AuthenticatedUser:
    user: User
    session_id: int


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 bytes")
    return secret


def _positive_int_setting(name: str, default: int) -> int:
    value = os.getenv(name, str(default))
    try:
        result = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer") from exc
    if result <= 0:
        raise RuntimeError(f"{name} must be a positive integer")
    return result


def validate_security_settings() -> None:
    _jwt_secret()
    _positive_int_setting("ACCESS_TOKEN_MINUTES", 15)
    _positive_int_setting("REFRESH_TOKEN_DAYS", 7)


def hash_password(password: str) -> str:
    if password_hasher is not None:
        return password_hasher.hash(password)
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        return False
    if password_hash.startswith("pbkdf2_sha256$"):
        try:
            _, salt, expected = password_hash.split("$", 2)
        except ValueError:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        ).hex()
        return hmac.compare_digest(actual, expected)
    return password_hasher is not None and password_hasher.verify(password, password_hash)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _encode_token(
    *,
    user_id: int,
    role: str,
    session_id: int,
    token_type: str,
    expires_at: datetime,
    now: datetime,
) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "sid": session_id,
            "type": token_type,
            "iat": now,
            "exp": expires_at,
            "jti": secrets.token_urlsafe(16),
        },
        _jwt_secret(),
        algorithm="HS256",
    )


def _new_token_pair(
    user_id: int,
    role: str,
    session_id: int,
    refresh_expires_at: datetime,
    now: datetime,
) -> TokenResponse:
    access_expires_at = now + timedelta(
        minutes=_positive_int_setting("ACCESS_TOKEN_MINUTES", 15)
    )
    refresh_token = _encode_token(
        user_id=user_id,
        role=role,
        session_id=session_id,
        token_type="refresh",
        expires_at=refresh_expires_at,
        now=now,
    )
    access_token = _encode_token(
        user_id=user_id,
        role=role,
        session_id=session_id,
        token_type="access",
        expires_at=access_expires_at,
        now=now,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int((access_expires_at - now).total_seconds()),
        role=role,
    )


def create_session_tokens(db: Session, user: User) -> TokenResponse:
    now = datetime.now(timezone.utc)
    refresh_expires_at = now + timedelta(
        days=_positive_int_setting("REFRESH_TOKEN_DAYS", 7)
    )
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=secrets.token_hex(32),
        expires_at=refresh_expires_at,
    )
    db.add(session)
    db.flush()

    tokens = _new_token_pair(user.id, user.role, session.id, refresh_expires_at, now)
    session.refresh_token_hash = _token_hash(tokens.refresh_token)
    db.commit()
    return tokens


def _decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "jti", "sid", "sub", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if claims.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims


def _token_ids(claims: dict[str, Any]) -> tuple[int, int]:
    try:
        user_id = int(claims["sub"])
        session_id = claims["sid"]
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if user_id <= 0 or isinstance(session_id, bool) or not isinstance(session_id, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id, session_id


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = _decode_token(credentials.credentials, "access")
    user_id, session_id = _token_ids(claims)
    now = datetime.now(timezone.utc)
    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .first()
    )
    user = db.query(User).filter(User.id == user_id).first()
    if session is None or user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is expired, revoked, or no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthenticatedUser(user=user, session_id=session_id)


def require_teacher(
    current: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if current.user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher role required",
        )
    return current


def require_student(
    current: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if current.user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student role required",
        )
    return current


def rotate_refresh_token(db: Session, token: str) -> TokenResponse:
    claims = _decode_token(token, "refresh")
    user_id, session_id = _token_ids(claims)
    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(timezone.utc),
        )
        .with_for_update()
        .first()
    )
    if session is None or not hmac.compare_digest(
        session.refresh_token_hash, _token_hash(token)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session is expired, revoked, or already used",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc)
    tokens = _new_token_pair(user.id, user.role, session.id, session.expires_at, now)
    session.refresh_token_hash = _token_hash(tokens.refresh_token)
    db.commit()
    return tokens
