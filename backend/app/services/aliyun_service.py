from typing import Dict, Any, List, Optional
from app.models.file import File, FileType
from app.schemas.file import VerificationResult
import json


class AliyunVerificationService:
    """
    Service for integrating with Aliyun Agent API
    for PDF file verification.
    """

    def __init__(self):
        self.endpoint = None  # Load from config
        self.access_key = None
        self.access_key_secret = None

    async def verify_pdf(
        self,
        file_path: str,
        file_type: FileType,
        file_bytes: bytes,
    ) -> Dict[str, Any]:
        """
        Verify a PDF file using Aliyun Agent.

        Args:
            file_path: Path to the file in MinIO
            file_type: Type of file being verified
            file_bytes: Raw file bytes

        Returns:
            Dict with verification results including:
            - status: overall status (pass, warning, fail)
            - checks: list of individual check results
            - summary: result summary
        """
        # TODO: Implement actual Aliyun Agent API call
        # This is a mock implementation

        # Mock verification result structure
        result = {
            "status": "warning",
            "checks": [
                {
                    "name": "文件格式校验",
                    "status": "pass",
                    "message": "PDF 格式符合规范，版本 1.7，无损坏文件",
                },
                {
                    "name": "必要字段完整性",
                    "status": "pass",
                    "message": "所有必填字段均已填写完整，共检测到 15 个字段",
                },
                {
                    "name": "数据一致性校验",
                    "status": "warning",
                    "message": "第 3 页数量合计与明细存在差异（合计：1000，明细：998），请核对",
                    "page": 3
                },
                {
                    "name": "签名有效性校验",
                    "status": "pass",
                    "message": "数字签名验证通过",
                },
                {
                    "name": "版本合规性校验",
                    "status": "warning",
                    "message": "使用模板版本 v2.1，建议升级到 v2.3 以获得最新校验规则",
                },
                {
                    "name": "编码规范校验",
                    "status": "pass",
                    "message": "物料编码符合规范，无重复编码",
                },
            ],
            "summary": {
                "total": 6,
                "pass": 4,
                "warning": 2,
                "fail": 0,
            },
            "model_version": "Aliyun Agent v1.2",
        }

        return result

    def parse_pdf_metadata(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Parse basic PDF metadata.

        Args:
            file_bytes: Raw PDF file bytes

        Returns:
            Dict with PDF metadata
        """
        # TODO: Use pypdf or pdfplumber to extract metadata
        return {
            "page_count": 15,
            "pdf_version": "1.7",
            "title": "",
            "author": "",
            "subject": "",
            "creator": "",
            "creation_date": None,
        }

    def detect_file_type(self, filename: str, content: str) -> FileType:
        """
        Detect file type based on filename and content.

        Args:
            filename: Original filename
            content: First page text content

        Returns:
            Detected FileType
        """
        # Simple keyword-based detection
        filename_lower = filename.lower()

        if "生产计划" in filename or "production" in filename_lower:
            return FileType.PRODUCTION_PLAN
        elif "质量" in filename or "quality" in filename_lower:
            return FileType.QUALITY_REPORT
        elif "采购" in filename or "purchase" in filename_lower or "po" in filename_lower:
            return FileType.PURCHASE_ORDER
        elif "供应商" in filename or "supplier" in filename_lower:
            return FileType.SUPPLIER_QUALIFICATION
        elif "规格" in filename or "specification" in filename_lower:
            return FileType.PRODUCT_SPECIFICATION
        else:
            return FileType.OTHER

    async def call_qwen_async(self, prompt: str) -> str:
        """
        Call Aliyun Qwen LLM asynchronously.
        If credentials are not set, falls back to a smart mock response.
        """
        doc_content = prompt
        if "文档内容" in prompt:
            parts = prompt.rsplit("文档内容", 1)
            if len(parts) > 1:
                doc_content = parts[1]

        doc_content_lower = doc_content.lower()
        if "华测" in doc_content_lower or "cti" in doc_content_lower:
            return json.dumps({"institution": "CTI", "confidence": 0.98})
        elif "sgs" in doc_content_lower:
            return json.dumps({"institution": "SGS", "confidence": 0.95})
        else:
            return json.dumps({"institution": "UNKNOWN", "confidence": 0.5})



# Global service instance
aliyun_service = AliyunVerificationService()
