from fastapi import APIRouter
from app.api import auth, files, notifications, notes, settings, ldap, websocket, rules, audit, modules, oidc, operators

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(files.router)
api_router.include_router(websocket.router)
api_router.include_router(notifications.router)
api_router.include_router(notes.router)
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(ldap.router, prefix="/settings", tags=["ldap"])
api_router.include_router(rules.router, prefix="/rule-engine", tags=["rules"])
api_router.include_router(operators.router, prefix="/rule-engine/operators", tags=["operators"])
api_router.include_router(audit.router, prefix="/audit-logs", tags=["audit"])
api_router.include_router(modules.router, prefix="/modules", tags=["modules"])
api_router.include_router(oidc.router, tags=["oidc"])
