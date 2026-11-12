from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn as uv

from api.auth import router_auth
from api.v3.endpoints.students import router_students
from api.v3.endpoints.tasks import router_task
from core.security import validate_security_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_security_settings()
    yield


app = FastAPI(
    title="Student-Teacher Task Manager API",
    description="Role-based student and teacher task management API backed by PostgreSQL, SQLAlchemy, and Alembic.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.include_router(router_auth, prefix="/auth")
app.include_router(router_students, prefix="/students")
app.include_router(router_task, prefix="/tasks")


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "success",
        "message": "Task Manager API is running",
        "service": "Student-Teacher Task Manager API",
        "version": "2.0.0",
    }


if __name__ == "__main__":
    uv.run("main:app", host="0.0.0.0", port=8000)
