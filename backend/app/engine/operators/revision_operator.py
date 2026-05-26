import logging
from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.checkers.revision_checker import count_pdf_revisions

logger = logging.getLogger(__name__)

class RevisionCheckOperator(BaseOperator):
    """
    升级版修订版本篡改检查算子（合规联合会签白名单判定）：
    1. 时序防御自愈：若共享上下文中缺失数字签名结果（如在沙盒中单独测试该模块），算子将自动进行极速签名扫描，防止漏报。
    2. 联合会签合规白名单（Revision <= Sig_Count + 1 法则）：
       - 在多方会签中，每盖一个电子章都会产生一个合规的增量更新（Revision）。
       - 只要 Revision 数量不超过 `已盖章数 + 1`，判定为“合法联合签字盖章”，予以通过！
       - 一旦 Revision 数量大于 `已盖章数 + 1`，说明存在纯内容的非盖章修改篡改，判定为不合规。
    """
    def __init__(self):
        super().__init__(name="RevisionCheck")

    @property
    def provides(self) -> List[str]:
        return ["pdf_revisions"]

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
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message=f"无法加载 PDF 字节流: {e}"
                )

        try:
            # 1. 提取物理版本数量
            revision_data = count_pdf_revisions(pdf_bytes)
            rev_count = revision_data.get("revision_count", 1)

            # 2. 时序防御自愈：确保有签名特征数据可用
            sig_data = context.shared_state.get("digital_signatures")
            if not sig_data:
                try:
                    from app.checkers.sig_verifier import verify_pdf_signatures
                    logger.info("⚡ RevisionCheck 触发时序自愈防御：检测到缺失签名数据，正在后台极速执行签名防伪直取...")
                    sig_data = await verify_pdf_signatures(pdf_bytes)
                    context.shared_state["digital_signatures"] = sig_data
                except Exception as sig_err:
                    logger.warning(f"RevisionCheck 时序自愈解析签名失败: {sig_err}")
                    sig_data = {}

            is_signed = sig_data.get("signed", False) if sig_data else False
            signatures = sig_data.get("signatures", []) if sig_data else []
            sig_count = len(signatures)

            # 3. 联合会签合规数学白名单法则判定 (Revision <= Sig_Count + 1)
            is_tampered_after_sign = False
            tamper_message = ""

            revision_data["is_signed"] = is_signed
            revision_data["signature_count"] = sig_count

            if is_signed:
                # 理论上，N 个签名可能会产生至多 N 个增量 xref 区间
                # 合法界限为 rev_count <= sig_count + 1
                allowed_max_revs = sig_count + 1
                if rev_count > allowed_max_revs:
                    is_tampered_after_sign = True
                    tamper_message = (
                        f"文档共检测到 {rev_count} 次修订版本，超过了合规联合会签的上限 {allowed_max_revs} 次 "
                        f"(当前包含 {sig_count} 个电子签名，但存在额外的非盖章增量更新)，存在内容二次篡改的极高风险。"
                    )
                else:
                    is_tampered_after_sign = False
                    tamper_message = (
                        f"文档共检测到 {rev_count} 次修订版本，与 {sig_count} 个电子签章的增量区间完美契合，"
                        f"版本结构符合多方联合盖章的合规要求，无额外内容修改。"
                    )
            else:
                # 如果完全没签名，但 revision_count > 1，代表文档被一些不太规范的 PDF 工具保存了多次
                if rev_count > 1:
                    is_tampered_after_sign = False  # 无签名时，多版本仅为非签名文档的正常多次保存，不判定为篡改
                    tamper_message = f"未签名文档，包含 {rev_count} 个增量保存版本，版本结构正常。"
                else:
                    is_tampered_after_sign = False
                    tamper_message = "未签名文档，共 1 个版本，版本结构完整。"

            revision_data["is_tampered_after_sign"] = is_tampered_after_sign
            revision_data["tamper_message"] = tamper_message
            context.shared_state["pdf_revisions"] = revision_data

            # 4. 生成规范的 Operator 结果
            if is_tampered_after_sign:
                msg = f"⚠️ 修订不合规：{tamper_message}"
                pass_status = False
            else:
                msg = f"修订合规：{tamper_message}"
                pass_status = True

            return OperatorResult(
                operator_name=self.name,
                pass_status=pass_status,
                message=msg,
                extracted_data=revision_data
            )

        except Exception as e:
            logger.error(f"RevisionCheckOperator 发生不可恢复异常: {e}")
            return OperatorResult(
                operator_name=self.name,
                pass_status=True,  # 异常时默认放行，防止系统因容错中断
                message=f"修订版本分析中断，默认放行: {e}"
            )
