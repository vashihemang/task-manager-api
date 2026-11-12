from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

TaskStatusLiteral = Literal["pending", "in_progress", "completed"]

_STATUS_MAP: dict[str, TaskStatusLiteral] = {
    "pending": "pending",
    "in_progress": "in_progress",
    "in progress": "in_progress",
    "in-progress": "in_progress",
    "completed": "completed",
    "done": "completed",
}


def normalize_task_status(value: str) -> TaskStatusLiteral:
    if not isinstance(value, str):
        raise ValueError("Status must be a string")
    normalized = _STATUS_MAP.get(value.strip().lower())
    if normalized is None:
        raise ValueError("Status must be one of: pending, in_progress, completed")
    return normalized


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: str | None = None
    status: str
    role: Literal["student"]
    created_at: datetime
    updated_at: datetime | None = None


class StudentListResponse(BaseModel):
    message: str
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1)
    total_students: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=1)
    data: list[StudentResponse]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    deadline: datetime | None = None
    status: str = "pending"
    user_id: int = Field(..., gt=0)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Title must contain at least 2 non-whitespace characters")
        return value

    @field_validator("status")
    @classmethod
    def validate_initial_status(cls, value: str) -> TaskStatusLiteral:
        normalized = normalize_task_status(value)
        if normalized != "pending":
            raise ValueError("New tasks must be created with status 'pending'")
        return normalized


class TaskStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    work_notes: str | None = Field(default=None, max_length=20000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> TaskStatusLiteral:
        return normalize_task_status(value)


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    deadline: datetime | None = None
    status: str | None = None
    user_id: int | None = Field(default=None, gt=0)
    work_notes: str | None = Field(default=None, max_length=20000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Title must contain at least 2 non-whitespace characters")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> TaskStatusLiteral | None:
        if value is None:
            return None
        return normalize_task_status(value)

    @model_validator(mode="after")
    def validate_changes(self) -> "TaskUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one task field must be provided")
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("Status cannot be null")
        if "user_id" in self.model_fields_set and self.user_id is None:
            raise ValueError("Assignee cannot be null")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Title cannot be null")
        return self


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    status: TaskStatusLiteral
    work_notes: str | None = None
    deadline: datetime | None = None
    user_id: int
    assigned_by_id: int | None = None
    created_at: datetime
    updated_at: datetime | None = None


class TaskCreateResponse(BaseModel):
    message: str
    data: TaskResponse


class TaskListResponse(BaseModel):
    message: str
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1)
    total_tasks: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=1)
    data: list[TaskResponse]


class StudentTasksOverview(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    total_tasks: int
    tasks: list[TaskResponse]


class StudentTaskListResponse(BaseModel):
    message: str
    data: list[StudentTasksOverview]


class StudentWithTasksResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: str | None = None
    status: str
    role: Literal["student"]
    created_at: datetime
    updated_at: datetime | None = None
    tasks: list[TaskResponse]


class StudentDetailResponse(BaseModel):
    message: str
    data: StudentWithTasksResponse
