"""
Operator Registry - 算子注册表模型
维护系统中所有可用检测算子的元数据、配置参数和使用说明
"""
from sqlalchemy import Column, String, Boolean, JSONB, ForeignKey, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class OperatorRegistry(Base):
    """算子注册表 - 定义所有可用的检测算子"""
    __tablename__ = "operator_registry"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    operator_key = Column(String(100), unique=True, nullable=False)  # 如: "digital_signature", "qr_scanner"
    display_name = Column(String(200), nullable=False)  # 如: "数字签名验证"

    # 算子分类
    category = Column(String(50))  # "verification" | "extraction" | "comparison" | "external_call"

    # 功能说明
    description = Column(Text)

    # 算子类型
    operator_type = Column(String(50))  # "native" | "llm" | "http" | "plugin"

    # 配置参数定义 (JSON Schema 格式)
    parameters_schema = Column(JSONB, default=dict)

    # 输出数据结构定义
    output_schema = Column(JSONB, default=dict)

    # 是否支持 severity 配置
    supports_severity = Column(Boolean, default=True)

    # 默认严重级别
    default_severity = Column(String(20), default="fail")  # "fail" | "warning" | "review" | "reference"

    # 执行优先级 (数字越小优先级越高)
    priority = Column(Integer, default=100)

    # 是否为高能耗算子 (需要在 Stage 2 执行)
    is_heavy = Column(Boolean, default=False)

    # 算子状态
    is_active = Column(Boolean, default=True)
    is_deprecated = Column(Boolean, default=False)
    deprecated_by = Column(String(100))  # 推荐使用的替代算子

    # 版本信息
    version = Column(String(20), default="1.0.0")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OperatorTemplate(Base):
    """预定义的算子配置模板"""
    __tablename__ = "operator_templates"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    operator_key = Column(String(100), nullable=False)  # 关联到 OperatorRegistry

    # 预配置的参数
    preset_parameters = Column(JSONB, default=dict)

    # 适用场景描述
    use_case_description = Column(Text)

    # 是否为系统预设
    is_system = Column(Boolean, default=False)

    created_by = Column(UUID, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


# 预置算子注册数据 (初始化脚本使用)
INITIAL_OPERATORS = [
    {
        "operator_key": "digital_signature",
        "display_name": "数字签名验证",
        "category": "verification",
        "description": "验证 PDF 文档的数字签名完整性、签发者信息和证书有效期",
        "operator_type": "native",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "expectedIssuer": {"type": "string", "description": "预期签发者名称"}
            }
        },
        "supports_severity": True,
        "default_severity": "fail",
        "priority": 10,
        "is_heavy": True
    },
    {
        "operator_key": "qr_scanner",
        "display_name": "二维码识别",
        "category": "verification",
        "description": "扫描并解析 PDF 文档中的二维码内容",
        "operator_type": "native",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "required": {"type": "boolean", "description": "是否必须存在二维码"}
            }
        },
        "supports_severity": True,
        "default_severity": "warning",
        "priority": 20,
        "is_heavy": True
    },
    {
        "operator_key": "revision_check",
        "display_name": "文档篡改检测",
        "category": "verification",
        "description": "检测 PDF 签名后是否存在修订版本，判断文档是否被篡改",
        "operator_type": "native",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "maxRevisions": {"type": "integer", "description": "允许的最大修订版本数"},
                "allowIncrementalUpdates": {"type": "boolean", "description": "是否允许增量更新"}
            }
        },
        "supports_severity": True,
        "default_severity": "fail",
        "priority": 15,
        "is_heavy": True
    },
    {
        "operator_key": "institution_sniffer",
        "display_name": "发证机构识别",
        "category": "extraction",
        "description": "从文档文本中智能识别发证/签发机构名称",
        "operator_type": "native",
        "parameters_schema": {},
        "supports_severity": False,
        "priority": 1,
        "is_heavy": False
    },
    {
        "operator_key": "text_llm",
        "display_name": "文本大模型分析",
        "category": "verification",
        "description": "使用大语言模型对文档文本进行语义理解和验证",
        "operator_type": "llm",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "分析提示词"},
                "operation_mode": {"type": "string", "enum": ["verification", "extraction"]}
            }
        },
        "supports_severity": True,
        "default_severity": "review",
        "priority": 50,
        "is_heavy": True
    },
    {
        "operator_key": "http_call",
        "display_name": "外部 HTTP 验证",
        "category": "external_call",
        "description": "调用外部 HTTP API 进行数据验证",
        "operator_type": "http",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "url_template": {"type": "string"},
                "http_method": {"type": "string", "enum": ["GET", "POST", "PUT"]},
                "success_type": {"type": "string", "enum": ["status_2xx", "json_path", "text_contains"]}
            }
        },
        "supports_severity": True,
        "default_severity": "fail",
        "priority": 60,
        "is_heavy": True
    }
]
