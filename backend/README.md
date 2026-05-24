# PPAP File Verification Platform - Backend

FastAPI backend for AI-powered PDF file verification.

## Tech Stack

- **Framework**: FastAPI 0.109
- **Database**: PostgreSQL + SQLAlchemy 2.0 (async)
- **Cache**: Redis
- **File Storage**: MinIO
- **AI Service**: Aliyun Agent

## Project Structure

```
backend/
├── app/
│   ├── api/           # API routes
│   ├── core/          # Core config & utilities
│   ├── models/        # Database models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   └── main.py        # Application entry
├── requirements.txt   # Dependencies
└── .env.example       # Configuration template
```

## Quick Start

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start services (using Docker)

```bash
docker-compose up -d postgres redis minio
```

### 4. Run database migrations

```bash
# TODO: Add Alembic setup
```

### 5. Start the server

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. Start the Celery Worker (Background tasks)

For file verification and periodic tasks to process, you must run the Celery worker in a separate terminal:

```bash
cd backend

# On Linux/Production:
celery -A app.tasks.celery_app worker --loglevel=info

# On macOS (Local Development):
# Use the wrapper script to avoid fork() crashes (signal 6) caused by Objective-C libs
./start_celery.sh
```

### 6. Access API

- API: http://localhost:8000/api/v1
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/login | User login |
| GET | /api/v1/auth/me | Get current user |
| POST | /api/v1/files/upload | Upload file |
| GET | /api/v1/files | List files |
| GET | /api/v1/files/{id} | Get file detail |
| GET | /api/v1/files/{id}/download | Get download URL |
| DELETE | /api/v1/files/{id} | Delete file |
| GET | /api/v1/notifications | Get notifications |
| POST | /api/v1/notifications/mark-read | Mark as read |
| POST | /api/v1/notes | Create note |
| GET | /api/v1/notes/file/{file_id} | Get file notes |

## Development

### Code formatting

```bash
# Format code
black app/

# Lint
ruff check app/
```

### Run tests

```bash
pytest
```
