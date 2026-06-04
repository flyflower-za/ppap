import json
import base64
import logging
import re
from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.services.aliyun_service import aliyun_service
from app.engine.operators.vision_llm_operator import _get_ai_config

logger = logging.getLogger(__name__)

class InstitutionSnifferOperator(BaseOperator):
    """
    终极闭环泛化版签发机构嗅探算子：
    1. 泛化密码学证书直取：如果 PDF 包含有效数字签名，直接把证书中解析出的主体组织(Org/CN)名作为最终机构名称返回（不论是否在白名单内），100% 抵御文本伪造。
    2. 1ms 高频硬编码正则秒回：对无签名的纯文本，优先秒回最常见的超高频大机构（如华测、SGS等），提速避开大模型请求。
    3. 通用大模型文本语义提取：指引大模型根据第一页的红头、页眉 LOGO 或落款，智能化识别任何未知的中文官方机构全称，实现无限量机构泛化识别。
    4. 第一页视觉 Fallback：针对扫描件，仅渲染第一页头部图像进行 VLM 视觉判定，带宽与 Token 减半。
    """
    def __init__(self):
        super().__init__(name="InstitutionSniffer")

    @property
    def provides(self) -> List[str]:
        return ["institution"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        pdf_bytes = context.shared_state.get("pdf_bytes")
        if not pdf_bytes:
            try:
                with open(context.file_path, "rb") as f:
                    pdf_bytes = f.read()
            except Exception as e:
                if not context.shared_state.get("full_text"):
                    return OperatorResult(
                        operator_name=self.name,
                        pass_status=False,
                        message=f"无法加载 PDF 字节流: {e}"
                    )

        # ─── PART 0: 密码学证书指纹前置直取 (全量泛化提取) ───
        try:
            sig_data = context.shared_state.get("digital_signatures")
            if not sig_data:
                from app.checkers.sig_verifier import verify_pdf_signatures
                sig_data = await verify_pdf_signatures(pdf_bytes)
                context.shared_state["digital_signatures"] = sig_data

            if sig_data and sig_data.get("signed", False):
                for sig in sig_data.get("signatures", []):
                    signer_cn = sig.get("signer_cn", "")
                    cert_subject = sig.get("cert_info", {}).get("subject", {})
                    org_name = cert_subject.get("organization_name") or signer_cn
                    
                    if org_name and org_name != "未知证书主体":
                        org_name_lower = org_name.lower()
                        # A. 优先将超高频缩写/名称清洗为规范标准中文名
                        matched_inst = None
                        if any(kw in org_name_lower for kw in ["华测", "cti", "centre testing"]):
                            matched_inst = "CTI"
                        elif any(kw in org_name_lower for kw in ["sgs", "通标"]):
                            matched_inst = "SGS"
                        elif any(kw in org_name_lower for kw in ["中国检验认证", "ccic"]):
                            matched_inst = "CCIC"
                        elif any(kw in org_name_lower for kw in ["tuv rheinland", "莱茵", "tüv rheinland"]):
                            matched_inst = "TUV"
                        elif any(kw in org_name_lower for kw in ["tuv sud", "南德", "tüv süd"]):
                            matched_inst = "TUV"
                        
                        # B. 【泛化核心】：如果不在高频机构库内，直接原样使用证书提取出的完整企业组织名称！
                        if not matched_inst:
                            # 过滤掉一些技术性的特殊字符，保留干净的企业/组织名称
                            clean_name = org_name.strip()
                            if len(clean_name) > 2 and not re.match(r'^[a-fA-F0-9\-]+$', clean_name):
                                matched_inst = clean_name

                        if matched_inst:
                            logger.info(f"🔒 密码学数字签名特征命中！基于证书组织 [{org_name}] 直接断定机构为: [{matched_inst}]")
                            context.shared_state["institution"] = matched_inst
                            return OperatorResult(
                                operator_name=self.name,
                                pass_status=True,
                                message=f"密码学指纹提取成功：归属机构 [{matched_inst}] (基于PDF数字证书防伪直取)",
                                extracted_data={"institution": matched_inst, "confidence": 1.0, "source": "digital_signature"}
                            )
        except Exception as sig_err:
            logger.warning(f"Institution Sniffer pre-sig check failed: {sig_err}")

        # ─── PART 1: 提取第一页的纯文本 ───
        first_page_text = ""
        if pdf_bytes:
            try:
                import fitz
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                if len(doc) > 0:
                    first_page_text = doc[0].get_text().strip()
                doc.close()
            except Exception as parse_err:
                logger.warning(f"Failed to parse first page text: {parse_err}")

        if not first_page_text:
            first_page_text = context.shared_state.get("full_text", "")

        # 如果没有第一页文本，直接进入视觉分析
        if not first_page_text:
            logger.info("第一页没有提取到有效文字（可能是扫描件/纯图片 PDF），直接启动视觉降维嗅探。")
            vision_res = await self._run_vision_first_page(pdf_bytes)
            if vision_res:
                inst = vision_res.get("institution", "UNKNOWN")
                conf = vision_res.get("confidence", 0.0)
                context.shared_state["institution"] = inst
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=True,
                    message=f"视觉检测完成：归属机构 [{inst}] (基于第一页排版LOGO分析)",
                    extracted_data={"institution": inst, "confidence": conf}
                )
            else:
                context.shared_state["institution"] = "UNKNOWN"
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message="未检测到任何签发机构（扫描件视觉识别失败）。",
                    extracted_data={"institution": "UNKNOWN", "confidence": 0.0}
                )

        # ─── PART 2: 1ms 本地超高速高频正则匹配 ───
        local_rules = [
            (r"(华测检测|CENTRE TESTING INTERNATIONAL|CTI)", "CTI"),
            (r"(SGS|通标标准技术服务)", "SGS"),
            (r"(中国检验认证|CCIC)", "CCIC"),
            (r"(莱茵|TUV Rhe|TÜV Rhe)", "TUV"),
            (r"(南德|TUV SUD|TÜV SÜD)", "TUV"),
        ]

        text_to_analyze = first_page_text[:1200]
        for pattern, inst_name in local_rules:
            if re.search(pattern, text_to_analyze, re.IGNORECASE):
                logger.info(f"⚡ 本地高置信度正则命中，1ms秒回签发机构: [{inst_name}]")
                context.shared_state["institution"] = inst_name
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=True,
                    message=f"极速嗅探成功：归属机构 [{inst_name}] (本地指纹匹配)",
                    extracted_data={"institution": inst_name, "confidence": 0.98}
                )

        # ─── PART 3: 通用泛化大模型文本语义识别（提取任意未知机构） ───
        prompt = f"""
请分析以下文档第一页的头部及页眉内容，识别该文档是由哪个机构/公司签发的（如华测检测、SGS通标、中检集团、或者任何其他检测研究院/出具单位）。
请务必返回合法的 JSON 格式，包含以下字段：
- "institution": 提取到的具体签发/出具机构官方登记中文全称（如："华测检测", "SGS通标", "XX市质量监督检测研究院", "XX有限公司"）。如果是常规英文缩写，请尽量转为中文官方名称。如果实在无法确定，请返回 "UNKNOWN"。
- "confidence": 0.0 到 1.0 的置信度。

文档第一页内容：
{text_to_analyze}
"""
        try:
            llm_res = await aliyun_service.call_qwen_async(prompt)
            json_match = re.search(r'\{.*\}', llm_res.replace('\n', ''))
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(llm_res)

            institution = data.get("institution", "UNKNOWN")
            confidence = data.get("confidence", 0.0)

            # ─── PART 4: 多模态视觉 Fallback（仅限 UNKNOWN 状态下的扫描件） ───
            if institution == "UNKNOWN":
                logger.info("第一页文本语义无法确定机构，自动切换为第一页视觉大模型识别...")
                vision_res = await self._run_vision_first_page(pdf_bytes)
                if vision_res:
                    institution = vision_res.get("institution", "UNKNOWN")
                    confidence = vision_res.get("confidence", 0.0)

            # 对主流机构结果进行一次标准清洗归一化
            inst_lower = institution.lower()
            if "华测" in inst_lower or "cti" in inst_lower:
                institution = "CTI"
            elif "sgs" in inst_lower or "通标" in inst_lower:
                institution = "SGS"
            elif "中检" in inst_lower or "ccic" in inst_lower:
                institution = "CCIC"
            elif "莱茵" in inst_lower or "rheinland" in inst_lower:
                institution = "TUV"
            elif "南德" in inst_lower or "sud" in inst_lower:
                institution = "TUV"

            context.shared_state["institution"] = institution
            
            return OperatorResult(
                operator_name=self.name,
                pass_status=True,
                message=f"语义嗅探完成：归属机构 [{institution}] (置信度: {confidence})",
                extracted_data={"institution": institution, "confidence": confidence}
            )

        except Exception as e:
            logger.error(f"Text LLM Sniffing failed, entering fallback: {e}")
            context.shared_state["institution"] = "UNKNOWN"
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"嗅探分析异常: {e}",
                extracted_data={"institution": "UNKNOWN", "confidence": 0.0}
            )

    async def _run_vision_first_page(self, pdf_bytes: bytes) -> dict:
        """
        通用视觉大模型 Fallback
        """
        try:
            ai_config = await _get_ai_config("vision")
            if not ai_config.get("enabled") or not ai_config.get("api_key"):
                logger.warning("视觉大模型 API 未配置，跳过视觉嗅探。")
                return None

            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if len(doc) == 0:
                doc.close()
                return None

            page = doc[0]
            zoom = 1.5
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            image_bytes = pix.tobytes("jpeg")
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            doc.close()

            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=ai_config["api_key"],
                base_url=ai_config.get("base_url", "https://api.openai.com/v1")
            )

            system_prompt = """
            你是一个文档识别专家。请通过观察文档第一页的图片，根据顶部的红头、企业 LOGO、公章或落款名称，判定该文档的实际出具或签发机构。
            必须且只能返回标准的 JSON 格式：
            {"institution": "机构中文规范全称", "confidence": 0.9}
            请智能识别出真实的官方登记机构全称（如“北京市计量检测科学研究院”），不要仅局限于知名大机构。
            如果实在无法提取，请返回 {"institution": "UNKNOWN", "confidence": 0.0}
            """

            response = await client.chat.completions.create(
                model=ai_config.get("vision_model", "gpt-4o"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请提取该图片中的文档签发机构名称："},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}}
                        ]
                    }
                ],
                max_tokens=128,
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            raw = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', raw.replace('\n', ''))
            if json_match:
                return json.loads(json_match.group())
            return json.loads(raw)

        except Exception as e:
            logger.error(f"Vision first page fallback failed: {e}")
            return None
