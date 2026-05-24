from fastapi import APIRouter
from app.api import auth, files, notifications, notes, settings, ldap, websocket, rules

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(files.router)
api_router.include_router(websocket.router)
api_router.include_router(notifications.router)
api_router.include_router(notes.router)
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(ldap.router, prefix="/settings", tags=["ldap"])
api_router.include_router(rules.router, prefix="/rule-engine", tags=["rules"])
