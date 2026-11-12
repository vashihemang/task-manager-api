import sys
from getpass import getpass
from pathlib import Path

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import func
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import SessionLocal
from core.security import hash_password
from db.database import User


def seed_user(db: Session, role: str) -> None:
    email = input(f"{role.title()} email [{role}@example.com]: ").strip()
    if not email:
        email = f"{role}@example.com"
    email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    existing_user = db.query(User).filter(func.lower(User.email) == email).first()
    if existing_user is not None:
        if existing_user.role != role:
            raise ValueError(f"{email} already exists with a different role")
        print(f"Existing {role} account kept: {email}")
        return

    name = input(f"{role.title()} full name: ").strip()
    if len(name) < 2:
        raise ValueError("Name must contain at least 2 characters")
    password = getpass(f"Set {role} password (at least 8 characters): ")
    if len(password) < 8 or len(password) > 128:
        raise ValueError("Password must be between 8 and 128 characters")

    db.add(
        User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            status="active",
        )
    )
    db.flush()
    print(f"Created {role} account: {email}")


def main() -> None:
    with SessionLocal.begin() as db:
        seed_user(db, "teacher")
        seed_user(db, "student")


if __name__ == "__main__":
    main()
