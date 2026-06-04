from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.redis import redis_client
from app.core.minio_client import minio_client
from app.api import api_router
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting PPAP File Verification Platform...")

    # Initialize Database Tables
    try:
        from app.core.database import engine, Base
        import app.models  # Registers all models in Base.metadata
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")

    # Initialize Operator Registry
    try:
        from app.models.operator_registry import INITIAL_OPERATORS, OperatorRegistry
        from sqlalchemy import select
        from app.core.database import async_session_maker
        async with async_session_maker() as db:
            for operator_data in INITIAL_OPERATORS:
                existing = await db.execute(
                    select(OperatorRegistry).where(
                        OperatorRegistry.operator_key == operator_data["operator_key"]
                    )
                )
                existing_op = existing.scalars().first()
                if existing_op:
                    for key, value in operator_data.items():
                        if key != "operator_key":
                            setattr(existing_op, key, value)
                else:
                    new_op = OperatorRegistry(**operator_data)
                    db.add(new_op)
            await db.commit()
        logger.info("Operator registry initialized successfully.")
    except Exception as e:
        logger.warning(f"Failed to initialize operator registry: {e}")

    # Initialize Rule Templates
    try:
        from app.models.rule_template import DEFAULT_RULE_TEMPLATES, RuleTemplate
        from sqlalchemy import select
        from app.core.database import async_session_maker
        async with async_session_maker() as db:
            for template_data in DEFAULT_RULE_TEMPLATES:
                existing = await db.execute(
                    select(RuleTemplate).where(
                        RuleTemplate.name == template_data["name"],
                        RuleTemplate.is_system == True
                    )
                )
                existing_template = existing.scalars().first()
                if existing_template:
                    for key, value in template_data.items():
                        if key not in ["name", "created_by"]:
                            setattr(existing_template, key, value)
                else:
                    new_template = RuleTemplate(**template_data)
                    db.add(new_template)
            await db.commit()
        logger.info("Rule templates initialized successfully.")
    except Exception as e:
        logger.warning(f"Failed to initialize rule templates: {e}")

    # Initialize Default Email Templates
    try:
        from app.data.default_templates import init_default_templates
        await init_default_templates()
        logger.info("Default email templates initialized successfully.")
    except Exception as e:
        logger.warning(f"Failed to initialize default email templates: {e}")

    # Migrate User Roles
    try:
        from app.data.migrate_user_roles import migrate_user_roles
        await migrate_user_roles()
        logger.info("User role migration completed.")
    except Exception as e:
        logger.warning(f"Failed to migrate user roles: {e}")

    # Initialize Redis
    try:
        await redis_client.connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")

    # Initialize MinIO
    try:
        minio_client.connect()
        logger.info("MinIO connected")
    except Exception as e:
        logger.warning(f"MinIO connection failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await redis_client.disconnect()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered PDF file verification platform for PPAP documents",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.API_PREFIX)


# ==========================================
# Global Exception Handlers
# ==========================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle standard HTTP exceptions cleanly."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": str(exc.detail), "code": exc.status_code},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Mask database errors to avoid leaking schema or data details."""
    logger.error(f"Database error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": True, "message": "数据库操作失败", "code": 5001},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions to prevent stack trace leaks."""
    logger.error(f"Unhandled system error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": True, "message": "系统内部服务器错误", "code": 5000},
    )



# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": settings.APP_NAME,
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api_prefix": settings.API_PREFIX,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
