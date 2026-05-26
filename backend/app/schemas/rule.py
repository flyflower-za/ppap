from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

class DocumentCategoryBase(BaseModel):
    name: str
    keywords: List[str] = Field(default_factory=list)
    is_active: bool = True

    @field_validator("keywords", mode="before")
    @classmethod
    def coerce_null_keywords(cls, v):
        if v is None:
            return []
        return v

class DocumentCategoryCreate(DocumentCategoryBase):
    pass

class DocumentCategoryUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    is_active: Optional[bool] = None

class DocumentCategoryResponse(DocumentCategoryBase):
    id: UUID

    class Config:
        from_attributes = True


class VerificationRuleBase(BaseModel):
    category_id: Optional[UUID] = None
    rule_name: str
    rule_type: str
    rule_content: str
    severity: str
    is_active: bool = True
    is_system: bool = False
    logic_config: Dict[str, Any] = Field(default_factory=dict)

class VerificationRuleCreate(VerificationRuleBase):
    pass

class VerificationRuleUpdate(BaseModel):
    category_id: Optional[UUID] = None
    rule_name: Optional[str] = None
    rule_type: Optional[str] = None
    rule_content: Optional[str] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None
    is_system: Optional[bool] = None
    logic_config: Optional[Dict[str, Any]] = None

class VerificationRuleResponse(VerificationRuleBase):
    id: UUID

    class Config:
        from_attributes = True

class DocumentCategoryWithRules(DocumentCategoryResponse):
    rules: List[VerificationRuleResponse] = Field(default_factory=list)
