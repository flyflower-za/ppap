from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Dict, Any

class AuditLogBase(BaseModel):
    action: str = Field(..., description="The action performed, e.g., 'LOGIN', 'CREATE_RULE', 'VERIFY_DOCUMENT'")
    resource_type: Optional[str] = Field(None, description="The type of resource affected, e.g., 'RULE', 'DOCUMENT', 'SYSTEM'")
    resource_id: Optional[str] = Field(None, description="The ID of the resource affected")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional structured details about the action")

class AuditLogCreate(AuditLogBase):
    user_id: Optional[str] = None
    ip_address: Optional[str] = None

class AuditLogResponse(AuditLogBase):
    id: str
    user_id: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    
    # Optional field to include user email when returning to frontend
    user_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
