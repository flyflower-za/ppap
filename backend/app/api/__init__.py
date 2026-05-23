from fastapi import APIRouter
from app.api import auth, files, notifications, notes, settings

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(files.router)
api_router.include_router(notifications.router)
api_router.include_router(notes.router)
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
