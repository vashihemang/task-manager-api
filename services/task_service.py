from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.security import AuthenticatedUser
from db.database import Task, User
from models.users_v3 import (
    TaskCreate,
    TaskStatusUpdate,
    TaskUpdate,
    normalize_task_status,
)


def _validate_student_assignee(db: Session, student_id: int) -> User:
    assignee = db.query(User).filter(User.id == student_id).first()
    if assignee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    if assignee.role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tasks can only be assigned to students",
        )
    if assignee.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign tasks to an inactive student account",
        )
    return assignee


def create_and_assign_task(
    db: Session,
    payload: TaskCreate,
    teacher_id: int,
) -> Task:
    _validate_student_assignee(db, payload.user_id)
    new_task = Task(
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        status=payload.status,
        user_id=payload.user_id,
        assigned_by_id=teacher_id,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


def list_tasks(
    db: Session,
    current: AuthenticatedUser,
    page: int = 1,
    limit: int = 10,
    status_filter: str | None = None,
    user_id: int | None = None,
    search: str | None = None,
) -> dict:
    # Prevent IDOR: Students cannot query tasks belonging to another student
    if current.user.role == "student":
        if user_id is not None and user_id != current.user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: students can only view their own assigned tasks",
            )
        effective_user_id = current.user.id
    else:
        effective_user_id = user_id

    query = db.query(Task)
    if effective_user_id is not None:
        query = query.filter(Task.user_id == effective_user_id)

    if status_filter is not None:
        try:
            normalized_status = normalize_task_status(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        query = query.filter(Task.status == normalized_status)

    if search and search.strip():
        query = query.filter(Task.title.ilike(f"%{search.strip()}%"))

    total_tasks = query.count()
    total_pages = (total_tasks + limit - 1) // limit if total_tasks else 1
    tasks = (
        query.order_by(Task.id)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Tasks fetched successfully",
        "page": page,
        "limit": limit,
        "total_tasks": total_tasks,
        "total_pages": total_pages,
        "data": tasks,
    }


def get_task_for_user(
    db: Session,
    task_id: int,
    current: AuthenticatedUser,
) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    if current.user.role == "student" and task.user_id != current.user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: students can only view their own assigned tasks",
        )
    return task


def update_task_status_for_user(
    db: Session,
    task_id: int,
    status_data: TaskStatusUpdate,
    current: AuthenticatedUser,
) -> Task:
    task = get_task_for_user(db, task_id, current)
    task.status = status_data.status
    if "work_notes" in status_data.model_fields_set:
        task.work_notes = status_data.work_notes
    db.commit()
    db.refresh(task)
    return task


def update_task_for_user(
    db: Session,
    task_id: int,
    task_data: TaskUpdate,
    current: AuthenticatedUser,
) -> Task:
    update_data = task_data.model_dump(exclude_unset=True)

    if current.user.role == "student":
        forbidden_fields = set(update_data) - {"status", "work_notes"}
        if forbidden_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students may only update task status and work notes",
            )

    task = get_task_for_user(db, task_id, current)

    if "user_id" in update_data:
        _validate_student_assignee(db, update_data["user_id"])

    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


def delete_task_by_id(db: Session, task_id: int) -> None:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    db.delete(task)
    db.commit()


def get_all_students_with_tasks(db: Session) -> list[dict]:
    rows = (
        db.query(User, Task)
        .outerjoin(Task, Task.user_id == User.id)
        .filter(User.role == "student")
        .order_by(User.id, Task.id)
        .all()
    )
    students: dict[int, dict] = {}
    for student, task in rows:
        student_data = students.setdefault(
            student.id,
            {
                "user_id": student.id,
                "name": student.name,
                "email": student.email,
                "total_tasks": 0,
                "tasks": [],
            },
        )
        if task is not None:
            student_data["tasks"].append(task)
            student_data["total_tasks"] += 1
    return list(students.values())


def get_task_progress_summary(db: Session) -> dict:
    statuses = ("pending", "in_progress", "completed")
    status_counts = {
        row.status: row.total
        for row in db.query(Task.status, func.count(Task.id).label("total"))
        .group_by(Task.status)
        .all()
    }
    students = db.query(User).filter(User.role == "student").order_by(User.id).all()
    student_counts: dict[int, dict[str, int]] = {}
    for row in (
        db.query(Task.user_id, Task.status, func.count(Task.id).label("total"))
        .group_by(Task.user_id, Task.status)
        .all()
    ):
        student_counts.setdefault(row.user_id, {})[row.status] = row.total

    return {
        "total_tasks": sum(status_counts.values()),
        "by_status": {
            task_status: status_counts.get(task_status, 0)
            for task_status in statuses
        },
        "students": [
            {
                "user_id": student.id,
                "name": student.name,
                "email": student.email,
                "total_tasks": sum(student_counts.get(student.id, {}).values()),
                "by_status": {
                    task_status: student_counts.get(student.id, {}).get(task_status, 0)
                    for task_status in statuses
                },
            }
            for student in students
        ],
    }
