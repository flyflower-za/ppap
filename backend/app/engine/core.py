import logging
from typing import List, Dict, Type
from app.models.rule import VerificationRule, RuleType
from app.engine.base import BaseOperator, DocumentContext
from app.engine.operators.qr_operator import QRScannerOperator
from app.engine.operators.signature_operator import SignatureOperator
from app.engine.operators.pdf_info_operator import PDFInfoOperator
from app.engine.operators.text_llm_operator import TextLLMOperator
from app.engine.operators.vision_llm_operator import VisionLLMOperator

logger = logging.getLogger(__name__)

class VerificationEngine:
    """
    The Orchestrator that parses rules, identifies required operators,
    executes them optimally, and evaluates the final rule logic.
    """
    def __init__(self):
        # Register available operators
        self._available_operators: Dict[str, BaseOperator] = {
            "PDFInfoExtractor": PDFInfoOperator(),
            "QRScanner": QRScannerOperator(),
            "SignatureVerifier": SignatureOperator(),
            "TextLLM": TextLLMOperator(),
            "VisionLLM": VisionLLMOperator(),
        }

    def _determine_required_operators(self, rules: List[VerificationRule]) -> List[BaseOperator]:
        """
        Analyze the AST/rule dependencies to figure out which operators must run.
        """
        required_names = set()
        for rule in rules:
            if rule.rule_type == RuleType.plugin:
                # For basic string-based plugins
                if rule.rule_content == "REQUIRE_QR_CODE":
                    required_names.add("QRScanner")
                elif rule.rule_content == "REQUIRE_SIGNATURE":
                    required_names.add("SignatureVerifier")
            
            # If logic_config has explicitly defined operator dependencies
            logic = rule.logic_config or {}
            if "depends_on" in logic:
                for op_name in logic["depends_on"]:
                    required_names.add(op_name)

        # Build list
        ops_to_run = []
        for name in required_names:
            if name in self._available_operators:
                ops_to_run.append(self._available_operators[name])
            else:
                logger.warning(f"Engine requested unknown operator: {name}")
                
        return ops_to_run

    async def run(self, context: DocumentContext, rules: List[VerificationRule]) -> Dict[str, any]:
        """
        Execute the dynamic pipeline.
        Returns the overall verification result dict to be stored in DB.
        """
        logger.info(f"[Engine] Starting dynamic verification for {context.file_path}")
        
        operators = self._determine_required_operators(rules)
        logger.info(f"[Engine] Resolved {len(operators)} required operators based on rules.")

        # Phase 1: Execute required operators
        # In the future, this can use asyncio.gather for parallel execution 
        # of independent nodes based on an execution graph.
        operator_results = {}
        for op in operators:
            logger.info(f"[Engine] Executing operator: {op.name}")
            try:
                res = await op.execute(context)
                operator_results[op.name] = res.dict()
            except Exception as e:
                logger.error(f"[Engine] Operator {op.name} crashed: {e}")
                operator_results[op.name] = {"pass_status": False, "message": str(e)}

        # Phase 2: Evaluate Rules
        rule_evaluations = []
        pass_count = warning_count = fail_count = 0
        needs_review = False

        for rule in rules:
            rule_pass = False
            rule_msg = "未执行"
            confidence = 1.0

            if rule.rule_type == RuleType.plugin:
                if rule.rule_content == "REQUIRE_QR_CODE":
                    qr_data = context.shared_state.get("qr_codes", [])
                    if len(qr_data) > 0:
                        rule_pass = True
                        rule_msg = f"通过：检测到 {len(qr_data)} 个二维码"
                    else:
                        rule_msg = "未通过：未在页面上发现追溯二维码"

                elif rule.rule_content == "REQUIRE_SIGNATURE":
                    sig_data = context.shared_state.get("digital_signatures", {})
                    is_signed = sig_data.get("signed", False)
                    sigs = sig_data.get("signatures", [])
                    valid_sigs = [s for s in sigs if s.get("integrity", False)]
                    
                    if valid_sigs:
                        rule_pass = True
                        rule_msg = "通过：检测到合法的数字签名"
                    else:
                        rule_msg = "未通过：该文档缺失强制要求的合法数字签名"
            elif rule.rule_type == RuleType.llm_prompt:
                # Text LLM evaluation fallback
                llm_results = context.shared_state.get("llm_semantic_analysis", [])
                if llm_results:
                    # For simplicity in Phase 2, take the latest execution that matches this rule's intent
                    res = llm_results[-1]
                    rule_pass = res.get("passed", False)
                    rule_msg = res.get("reason", "大模型分析未返回原因。")
                    confidence = res.get("confidence", 1.0)
                else:
                    rule_msg = "未通过：未获得大模型分析结果"
            else:
                # Fallback for old rule types (keyword, regex, llm) 
                # This logic can be moved to dedicated TextOperators later
                rule_msg = f"引擎尚未适配该规则类型 ({rule.rule_type})"
                rule_pass = False

            # Tally stats
            if rule_pass:
                pass_count += 1
            else:
                if rule.severity == "warning":
                    warning_count += 1
                else:
                    fail_count += 1

            # Check if confidence is low enough to trigger human review
            if confidence < 0.85:
                needs_review = True

            rule_evaluations.append({
                "rule_name": rule.rule_name,
                "rule_type": rule.rule_type.value,
                "passed": rule_pass,
                "message": rule_msg,
                "severity": rule.severity.value,
                "confidence": confidence
            })

        logger.info(f"[Engine] Verification complete. Pass:{pass_count}, Fail:{fail_count}")

        return {
            "checks": rule_evaluations,
            "operator_logs": operator_results,
            "pass_count": pass_count,
            "warning_count": warning_count,
            "fail_count": fail_count,
            "needs_review": needs_review
        }
