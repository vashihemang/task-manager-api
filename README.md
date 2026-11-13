# 🚀 Student-Teacher Task Manager API

<p align="center">
  <img src="https://img.shields.io/badge/Python-Backend-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-Framework-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" />
</p>

<p align="center">
  <b>A secure, scalable, and role-based Task Management REST API built with FastAPI and PostgreSQL.</b>
</p>

<p align="center">
  <a href="#-about-the-project">About</a> •
  <a href="#-features">Features</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-installation--setup">Installation</a> •
  <a href="#-api-documentation">API Docs</a>
</p>

---

## 📌 About the Project

**Student-Teacher Task Manager API** is a backend application designed to simplify task management and improve collaboration between students and teachers.

The application provides a structured, role-based environment where users can authenticate securely, manage tasks, and interact with the system according to their assigned roles.

Built using **FastAPI**, **PostgreSQL**, and **SQLAlchemy**, the API focuses on clean architecture, secure authentication, database management, and maintainable backend development.

It also integrates JWT-based authentication, database migrations with Alembic, and password hashing with Argon2.

Whether it's managing student assignments or organizing academic tasks, this API provides a foundation for a reliable task management platform.

## ✨ Features

- 🔐 **Secure Authentication** – JWT-based authentication.
- 👨‍🏫 **Role-Based Architecture** – Separate student and teacher functionality.
- 📝 **Task Management** – Dedicated task management endpoints.
- 👨‍🎓 **Student Management** – Student-related API functionality.
- 🔑 **Password Security** – Secure password hashing using Argon2.
- 🗄️ **Database Integration** – PostgreSQL with SQLAlchemy ORM.
- 🔄 **Database Migrations** – Schema versioning using Alembic.
- ⚡ **High Performance** – Asynchronous API support through FastAPI.
- 📚 **Interactive API Documentation** – Swagger UI and ReDoc.
- 🧪 **Testing Support** – Pytest and HTTPX.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| 🐍 Python | Backend programming |
| ⚡ FastAPI | REST API framework |
| 🐘 PostgreSQL | Relational database |
| 🗄️ SQLAlchemy | ORM and database operations |
| 🔄 Alembic | Database migrations |
| 🔐 PyJWT | JWT authentication |
| 🔑 Argon2 | Password hashing |
| 📦 Pydantic | Data validation |
| 🚀 Uvicorn | ASGI server |
| 🧪 Pytest | Automated testing |
| 🌱 Python Dotenv | Environment configuration |

## 📂 Project Structure

```text
task-manager-api/
│
├── api/
│   ├── auth.py
│   └── v3/
│       └── endpoints/
│           ├── students.py
│           └── tasks.py
│
├── core/
│   └── security.py
│
├── db/
│
├── models/
│
├── scripts/
│
├── services/
│
├── tests/
│
├── versions/
│
├── .env.example
├── .gitignore
├── alembic.ini
├── env.py
├── main.py
├── requirements.txt
└── README.md
```

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/vashihemang/task-manager-api.git
```

```bash
cd task-manager-api
```

### 2️⃣ Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows**
```bash
venv\Scripts\activate
```

**Linux / macOS**
```bash
source venv/bin/activate
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Configure environment variables

Create a `.env` file using the example configuration:

```bash
cp .env.example .env
```

For Windows:

```bash
copy .env.example .env
```

Configure the following variables:

```env
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/task_manager

JWT_SECRET_KEY=your-secure-secret-key-at-least-32-bytes-long

TEACHER_REGISTRATION_KEY=

ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7

DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=1800
```

**Important:** 

- Make sure PostgreSQL is installed and running.
- Create the `task_manager` database before starting the application.
- Use a strong, randomly generated JWT secret of at least 32 bytes.
- Keep your `.env` file private. Never commit production credentials.

### 5️⃣ Run database migrations

```bash
alembic upgrade head
```

### 6️⃣ Start the development server

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

## 📚 API Documentation

FastAPI automatically generates interactive API documentation.

| Documentation | URL |
|---|---|
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| OpenAPI Schema | http://127.0.0.1:8000/openapi.json |

### Available API Modules

| Module | Base Route | Description |
|---|---|---|
| 🔐 Authentication | `/auth` | User authentication |
| 👨‍🎓 Students | `/students` | Student-related operations |
| 📝 Tasks | `/tasks` | Task-related operations |
| ❤️ Health | `/health` | Application health check |

### Health Check

**Request**

```http
GET /health
```

**Example Response**

```json
{
  "status": "success",
  "message": "Task Manager API is running",
  "service": "Student-Teacher Task Manager API",
  "version": "2.0.0"
}
```

For the complete list of available endpoints, request methods, parameters, and response schemas, visit the Swagger documentation.

## 🧪 Running Tests

Run the automated test suite using:

```bash
pytest
```

For detailed test output:

```bash
pytest -v
```

## 🔒 Security

Security is an important part of this project.

- JWT-based authentication.
- Argon2 password hashing.
- Environment-based secret management.
- Configurable access-token and refresh-token expiration.
- Optional teacher registration key.
- Security configuration validation during application startup.

## 🚀 Future Enhancements

Potential improvements for the project include:

- 📧 Email notifications for task assignments.
- 📊 Student and teacher dashboards.
- ⏰ Task deadlines and reminder notifications.
- 📈 Task progress analytics.
- 🔔 Real-time notifications.
- 📎 File attachments for assignments.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the repository.
2. Create a new branch:

```bash
git checkout -b feature/your-feature-name
```

3. Commit your changes:

```bash
git commit -m "Add: your feature description"
```

4. Push your branch:

```bash
git push origin feature/your-feature-name
```

5. Open a Pull Request.

## 📊 GitHub Statistics

<p align="center">
  <img src="https://github-readme-stats.vercel.app/api?username=vashihemang&show_icons=true&theme=tokyonight&hide_border=true" height="165" />
  <img src="https://github-readme-stats.vercel.app/api/top-langs/?username=vashihemang&layout=compact&theme=tokyonight&hide_border=true" height="165" />
</p>

<p align="center">
  <img src="https://streak-stats.demolab.com?user=vashihemang&theme=tokyonight&hide_border=true" />
</p>

## 👨‍💻 Author

**Hemang Vashi**

GitHub: [@vashihemang](https://github.com/vashihemang)

Project: [Task Manager API](https://github.com/vashihemang/task-manager-api)

---

<p align="center">
  ⭐ If you find this project useful, consider giving it a star!
</p>

<p align="center">
  <b>Built with ❤️ using Python and FastAPI</b>
</p>
