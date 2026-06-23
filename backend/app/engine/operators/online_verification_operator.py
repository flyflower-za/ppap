import logging
import re
from typing import List, Any
from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.engine.operators.diff_operator import DocumentDiffOperator

logger = logging.getLogger(__name__)

class OnlineVerificationOperator(BaseOperator):
    """
    一体化在线防伪比对算子：
    1. 获取二维码内容
    2. 使用正则提取关键参数
    3. 组装远程拉取URL
    4. 调用文档差异比对模块进行下载和文本/视觉对比
    """
    def __init__(self):
        super().__init__(name="OnlineVerificationOperator")

    @property
    def provides(self) -> List[str]:
        return ["online_verification_result"]

    @property
    def requires(self) -> List[str]:
        return ["qr_codes"]

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        regex_pattern = kwargs.get("regex_pattern", "")
        url_template = kwargs.get("url_template", "")
        similarity_threshold = kwargs.get("similarity_threshold", 95.0)

        # 1. 获取二维码
        qr_data = context.shared_state.get("qr_codes", [])
        if not qr_data:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message="在线防伪失败：文档中未检测到二维码。"
            )

        # 获取第一个二维码内容
        qr_content = qr_data[0].get("data", "") if isinstance(qr_data[0], dict) else str(qr_data[0])
        
        if not qr_content:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message="在线防伪失败：二维码内容为空。"
            )

        # 2. 正则提取参数
        try:
            pattern = re.compile(regex_pattern)
        except Exception as e:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"在线防伪异常：提取正则配置错误 ({e})。"
            )

        match = pattern.search(qr_content)
        if not match:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"在线防伪失败：二维码内容未匹配提取规则。\n内容: {qr_content}\n正则: {regex_pattern}"
            )

        extracted_vars = match.groupdict()
        if not extracted_vars:
            # 如果没有命名捕获组，提供一个通用的 fallback
            extracted_vars = {"matched": match.group(0)}

        # 3. 组装 URL
        formatted_url = url_template
        for key, val in extracted_vars.items():
            formatted_url = formatted_url.replace(f"{{{{{key}}}}}", str(val))

        logger.info(f"[OnlineVerification] Formatted URL: {formatted_url}")

        # 4. 调用原件比对
        try:
            diff_op = DocumentDiffOperator()
            diff_result = await diff_op.execute(
                context, 
                base_document_url=formatted_url, 
                similarity_threshold=similarity_threshold
            )
            
            # 返回 Diff 算子的比对结果
            return OperatorResult(
                operator_name=self.name,
                pass_status=diff_result.pass_status,
                message=f"在线防伪比对完成 (目标URL: {formatted_url})\n{diff_result.message}",
                extracted_data=diff_result.extracted_data
            )
        except Exception as e:
            logger.exception("OnlineVerification Diff error")
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"在线防伪异常：拉取或比对原件失败 ({e})。"
            )
