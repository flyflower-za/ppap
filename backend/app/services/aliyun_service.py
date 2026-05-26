from typing import Dict, Any, List, Optional
from app.models.file import File, FileType
from app.schemas.file import VerificationResult
import json
import logging
import httpx


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
        Uses database-stored AI model profiles.
        Falls back to environment variables for backward compatibility.
        If no credentials are configured, falls back to a smart mock response.
        """
        logger = logging.getLogger(__name__)

        # Try to load AI config from database first
        ai_config = await self._load_ai_config()

        # If AI config is enabled and has credentials, use it
        if ai_config.get("enabled") and ai_config.get("api_key"):
            try:
                return await self._call_real_llm_api(prompt, ai_config)
            except Exception as e:
                logger.warning(f"LLM API call failed: {e}, falling back to mock")

        # Improved fallback algorithm with institution detection patterns
        doc_content = prompt
        if "文档内容" in prompt:
            parts = prompt.rsplit("文档内容", 1)
            if len(parts) > 1:
                doc_content = parts[1]

        # Comprehensive institution detection patterns
        institution_patterns = {
            "CTI": ["华测", "华测检测", "CTI", "centre testing international"],
            "SGS": ["SGS", "sgs", "通标标准", "通标"],
            "TUV": ["TUV", "tuv", "莱茵", "TÜV"],
            "INTERTEK": ["INTERTEK", "Intertek", "天祥"],
            "BV": ["BV", "bureau veritas", "必维", "必维国际检验"],
            "UL": ["UL", "underwriters laboratories", "保险商实验室"],
            "CSA": ["CSA", "加拿大标准协会"],
            "PONY": ["PONY", "谱尼测试", "谱尼"],
            "CTI": ["中检", "中国检验认证", "CCIC"],  # Adding CCIC patterns
        }

        doc_content_lower = doc_content.lower()

        # Score-based detection with confidence calculation
        best_match = {"institution": "UNKNOWN", "confidence": 0.0, "matches": 0}

        for institution, patterns in institution_patterns.items():
            match_count = 0
            for pattern in patterns:
                if pattern.lower() in doc_content_lower:
                    match_count += 1

            if match_count > 0:
                # Calculate confidence based on number of matches and content richness
                base_confidence = 0.6 + (match_count * 0.15)  # Base 0.6, +0.15 per match

                # Boost confidence if document has substantial content
                if len(doc_content) > 500:
                    base_confidence += 0.1

                # Cap at 0.95 (leave room for LLM to be more confident)
                confidence = min(base_confidence, 0.95)

                if match_count > best_match["matches"] or \
                   (match_count == best_match["matches"] and confidence > best_match["confidence"]):
                    best_match = {
                        "institution": institution,
                        "confidence": confidence,
                        "matches": match_count
                    }

        # If no clear pattern found, try to extract from header/footer
        if best_match["institution"] == "UNKNOWN":
            # Look for company indicators
            company_indicators = ["公司", "有限公司", "厂", "企业", "集团"]
            for indicator in company_indicators:
                if indicator in doc_content:
                    # Try to extract company name from context
                    lines = doc_content.split('\n')
                    for i, line in enumerate(lines):
                        if indicator in line:
                            # Extract surrounding context as company name
                            start = max(0, i-1)
                            end = min(len(lines), i+2)
                            company_context = ''.join(lines[start:end])
                            # Clean up and use as institution
                            company_name = company_context.strip()[:20]  # Limit length
                            best_match = {
                                "institution": f"检测机构({company_name})",
                                "confidence": 0.4,  # Lower confidence for extracted names
                                "matches": 1
                            }
                            break
                    if best_match["institution"] != "UNKNOWN":
                        break

        # If still unknown, return with low confidence
        if best_match["institution"] == "UNKNOWN":
            best_match["confidence"] = 0.3

        return json.dumps({
            "institution": best_match["institution"],
            "confidence": best_match["confidence"]
        })



    async def _load_ai_config(self) -> dict:
        """
        Load AI model config from database profiles.
        Falls back to environment variables for backward compatibility.
        """
        try:
            from app.core.database import async_session_maker
            from app.models.setting import Setting
            async with async_session_maker() as session:
                # Try to load from profiles first
                profiles_row = await session.get(Setting, "ai_model_profiles")
                if profiles_row:
                    profiles = json.loads(profiles_row.value)
                    # Find enabled text model (prefer text, fallback to both)
                    text_models = [
                        p for p in profiles
                        if p.get("enabled") and p.get("model_type") in ("text", "both")
                    ]
                    if text_models:
                        # Prefer default text model
                        default = next((p for p in text_models if p.get("is_default_text")), None)
                        chosen = default or text_models[0]
                        return {
                            "enabled": True,
                            "api_key": chosen.get("api_key"),
                            "base_url": chosen.get("base_url", "https://api.openai.com/v1"),
                            "model_name": chosen.get("model_name", "gpt-3.5-turbo"),
                            "max_tokens": chosen.get("max_tokens", 2048),
                            "temperature": chosen.get("temperature", 0.1),
                        }

                # Fallback to legacy single config
                legacy_row = await session.get(Setting, "ai_model_config")
                if legacy_row:
                    return json.loads(legacy_row.value)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not load AI config from DB: {e}")

        # Final fallback to environment variables
        from app.core.config import settings
        if settings.ALIYUN_ACCESS_KEY_ID and settings.ALIYUN_AGENT_ENDPOINT:
            return {
                "enabled": True,
                "api_key": settings.ALIYUN_ACCESS_KEY_ID,
                "base_url": settings.ALIYUN_AGENT_ENDPOINT,
                "model_name": settings.ALIYUN_MODEL_NAME if hasattr(settings, 'ALIYUN_MODEL_NAME') else "gpt-3.5-turbo",
                "max_tokens": 2048,
                "temperature": 0.1,
            }

        return {}

    async def _call_real_llm_api(self, prompt: str, ai_config: dict) -> str:
        """
        Call OpenAI-compatible LLM API with configured credentials.
        Supports various providers: OpenAI, Azure, local models, third-party services.
        """
        logger = logging.getLogger(__name__)

        try:
            return await self._call_openai_compatible_api(prompt, ai_config)
        except Exception as e:
            logger.error(f"OpenAI-compatible API call failed: {e}")
            raise

    async def _call_openai_compatible_api(self, prompt: str, ai_config: dict) -> str:
        """
        Call OpenAI-compatible API.
        This works with any provider that implements the OpenAI API standard.
        """
        from openai import AsyncOpenAI

        # Create client with configured credentials
        client = AsyncOpenAI(
            api_key=ai_config.get("api_key"),
            base_url=ai_config.get("base_url", "https://api.openai.com/v1")
        )

        # Smart system prompt for institution detection
        system_prompt = """你是一个专业的文档分析助手，专门识别文档签发机构。

请分析用户提供的文档内容，识别文档是由哪个机构签发的（如华测检测CTI、SGS检测、TUV莱茵等）。

请务必严格按照JSON格式返回结果，不要包含任何其他文字：
{
  "institution": "机构名称（如'CTI'、'SGS'等，不确定时返回'UNKNOWN'）",
  "confidence": 0.0到1.0之间的置信度数值
}

只返回JSON，不要包含解释性文字。"""

        try:
            response = await client.chat.completions.create(
                model=ai_config.get("model_name", "gpt-3.5-turbo"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=ai_config.get("max_tokens", 800),
                temperature=ai_config.get("temperature", 0.1),
                response_format={"type": "json_object"}  # Request JSON response
            )

            result = response.choices[0].message.content
            logger.info(f"LLM API call successful, response: {result[:100]}...")
            return result

        except Exception as e:
            logger.error(f"OpenAI-compatible API error: {e}")
            raise


# Global service instance
aliyun_service = AliyunVerificationService()
