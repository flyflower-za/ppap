"""
Operator Registry - 算子注册表模型
维护系统中所有可用检测算子的元数据、配置参数和使用说明
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
        "output_schema": {
            "type": "object",
            "properties": {
                "signer_cn": {"type": "string", "description": "签署人名称"},
                "signature_valid": {"type": "boolean", "description": "签名是否有效"},
                "digital_signatures": {"type": "object", "description": "完整数字签名数据结构"}
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
        "output_schema": {
            "type": "object",
            "properties": {
                "qr_content": {"type": "string", "description": "首个二维码内容"},
                "qr_codes": {"type": "array", "description": "所有二维码数据列表"}
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
        "output_schema": {
            "type": "object",
            "properties": {
                "is_tampered": {"type": "boolean", "description": "文档是否遭到篡改"},
                "revision_count": {"type": "integer", "description": "修订版本总数"}
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
        "output_schema": {
            "type": "object",
            "properties": {
                "institution": {"type": "string", "description": "识别归类的发证机构简称"}
            }
        },
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
        "output_schema": {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean", "description": "分析或验证是否符合要求"},
                "reason": {"type": "string", "description": "分析结论或解释说明"}
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
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "integer", "description": "HTTP 响应状态码"},
                "response_text": {"type": "string", "description": "原始响应文本内容"},
                "response_json": {"type": "object", "description": "解析后的 JSON 响应对象"},
                "passed": {"type": "boolean", "description": "是否符合请求成功条件"}
            }
        },
        "supports_severity": True,
        "default_severity": "fail",
        "priority": 60,
        "is_heavy": True
    },
    {
        "operator_key": "variable_extractor",
        "display_name": "正则变量提取器",
        "category": "extraction",
        "description": "使用正则表达式（支持命名捕获组）从二维码内容或文本中提取变量并注入上下文",
        "operator_type": "native",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "source_field": {"type": "string", "enum": ["qr_content", "full_text"], "description": "提取源数据字段"},
                "pattern": {"type": "string", "description": "用于提取变量的正则表达式（例如：(?P<report_number>\\d+)）"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "extracted_value": {"type": "string", "description": "全局捕获所得的匹配字符串值"}
            }
        },
        "supports_severity": False,
        "priority": 25,
        "is_heavy": False
    },
    {
        "operator_key": "document_diff",
        "display_name": "原件一致性比对",
        "category": "comparison",
        "description": "通过 URL 获取基准原件 PDF 并与当前上传 PDF 执行行级段落文本比对",
        "operator_type": "native",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "base_document_url": {"type": "string", "description": "基准文档 URL 模板，支持变量插值（例如：https://verify.example.com/docs/{{report_number}}）"},
                "similarity_threshold": {"type": "number", "description": "相似度阈值百分比（例如：95.0）"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean", "description": "比对相似度是否满足阈值要求"},
                "message": {"type": "string", "description": "比对差异结果详情或成功说明"},
                "similarity": {"type": "number", "description": "最终段落行级计算相似度百分比"}
            }
        },
        "supports_severity": True,
        "default_severity": "fail",
        "priority": 30,
        "is_heavy": True
    },
    {
        "operator_key": "template_formatter",
        "display_name": "文本拼接/格式化",
        "category": "extraction",
        "description": "将上游节点的提取字段与预置模板进行文本拼接和格式化组合",
        "operator_type": "native",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "template": {"type": "string", "description": "拼接模板，支持使用上游节点变量（例如：https://example/api/{{#regex_node.id#}}）"}
            },
            "required": ["template"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "formatted_result": {"type": "string", "description": "格式化拼接后的文本结果"}
            }
        },
        "supports_severity": False,
        "priority": 26,
        "is_heavy": False
    }
]
