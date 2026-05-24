from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogResponse

router = APIRouter()

@router.get("/", response_model=List[AuditLogResponse])
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    days: Optional[int] = Query(30, description="Fetch logs from the last X days")
):
    """
    Retrieve audit logs.
    Admins can see all logs. Regular users can only see their own logs.
    """
    query = select(AuditLog, User.email.label("user_email"))\
        .outerjoin(User, AuditLog.user_id == User.id)

    # Access control
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    is_admin = user_role == "ADMIN" or current_user.is_admin
    
    if not is_admin:
        query = query.where(AuditLog.user_id == current_user.id)

    # Filters
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if days is not None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.where(AuditLog.created_at >= cutoff)

    # Ordering and Pagination
    query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    rows = result.all()
    
    logs = []
    for log, email in rows:
        log_dict = {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at,
            "user_email": email
        }
        logs.append(log_dict)
        
    return logs
