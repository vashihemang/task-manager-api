from datetime import datetime, timedelta, timezone
import os

import jwt
import pytest
from fastapi.testclient import TestClient

from core.config import SessionLocal
from db.database import AuthSession, Task, User
from main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TEACHER_REGISTRATION_KEY", raising=False)
    with TestClient(app) as test_client:
        with SessionLocal.begin() as db:
            db.query(AuthSession).delete(synchronize_session=False)
            db.query(Task).delete(synchronize_session=False)
            db.query(User).delete(synchronize_session=False)
        yield test_client


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_and_login_teacher(
    client: TestClient,
    name: str = "Prof. Sharma",
    email: str = "teacher@example.com",
    password: str = "teacher-pass-123",
) -> tuple[dict, dict[str, str]]:
    reg = client.post(
        "/auth/teacher/register",
        json={"name": name, "email": email, "password": password, "phone": "9876543210"},
    )
    assert reg.status_code == 201
    login_res = client.post(
        "/auth/teacher/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    tokens = login_res.json()
    return reg.json(), bearer(tokens["access_token"])


def register_and_login_student(
    client: TestClient,
    name: str = "Aarav Patel",
    email: str = "student@example.com",
    password: str = "student-pass-123",
) -> tuple[dict, dict[str, str]]:
    reg = client.post(
        "/auth/student/register",
        json={"name": name, "email": email, "password": password, "phone": "9123456780"},
    )
    assert reg.status_code == 201
    login_res = client.post(
        "/auth/student/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    tokens = login_res.json()
    return reg.json(), bearer(tokens["access_token"])


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_separate_student_and_teacher_auth_profile_and_logout(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    # 1. Student registration & login
    student_profile, student_headers = register_and_login_student(client)
    assert student_profile["role"] == "student"

    # Duplicate email rejected with 409
    dup = client.post(
        "/auth/student/register",
        json={
            "name": "Duplicate",
            "email": "STUDENT@example.com",
            "password": "student-pass-123",
        },
    )
    assert dup.status_code == 409

    # 2. Teacher registration & login
    teacher_profile, teacher_headers = register_and_login_teacher(client)
    assert teacher_profile["role"] == "teacher"

    # Cross-role login attempts rejected with 401
    assert client.post(
        "/auth/teacher/login",
        json={"email": "student@example.com", "password": "student-pass-123"},
    ).status_code == 401
    assert client.post(
        "/auth/student/login",
        json={"email": "teacher@example.com", "password": "teacher-pass-123"},
    ).status_code == 401

    # Role-separated profile endpoints
    s_prof = client.get("/auth/student/profile", headers=student_headers)
    assert s_prof.status_code == 200
    assert s_prof.json()["email"] == "student@example.com"

    t_prof = client.get("/auth/teacher/profile", headers=teacher_headers)
    assert t_prof.status_code == 200
    assert t_prof.json()["email"] == "teacher@example.com"

    # Cross-role profile access blocked with 403
    assert client.get("/auth/teacher/profile", headers=student_headers).status_code == 403
    assert client.get("/auth/student/profile", headers=teacher_headers).status_code == 403

    # Optional TEACHER_REGISTRATION_KEY enforcement when configured
    reg_key = "secure-teacher-registration-key-32-bytes-minimum"
    monkeypatch.setenv("TEACHER_REGISTRATION_KEY", reg_key)
    assert client.post(
        "/auth/teacher/register",
        json={"name": "Second Teacher", "email": "t2@example.com", "password": "teacher-pass-123"},
        headers={"X-Teacher-Registration-Key": "wrong-key"},
    ).status_code == 403
    assert client.post(
        "/auth/teacher/register",
        json={"name": "Second Teacher", "email": "t2@example.com", "password": "teacher-pass-123"},
        headers={"X-Teacher-Registration-Key": reg_key},
    ).status_code == 201

    # Role-separated logout revokes session
    assert client.post("/auth/teacher/logout", headers=student_headers).status_code == 403
    assert client.post("/auth/student/logout", headers=student_headers).status_code == 200
    assert client.get("/auth/student/profile", headers=student_headers).status_code == 401


def test_teacher_student_task_workflow_rbac_and_idor_protection(client: TestClient):
    teacher, teacher_headers = register_and_login_teacher(client)
    student1, student1_headers = register_and_login_student(
        client, name="Student One", email="s1@example.com"
    )
    student2, student2_headers = register_and_login_student(
        client, name="Student Two", email="s2@example.com"
    )

    # Unauthenticated requests return 401
    assert client.get("/tasks/").status_code == 401
    assert client.get("/students/").status_code == 401

    # 5. Teachers can view all students & individual student details
    students_list = client.get("/students/", headers=teacher_headers)
    assert students_list.status_code == 200
    assert students_list.json()["total_students"] == 2

    student1_detail = client.get(f"/students/{student1['id']}", headers=teacher_headers)
    assert student1_detail.status_code == 200
    assert student1_detail.json()["data"]["email"] == "s1@example.com"

    # 11. Students cannot access teacher-only student endpoints
    assert client.get("/students/", headers=student1_headers).status_code == 403
    assert client.get(f"/students/{student2['id']}", headers=student1_headers).status_code == 403

    # 6. Teachers can create and assign tasks to students (with deadline and teacher relationship)
    deadline_str = "2026-12-01T18:00:00Z"
    created1 = client.post(
        "/tasks/",
        headers=teacher_headers,
        json={
            "title": "Database Schema Design",
            "description": "Design normalized PostgreSQL tables",
            "deadline": deadline_str,
            "user_id": student1["id"],
        },
    )
    assert created1.status_code == 201
    task1 = created1.json()["data"]
    assert task1["status"] == "pending"
    assert task1["user_id"] == student1["id"]
    assert task1["assigned_by_id"] == teacher["id"]
    assert task1["deadline"] is not None

    created2 = client.post(
        "/tasks/",
        headers=teacher_headers,
        json={
            "title": "API Security Audit",
            "description": "Verify RBAC and IDOR checks",
            "user_id": student2["id"],
        },
    )
    assert created2.status_code == 201
    task2 = created2.json()["data"]

    # Verify SQLAlchemy relationships between Teacher, Student, and Task
    with SessionLocal() as db:
        db_task1 = db.query(Task).filter(Task.id == task1["id"]).one()
        assert db_task1.student.id == student1["id"]
        assert db_task1.teacher.id == teacher["id"]

    # 8. Students can view only their own assigned tasks
    s1_tasks = client.get("/tasks/", headers=student1_headers)
    assert s1_tasks.status_code == 200
    assert [t["id"] for t in s1_tasks.json()["data"]] == [task1["id"]]

    s1_task_detail = client.get(f"/tasks/{task1['id']}", headers=student1_headers)
    assert s1_task_detail.status_code == 200
    assert s1_task_detail.json()["title"] == "Database Schema Design"

    # 9. Students can update their own task statuses (Pending -> In Progress -> Completed)
    in_prog = client.patch(
        f"/tasks/{task1['id']}/status",
        headers=student1_headers,
        json={"status": "In Progress", "work_notes": "Working on ER diagram"},
    )
    assert in_prog.status_code == 200
    assert in_prog.json()["status"] == "in_progress"
    assert in_prog.json()["work_notes"] == "Working on ER diagram"

    completed = client.put(
        f"/tasks/{task1['id']}",
        headers=student1_headers,
        json={"status": "Completed", "work_notes": "Submitted schema & migrations"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    # 10. IDOR Protection: Students cannot access or modify other students' tasks or statuses
    assert client.get(
        f"/tasks/{task2['id']}",
        headers=student1_headers,
    ).status_code == 403
    assert client.get(
        "/tasks/",
        headers=student1_headers,
        params={"user_id": student2["id"]},
    ).status_code == 403
    assert client.patch(
        f"/tasks/{task2['id']}/status",
        headers=student1_headers,
        json={"status": "completed"},
    ).status_code == 403
    assert client.put(
        f"/tasks/{task2['id']}",
        headers=student1_headers,
        json={"status": "completed"},
    ).status_code == 403

    # 11. Students cannot create, reassign, edit task metadata, or delete tasks
    assert client.post(
        "/tasks/",
        headers=student1_headers,
        json={"title": "Unauthorized", "user_id": student1["id"]},
    ).status_code == 403
    assert client.put(
        f"/tasks/{task1['id']}",
        headers=student1_headers,
        json={"user_id": student2["id"]},
    ).status_code == 403
    assert client.put(
        f"/tasks/{task1['id']}",
        headers=student1_headers,
        json={"title": "Tampered Title"},
    ).status_code == 403
    assert client.delete(
        f"/tasks/{task1['id']}",
        headers=student1_headers,
    ).status_code == 403
    assert client.get("/tasks/progress", headers=student1_headers).status_code == 403
    assert client.get("/tasks/students", headers=student1_headers).status_code == 403

    # 7. Teachers can view all students' tasks, statuses, and progress
    all_tasks = client.get("/tasks/", headers=teacher_headers)
    assert all_tasks.status_code == 200
    assert all_tasks.json()["total_tasks"] == 2

    overview = client.get("/tasks/students", headers=teacher_headers)
    assert overview.status_code == 200
    assert len(overview.json()["data"]) == 2

    progress = client.get("/tasks/progress", headers=teacher_headers)
    assert progress.status_code == 200
    assert progress.json()["by_status"] == {
        "pending": 1,
        "in_progress": 0,
        "completed": 1,
    }

    # Teacher can update and delete tasks
    t_update = client.put(
        f"/tasks/{task2['id']}",
        headers=teacher_headers,
        json={"title": "Updated Security Audit", "status": "in_progress"},
    )
    assert t_update.status_code == 200
    assert t_update.json()["title"] == "Updated Security Audit"
    assert t_update.json()["status"] == "in_progress"

    assert client.delete(f"/tasks/{task2['id']}", headers=teacher_headers).status_code == 200
    assert client.get(f"/tasks/{task2['id']}", headers=teacher_headers).status_code == 404


def test_pagination_search_filters_and_error_handling(client: TestClient):
    _, teacher_headers = register_and_login_teacher(client)
    student, _ = register_and_login_student(client)

    for title in ("Alpha Project", "Beta Assignment", "Gamma Project"):
        res = client.post(
            "/tasks/",
            headers=teacher_headers,
            json={"title": title, "user_id": student["id"]},
        )
        assert res.status_code == 201

    filtered = client.get(
        "/tasks/",
        headers=teacher_headers,
        params={
            "page": 1,
            "limit": 2,
            "search": "Project",
            "status": "pending",
            "user_id": student["id"],
        },
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert body["total_tasks"] == 2
    assert len(body["data"]) == 2

    # Invalid input & missing record errors
    assert client.post(
        "/tasks/",
        headers=teacher_headers,
        json={"title": "A", "user_id": student["id"]},
    ).status_code == 422
    assert client.post(
        "/tasks/",
        headers=teacher_headers,
        json={"title": "Missing Student Task", "user_id": 99999},
    ).status_code == 404
    assert client.get("/students/99999", headers=teacher_headers).status_code == 404
    assert client.get("/tasks/99999", headers=teacher_headers).status_code == 404


def test_expired_and_invalid_tokens_rejected(client: TestClient):
    register_and_login_student(client)
    login_res = client.post(
        "/auth/student/login",
        json={"email": "student@example.com", "password": "student-pass-123"},
    )
    tokens = login_res.json()

    claims = jwt.decode(
        tokens["access_token"],
        options={"verify_signature": False, "verify_exp": False},
        algorithms=["HS256"],
    )
    claims["exp"] = datetime.now(timezone.utc) - timedelta(seconds=5)
    expired_token = jwt.encode(
        claims,
        os.environ["JWT_SECRET_KEY"],
        algorithm="HS256",
    )
    assert client.get("/tasks/", headers=bearer(expired_token)).status_code == 401
