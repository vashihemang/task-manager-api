from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from core.config import get_db
from core.security import (
    AuthenticatedUser,
    require_student,
    require_teacher,
    rotate_refresh_token,
)
from db.database import User
from models.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserProfile,
)
from services.auth_service import (
    authenticate_user,
    logout_session,
    register_user,
    verify_teacher_registration_key,
)

router_auth = APIRouter(tags=["Authentication"])


# ==========================================
# STUDENT AUTHENTICATION ENDPOINTS
# ==========================================


@router_auth.post(
    "/student/register",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
)
def register_student(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> User:
    return register_user(db, payload, role="student")


@router_auth.post("/student/login", response_model=TokenResponse)
def login_student(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    return authenticate_user(db, payload, required_role="student")


@router_auth.get("/student/profile", response_model=UserProfile)
def student_profile(
    current: AuthenticatedUser = Depends(require_student),
) -> User:
    return current.user


@router_auth.post("/student/logout", response_model=MessageResponse)
def logout_student(
    current: AuthenticatedUser = Depends(require_student),
    db: Session = Depends(get_db),
) -> MessageResponse:
    return logout_session(db, current)


# ==========================================
# TEACHER AUTHENTICATION ENDPOINTS
# ==========================================


@router_auth.post(
    "/teacher/register",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
)
def register_teacher(
    payload: RegisterRequest,
    registration_key: str | None = Header(default=None, alias="X-Teacher-Registration-Key"),
    db: Session = Depends(get_db),
) -> User:
    verify_teacher_registration_key(registration_key)
    return register_user(db, payload, role="teacher")


@router_auth.post("/teacher/login", response_model=TokenResponse)
def login_teacher(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    return authenticate_user(db, payload, required_role="teacher")


@router_auth.get("/teacher/profile", response_model=UserProfile)
def teacher_profile(
    current: AuthenticatedUser = Depends(require_teacher),
) -> User:
    return current.user


@router_auth.post("/teacher/logout", response_model=MessageResponse)
def logout_teacher(
    current: AuthenticatedUser = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> MessageResponse:
    return logout_session(db, current)


# ==========================================
# SESSION TOKEN REFRESH
# ==========================================


@router_auth.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    return rotate_refresh_token(db, payload.refresh_token)
