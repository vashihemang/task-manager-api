from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.config import get_db
from core.security import AuthenticatedUser, get_current_user, require_teacher
from models.users_v3 import (
    StudentTaskListResponse,
    TaskCreate,
    TaskCreateResponse,
    TaskListResponse,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from services.task_service import (
    create_and_assign_task,
    delete_task_by_id,
    get_all_students_with_tasks,
    get_task_for_user,
    get_task_progress_summary,
    list_tasks,
    update_task_for_user,
    update_task_status_for_user,
)

router_task = APIRouter(tags=["Tasks"])


@router_task.post(
    "/",
    response_model=TaskCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    task: TaskCreate,
    current: AuthenticatedUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    new_task = create_and_assign_task(db, task, teacher_id=current.user.id)
    return {
        "message": "Task created and assigned successfully",
        "data": new_task,
    }


@router_task.get("/", response_model=TaskListResponse)
def get_tasks(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    status: str | None = Query(default=None),
    user_id: int | None = Query(default=None, ge=1),
    assigned_user: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None),
    title: str | None = Query(default=None),
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    effective_user_id = user_id if user_id is not None else assigned_user
    effective_search = search if search is not None else title

    return list_tasks(
        db=db,
        current=current,
        page=page,
        limit=limit,
        status_filter=status,
        user_id=effective_user_id,
        search=effective_search,
    )


@router_task.get("/progress")
def get_progress(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_teacher),
):
    return get_task_progress_summary(db)


@router_task.get("/students", response_model=StudentTaskListResponse)
def get_student_tasks(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_teacher),
):
    return {
        "message": "Student tasks fetched successfully",
        "data": get_all_students_with_tasks(db),
    }


@router_task.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_task_for_user(db, task_id, current)


@router_task.patch("/{task_id}/status", response_model=TaskResponse)
def update_task_status(
    task_id: int,
    status_data: TaskStatusUpdate,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_task_status_for_user(db, task_id, status_data, current)


@router_task.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_task_for_user(db, task_id, task_data, current)


@router_task.delete("/{task_id}", dependencies=[Depends(require_teacher)])
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    delete_task_by_id(db, task_id)
    return {
        "message": "Task deleted successfully",
    }
