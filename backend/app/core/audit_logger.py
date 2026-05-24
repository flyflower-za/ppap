from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from typing import Optional, Dict, Any
from app.models.audit import AuditLog
from app.models.user import User

async def log_audit_event(
    db: AsyncSession,
    action: str,
    user: Optional[User] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """
    Log an audit event asynchronously.
    """
    ip_address = None
    if request:
        if request.client:
            ip_address = request.client.host
        # Optionally, check headers for proxied IP like X-Forwarded-For
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()

    audit_log = AuditLog(
        user_id=user.id if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address
    )
    
    db.add(audit_log)
    # We commit in the request's main flow, or we could commit directly here.
    # To not interfere with transactions, it's often better to just add to the session.
    # However, if an error rolls back the session, the audit log is lost.
    # To guarantee audit logs even on error, we might need a separate session, 
    # but for simplicity we'll just flush it here. 
    await db.flush()
