"""
Operator Registry Schemas - 算子注册表的 API 数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class OperatorRegistryResponse(BaseModel):
    id: str
    operator_key: str
    display_name: str
    category: str
    description: Optional[str] = None
    operator_type: str
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    supports_severity: bool = True
    default_severity: str = "fail"
    priority: int = 100
    is_heavy: bool = False
    is_active: bool = True
    is_deprecated: bool = False
    deprecated_by: Optional[str] = None
    version: str = "1.0.0"
    created_at: datetime
    updated_at: datetime

    # UI 渲染所需的额外字段
    icon: Optional[str] = None
    color: Optional[str] = None
    border_color: Optional[str] = None
    group: Optional[str] = None

    class Config:
        from_attributes = True


class OperatorRegistryCreate(BaseModel):
    operator_key: str
    display_name: str
    category: str
    description: Optional[str] = None
    operator_type: str
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    supports_severity: bool = True
    default_severity: str = "fail"
    priority: int = 100
    is_heavy: bool = False
    icon: Optional[str] = None
    color: Optional[str] = None
    border_color: Optional[str] = None
    group: Optional[str] = None


class OperatorRegistryUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    supports_severity: Optional[bool] = None
    default_severity: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    is_deprecated: Optional[bool] = None
    deprecated_by: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    border_color: Optional[str] = None


class OperatorTemplateResponse(BaseModel):
    id: str
    name: str
    operator_key: str
    preset_parameters: Dict[str, Any] = Field(default_factory=dict)
    use_case_description: Optional[str] = None
    is_system: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class OperatorTemplateCreate(BaseModel):
    name: str
    operator_key: str
    preset_parameters: Dict[str, Any] = Field(default_factory=dict)
    use_case_description: Optional[str] = None


class RuleTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category_suggestions: List[str] = Field(default_factory=list)
    is_system: bool = False
    template_rules: List[Dict[str, Any]]
    created_by: Optional[str] = None
    created_at: datetime
    is_public: bool = False

    class Config:
        from_attributes = True


class RuleTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_suggestions: List[str] = Field(default_factory=list)
    template_rules: List[Dict[str, Any]]
    is_public: bool = False


class RuleTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_suggestions: Optional[List[str]] = None
    template_rules: Optional[List[Dict[str, Any]]] = None
    is_public: Optional[bool] = None
