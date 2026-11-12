from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.config import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('student', 'teacher')", name="ck_users_role"),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_users_status"),
        Index("ix_users_role", "role"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    password_hash = Column(String(255), nullable=False)
    role = Column(
        String(20),
        nullable=False,
        default="student",
        server_default=text("'student'"),
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Tasks assigned to this user (when user is a student)
    tasks = relationship(
        "Task",
        foreign_keys="Task.user_id",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Task.id",
    )

    # Tasks created/assigned by this user (when user is a teacher)
    assigned_tasks = relationship(
        "Task",
        foreign_keys="Task.assigned_by_id",
        back_populates="teacher",
        passive_deletes=True,
        order_by="Task.id",
    )

    auth_sessions = relationship(
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')",
            name="ck_tasks_status",
        ),
        Index("ix_tasks_user_id", "user_id"),
        Index("ix_tasks_assigned_by_id", "assigned_by_id"),
        Index("ix_tasks_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    work_notes = Column(Text, nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    student = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="tasks",
    )
    teacher = relationship(
        "User",
        foreign_keys=[assigned_by_id],
        back_populates="assigned_tasks",
    )

    @property
    def user(self):
        return self.student


class AuthSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user = relationship("User", back_populates="auth_sessions")
