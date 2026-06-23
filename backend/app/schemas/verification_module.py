from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class ModuleType(str, Enum):
    qr_scanner = "qr_scanner"
    signature_verifier = "signature_verifier"
    pdf_info = "pdf_info"
    institution_sniffer = "institution_sniffer"
    revision_check = "revision_check"
    text_llm = "text_llm"
    vision_llm = "vision_llm"
    url_fetch = "url_fetch"
    stamp_detection = "stamp_detection"
    document_diff = "document_diff"
    table_verification = "table_verification"
    regex_match = "regex_match"
    keyword_match = "keyword_match"
    comparison = "comparison"
    variable_extractor = "variable_extractor"
    online_verification = "online_verification"


class ModuleSeverity(str, Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


# Metadata for module types (for frontend rendering)
MODULE_TYPE_METADATA = {
    "qr_scanner": {
        "label": "二维码识别",
        "description": "识别文档中的二维码并提取内容",
        "icon": "📱",
        "config_fields": []
    },
    "signature_verifier": {
        "label": "数字签名验证",
        "description": "验证PDF电子签名的有效性",
        "icon": "🔐",
        "config_fields": [
            {"key": "expected_issuer", "label": "预期签发者", "type": "text", "default": ""}
        ]
    },
    "pdf_info": {
        "label": "PDF信息提取",
        "description": "提取PDF元数据（页数、标题等）",
        "icon": "📄",
        "config_fields": []
    },
    "institution_sniffer": {
        "label": "机构识别",
        "description": "识别发证机构（CTI、SGS等）",
        "icon": "🏢",
        "config_fields": []
    },
    "revision_check": {
        "label": "修订检查",
        "description": "检查文档是否被篡改或修改",
        "icon": "🔍",
        "config_fields": [
            {"key": "max_revisions", "label": "最大修订次数", "type": "number", "default": 0},
            {"key": "allow_incremental", "label": "允许增量更新", "type": "boolean", "default": True}
        ]
    },
    "text_llm": {
        "label": "文本语义分析",
        "description": "使用LLM分析文档文本内容",
        "icon": "📝",
        "config_fields": [
            {"key": "prompt", "label": "提示词", "type": "textarea", "default": ""},
            {"key": "operation_mode", "label": "操作模式", "type": "select", "options": ["verification", "extraction"], "default": "verification"}
        ]
    },
    "vision_llm": {
        "label": "视觉分析",
        "description": "使用视觉模型分析文档图像",
        "icon": "👁️",
        "config_fields": [
            {"key": "prompt", "label": "提示词", "type": "textarea", "default": ""},
            {"key": "target_page", "label": "目标页码", "type": "number", "default": 1},
            {"key": "operation_mode", "label": "操作模式", "type": "select", "options": ["verification", "extraction"], "default": "verification"}
        ]
    },
    "regex_match": {
        "label": "正则匹配",
        "description": "使用正则表达式匹配文本",
        "icon": "🔤",
        "config_fields": [
            {"key": "pattern", "label": "正则表达式", "type": "text", "default": ""}
        ]
    },
    "keyword_match": {
        "label": "关键词匹配",
        "description": "检查文档是否包含指定关键词",
        "icon": "🔑",
        "config_fields": [
            {"key": "keyword", "label": "关键词", "type": "text", "default": ""}
        ]
    },
    "comparison": {
        "label": "字段比较",
        "description": "比较两个字段是否一致",
        "icon": "⚖️",
        "config_fields": [
            {"key": "field_a", "label": "字段A", "type": "text", "default": ""},
            {"key": "field_b", "label": "字段B", "type": "text", "default": ""}
        ]
    },
    "variable_extractor": {
        "label": "变量提取",
        "description": "从文本中提取命名变量",
        "icon": "📤",
        "config_fields": [
            {"key": "source_field", "label": "源字段", "type": "text", "default": "qr_content"},
            {"key": "pattern", "label": "提取模式", "type": "text", "default": ""}
        ]
    },
    "stamp_detection": {
        "label": "印章检测",
        "description": "检测文档中的物理印章",
        "icon": "🖊️",
        "config_fields": []
    },
    "document_diff": {
        "label": "文档比对",
        "description": "与基准文档进行差异比对",
        "icon": "📊",
        "config_fields": [
            {"key": "base_document_url", "label": "基准文档URL", "type": "text", "default": ""},
            {"key": "similarity_threshold", "label": "相似度阈值(%)", "type": "number", "default": 95}
        ]
    },
    "table_verification": {
        "label": "表格验证",
        "description": "提取表格并验证数值",
        "icon": "📋",
        "config_fields": [
            {"key": "target_column_index", "label": "目标列索引", "type": "number", "default": -1}
        ]
    },
    "url_fetch": {
        "label": "远程拉取",
        "description": "从URL获取文档",
        "icon": "🌐",
        "config_fields": [
            {"key": "url", "label": "文档URL", "type": "text", "default": ""}
        ]
    },
    "online_verification": {
        "label": "在线防伪比对 (一体化)",
        "description": "自动扫描二维码提取参数，构造URL拉取远程原件并进行差异比对",
        "icon": "🔗",
        "config_fields": [
            {"key": "regex_pattern", "label": "二维码提取正则", "type": "text", "default": "id:(?P<report_id>\\d+);(?P<verify_code>\\w+)"},
            {"key": "url_template", "label": "请求URL模板", "type": "text", "default": "https://api.example.com/check?id={{report_id}}&code={{verify_code}}"},
            {"key": "similarity_threshold", "label": "相似度报警阈值(%)", "type": "number", "default": 95}
        ]
    }
}


class VerificationModuleBase(BaseModel):
    name: str = Field(..., description="模块名称")
    description: Optional[str] = Field(None, description="模块描述")
    module_type: ModuleType = Field(..., description="模块类型")
    severity: ModuleSeverity = Field(default=ModuleSeverity.warning, description="严重级别")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置参数")
    category_id: Optional[str] = Field(None, description="关联分类ID")
    is_active: bool = Field(default=True, description="是否启用")
    sort_order: int = Field(default=0, description="排序顺序")


class VerificationModuleCreate(VerificationModuleBase):
    pass


class VerificationModuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    module_type: Optional[ModuleType] = None
    severity: Optional[ModuleSeverity] = None
    config: Optional[Dict[str, Any]] = None
    category_id: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class VerificationModuleResponse(VerificationModuleBase):
    id: str
    is_system: bool
    created_at: Optional[int] = None
    updated_at: Optional[int] = None

    class Config:
        from_attributes = True


class ModuleWithMetadata(VerificationModuleResponse):
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuleModuleAssign(BaseModel):
    """Request model for assigning modules to a rule"""
    module_ids: List[str] = Field(..., description="要关联的模块ID列表")


class RuleModulesResponse(BaseModel):
    """Response model for getting modules assigned to a rule"""
    rule_id: str
    modules: List[VerificationModuleResponse]
