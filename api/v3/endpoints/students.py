from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.config import get_db
from core.security import require_teacher
from models.users_v3 import (
    StudentDetailResponse,
    StudentListResponse,
    TaskResponse,
)
from services.student_service import get_student_with_tasks, list_students

router_students = APIRouter(
    tags=["Students (Teacher Access)"],
    dependencies=[Depends(require_teacher)],
)


@router_students.get("/", response_model=StudentListResponse)
def get_all_students(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return list_students(db, page=page, limit=limit, search=search)


@router_students.get("/{student_id}", response_model=StudentDetailResponse)
def get_student_details(
    student_id: int,
    db: Session = Depends(get_db),
):
    student = get_student_with_tasks(db, student_id)
    return {
        "message": "Student details fetched successfully",
        "data": student,
    }


@router_students.get("/{student_id}/tasks", response_model=list[TaskResponse])
def get_student_assigned_tasks(
    student_id: int,
    db: Session = Depends(get_db),
):
    student = get_student_with_tasks(db, student_id)
    return student.tasks
