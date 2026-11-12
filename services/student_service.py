from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from db.database import User


def list_students(
    db: Session,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
) -> dict:
    query = db.query(User).filter(User.role == "student")
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern),
            )
        )

    total_students = query.count()
    total_pages = (total_students + limit - 1) // limit if total_students else 1
    students = (
        query.order_by(User.id)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Students fetched successfully",
        "page": page,
        "limit": limit,
        "total_students": total_students,
        "total_pages": total_pages,
        "data": students,
    }


def get_student_with_tasks(db: Session, student_id: int) -> User:
    student = (
        db.query(User)
        .options(selectinload(User.tasks))
        .filter(User.id == student_id, User.role == "student")
        .first()
    )
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    return student
