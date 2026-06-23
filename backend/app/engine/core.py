import logging
from typing import List, Dict, Type, Optional
from app.models.rule import VerificationRule, RuleType, Severity
from app.models.verification_module import VerificationModule, ModuleType, ModuleSeverity
from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.engine.operators.qr_operator import QRScannerOperator
from app.engine.operators.signature_operator import SignatureOperator
from app.engine.operators.pdf_info_operator import PDFInfoOperator
from app.engine.operators.text_llm_operator import TextLLMOperator
from app.engine.operators.vision_llm_operator import VisionLLMOperator
from app.engine.operators.sniffer_operator import InstitutionSnifferOperator
from app.engine.operators.revision_operator import RevisionCheckOperator
from app.engine.operators.url_fetch_operator import URLFetchOperator
from app.engine.operators.stamp_operator import StampDetectionOperator
from app.engine.operators.diff_operator import DocumentDiffOperator
from app.engine.operators.table_operator import TableVerificationOperator

logger = logging.getLogger(__name__)

def normalize_institution_name(name: str) -> str:
    if not name:
        return "unknown"
    name_lower = name.strip().lower()
    if any(kw in name_lower for kw in ["华测", "cti", "centre testing"]):
        return "cti"
    if any(kw in name_lower for kw in ["sgs", "通标"]):
        return "sgs"
    if any(kw in name_lower for kw in ["中检", "ccic", "中国检验认证"]):
        return "ccic"
    if any(kw in name_lower for kw in ["莱茵", "rheinland", "tuv rhe", "tüv rhe", "南德", "sud", "tuv sud", "tüv süd", "tuv"]):
        return "tuv"
    return name_lower

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
            "InstitutionSniffer": InstitutionSnifferOperator(),
            "RevisionCheck": RevisionCheckOperator(),
            "URLFetchOperator": URLFetchOperator(),
            "StampDetection": StampDetectionOperator(),
            "DocumentDiff": DocumentDiffOperator(),
            "TableVerification": TableVerificationOperator(),
        }

    def _flatten_shared_state(self, context: DocumentContext) -> None:
        """
        Flatten commonly used nested values from shared_state for easier variable access.
        This makes it simpler to reference things like signer_cn without full path.
        """
        # Flatten signature data
        sig_data = context.shared_state.get("digital_signatures", {})
        if isinstance(sig_data, dict):
            sigs = sig_data.get("signatures", [])
            if sigs and len(sigs) > 0:
                # Get first valid signature's info
                valid_sig = None
                for sig in sigs:
                    if sig.get("integrity", False):
                        valid_sig = sig
                        break
                # If no valid signature, use first one
                if not valid_sig and len(sigs) > 0:
                    valid_sig = sigs[0]

                if valid_sig:
                    context.shared_state["signer_cn"] = valid_sig.get("signer_cn", "")
                    context.shared_state["signature_valid"] = valid_sig.get("integrity", False)
                    context.shared_state["signature_expired"] = valid_sig.get("expired", False)

        # Flatten revision data
        rev_data = context.shared_state.get("pdf_revisions", {})
        if isinstance(rev_data, dict):
            context.shared_state["is_tampered"] = rev_data.get("is_tampered_after_sign", False)
            context.shared_state["revision_count"] = rev_data.get("revision_count", 1)
        # Register available operators
        self._available_operators: Dict[str, BaseOperator] = {
            "PDFInfoExtractor": PDFInfoOperator(),
            "QRScanner": QRScannerOperator(),
            "SignatureVerifier": SignatureOperator(),
            "TextLLM": TextLLMOperator(),
            "VisionLLM": VisionLLMOperator(),
            "InstitutionSniffer": InstitutionSnifferOperator(),
            "RevisionCheck": RevisionCheckOperator(),
            "URLFetchOperator": URLFetchOperator(),
            "StampDetection": StampDetectionOperator(),
            "DocumentDiff": DocumentDiffOperator(),
            "TableVerification": TableVerificationOperator(),
        }

    def _determine_required_operators(self, rules: List[VerificationRule], rule_to_modules: Dict[str, List[VerificationModule]] = None) -> List[BaseOperator]:
        """
        Analyze the AST/rule dependencies to figure out which operators must run.
        """
        required_names = set(["PDFInfoExtractor", "InstitutionSniffer", "RevisionCheck"])
        
        # Collect modules to see if their operators are needed
        if rule_to_modules:
            for rid, mods in rule_to_modules.items():
                # Only check mods if the rule itself is in the active list
                for mod in mods:
                    op = self._get_operator_for_module_type(mod.module_type)
                    if op:
                        required_names.add(op.name)

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

            # Auto-resolve from nodes in logic graph
            nodes = logic.get("nodes", [])
            for node in nodes:
                node_type = node.get("type")
                # Fallback to data.nodeType if top-level type is generic/default
                if not node_type or node_type in ["default", "input", "output"]:
                    node_type = node.get("data", {}).get("nodeType")
                
                if not node_type:
                    continue

                if node_type in ["digital_signature", "signature"]:
                    required_names.add("SignatureVerifier")
                elif node_type in ["qr_scanner", "qr-code"]:
                    required_names.add("QRScanner")
                elif node_type in ["pdf_metadata", "pdf-info"]:
                    required_names.add("PDFInfoExtractor")
                elif node_type in ["institution_sniffer", "institution-sniffer"]:
                    required_names.add("InstitutionSniffer")
                elif node_type in ["revision_check", "revision-check"]:
                    required_names.add("RevisionCheck")
                elif node_type in ["text_llm", "text-llm"]:
                    required_names.add("TextLLM")
                elif node_type in ["vision_llm", "vision-llm"]:
                    required_names.add("VisionLLM")
                elif node_type in ["http_call", "http-call"]:
                    required_names.add("URLFetchOperator")
                elif node_type in ["stamp_detection"]:
                    required_names.add("StampDetection")
                elif node_type in ["document_diff", "document-diff"]:
                    required_names.add("DocumentDiff")
                elif node_type in ["table_verification"]:
                    required_names.add("TableVerification")

        # Build list
        ops_to_run = []
        for name in required_names:
            if name in self._available_operators:
                ops_to_run.append(self._available_operators[name])
            else:
                logger.warning(f"Engine requested unknown operator: {name}")

        return ops_to_run

    def _get_operator_for_module_type(self, module_type: ModuleType) -> Optional[BaseOperator]:
        """
        Map module type to the corresponding operator instance.
        """
        module_to_operator = {
            ModuleType.qr_scanner: "QRScanner",
            ModuleType.signature_verifier: "SignatureVerifier",
            ModuleType.pdf_info: "PDFInfoExtractor",
            ModuleType.institution_sniffer: "InstitutionSniffer",
            ModuleType.revision_check: "RevisionCheck",
            ModuleType.text_llm: "TextLLM",
            ModuleType.vision_llm: "VisionLLM",
            ModuleType.url_fetch: "URLFetchOperator",
            ModuleType.stamp_detection: "StampDetection",
            ModuleType.document_diff: "DocumentDiff",
            ModuleType.table_verification: "TableVerification",
        }
        operator_name = module_to_operator.get(module_type)
        if operator_name:
            return self._available_operators.get(operator_name)
        return None

    async def _execute_verification_module(
        self,
        module: VerificationModule,
        context: DocumentContext,
        emit_log=None
    ) -> Dict[str, any]:
        """
        Execute a single verification module and return its result.
        """
        if emit_log:
            await emit_log(f"[模块] 开始执行校验模块: {module.name}")

        operator = self._get_operator_for_module_type(module.module_type)
        if not operator:
            result = {
                "name": module.name,
                "status": "fail",
                "passed": False,
                "message": f"未找到对应的算子: {module.module_type}",
                "severity": module.severity.value,
                "module_id": module.id
            }
            if emit_log:
                await emit_log(f"[模块] {result['message']}")
            return result

        try:
            # Execute the operator with module config
            op_result: OperatorResult = await operator.execute(context, **module.config)

            # Map pass_status to passed
            passed = op_result.pass_status if hasattr(op_result, 'pass_status') else op_result.passed

            # Determine status based on module severity and result
            if module.severity == ModuleSeverity.info:
                status = "info"
            elif module.severity == ModuleSeverity.warning:
                status = "warning" if not passed else "pass"
            else:  # critical
                status = "fail" if not passed else "pass"

            result = {
                "name": module.name,
                "status": status,
                "passed": passed,
                "message": op_result.message if hasattr(op_result, 'message') else "执行完成",
                "severity": module.severity.value,
                "module_id": module.id,
                "extracted_data": op_result.extracted_data if hasattr(op_result, 'extracted_data') else {},
                "confidence": op_result.confidence if hasattr(op_result, 'confidence') else 1.0
            }

            if emit_log:
                await emit_log(f"[模块] {module.name} 执行完成: {status} - {result['message']}")

            return result

        except Exception as e:
            logger.error(f"[Engine] Module {module.name} execution failed: {e}")
            result = {
                "name": module.name,
                "status": "fail" if module.severity == ModuleSeverity.critical else "warning",
                "passed": False,
                "message": f"执行异常: {str(e)}",
                "severity": module.severity.value,
                "module_id": module.id,
                "error": str(e)
            }
            if emit_log:
                await emit_log(f"[模块] {module.name} 执行异常: {str(e)}")
            return result

    async def _execute_verification_modules(
        self,
        modules: List[VerificationModule],
        context: DocumentContext,
        emit_log=None
    ) -> List[Dict[str, any]]:
        """
        Execute multiple verification modules and return their results.
        Modules are executed in sort_order.
        """
        if not modules:
            return []

        # Sort modules by sort_order
        sorted_modules = sorted(modules, key=lambda m: m.sort_order)

        if emit_log:
            await emit_log(f"[模块] 开始执行 {len(sorted_modules)} 个校验模块")

        results = []
        for module in sorted_modules:
            if not module.is_active:
                continue
            result = await self._execute_verification_module(module, context, emit_log)
            results.append(result)

        return results

    async def run(
        self, 
        context: DocumentContext, 
        rules: List[VerificationRule], 
        progress_callback=None, 
        categories=None, 
        verification_modules: List[VerificationModule] = None,
        rule_to_modules: Dict[str, List[VerificationModule]] = None
    ) -> Dict[str, any]:
        """
        Execute the dynamic pipeline with a two-stage architecture.
        Stage 1: Pre-classification (PDF Info & Institution Sniffer)
        Stage 1.5: Category keyword matching to route rules
        Stage 2: Execute heavy operators only for rules that match the category/institution.
        """
        logger.info(f"[Engine] Starting dynamic verification for {context.file_path}")
        
        async def emit_log(msg: str):
            if progress_callback:
                await progress_callback(msg)

        # ---------------------------------------------------------
        # STAGE 1: Pre-classification Operators
        # ---------------------------------------------------------
        await emit_log("引擎调度：启动基础信息解析与分类嗅探阶段")
        pre_op_names = ["PDFInfoExtractor", "InstitutionSniffer"]
        operator_results = {}

        for name in pre_op_names:
            if name in self._available_operators:
                op = self._available_operators[name]
                await emit_log(f"正在执行算子 [{name}]...")
                try:
                    res = await op.execute(context)
                    operator_results[op.name] = res.dict()
                    await emit_log(f"算子 [{name}] 执行完毕")
                except Exception as e:
                    logger.error(f"[Engine] Operator {op.name} crashed: {e}")
                    operator_results[op.name] = {"pass_status": False, "message": str(e)}
                    await emit_log(f"算子 [{name}] 执行异常: {e}")

        # Flatten commonly used nested values for easier access
        self._flatten_shared_state(context)

        # ---------------------------------------------------------
        # STAGE 1.5: Category Keyword Matching & Rule Routing
        # ---------------------------------------------------------
        sniffed_inst = context.shared_state.get("institution", "UNKNOWN")
        full_text = context.shared_state.get("full_text", "")
        file_path = context.file_path or ""
        matched_category_id = None
        matched_category_name = None

        if categories:
            await emit_log(f"分类嗅探结果: {sniffed_inst}。正在通过关键字匹配文档分类...")
            for cat in categories:
                cat_keywords = cat.keywords if hasattr(cat, 'keywords') else (cat.get('keywords', []) if isinstance(cat, dict) else [])
                cat_id = cat.id if hasattr(cat, 'id') else (cat.get('id') if isinstance(cat, dict) else None)
                cat_name = cat.name if hasattr(cat, 'name') else (cat.get('name', '') if isinstance(cat, dict) else '')
                cat_active = cat.is_active if hasattr(cat, 'is_active') else (cat.get('is_active', True) if isinstance(cat, dict) else True)
                if not cat_active or not cat_keywords:
                    continue
                for kw in cat_keywords:
                    if kw and (kw.lower() in full_text.lower() or kw.lower() in file_path.lower()):
                        matched_category_id = str(cat_id) if cat_id else None
                        matched_category_name = cat_name
                        break
                if matched_category_id:
                    break

        # Determine which rules to apply based on category matching
        if matched_category_id:
            # Check if the matched category has dedicated rules
            category_rules = [r for r in rules if r.category_id and str(r.category_id) == matched_category_id]
            if category_rules:
                await emit_log(f"文档匹配分类 [{matched_category_name}]，找到 {len(category_rules)} 条专属规则，将跳过全局默认规则")
                rules = category_rules
            else:
                await emit_log(f"文档匹配分类 [{matched_category_name}]，但该分类暂无专属规则，降级使用全局默认规则")
        else:
            if categories:
                await emit_log(f"分类嗅探结果: {sniffed_inst}。文档未匹配到任何分类关键字，使用全局默认规则")
            else:
                await emit_log(f"分类嗅探结果: {sniffed_inst}。无可用分类定义，使用全局默认规则")

        # ---------------------------------------------------------
        # FILTER RULES (Based on Institution conditions)
        # ---------------------------------------------------------
        applicable_rules = []
        for rule in rules:
            logic = rule.logic_config or {}
            conditions = logic.get("conditions", {})
            required_inst = conditions.get("institution")
            
            # If the rule has an explicit institution condition, check it.
            if required_inst:
                required_norm = normalize_institution_name(required_inst)
                sniffed_norm = normalize_institution_name(sniffed_inst)
                if required_norm != sniffed_norm:
                    logger.info(f"[Engine] Skipping rule {rule.rule_name} (requires {required_inst} [norm: {required_norm}], but sniffed {sniffed_inst} [norm: {sniffed_norm}])")
                    continue
            applicable_rules.append(rule)

        await emit_log(f"匹配到 {len(applicable_rules)} 条适用规则，开始阶段二深度分析")

        # ---------------------------------------------------------
        # STAGE 2: Heavy Operators for Applicable Rules
        # ---------------------------------------------------------
        heavy_operators = self._determine_required_operators(applicable_rules, rule_to_modules)
        # Filter out ones already run
        heavy_operators = [op for op in heavy_operators if op.name not in pre_op_names]

        if heavy_operators:
            await emit_log(f"解析到 {len(heavy_operators)} 个深度分析算子待执行...")

        for op in heavy_operators:
            logger.info(f"[Engine] Executing heavy operator: {op.name}")
            await emit_log(f"正在执行高能耗算子 [{op.name}]...")
            try:
                res = await op.execute(context)
                operator_results[op.name] = res.dict()
                await emit_log(f"算子 [{op.name}] 执行完毕")
            except Exception as e:
                logger.error(f"[Engine] Operator {op.name} crashed: {e}")
                operator_results[op.name] = {"pass_status": False, "message": str(e)}
                await emit_log(f"算子 [{op.name}] 执行异常: {e}")

        # Flatten any newly added shared_state values
        self._flatten_shared_state(context)

        # ---------------------------------------------------------
        # STAGE 3: Execute Verification Modules (legacy global modules input)
        # ---------------------------------------------------------
        global_module_results = []
        if verification_modules:
            global_module_results = await self._execute_verification_modules(
                verification_modules, context, emit_log
            )

        # Phase 2: Evaluate Rules
        rule_evaluations = []
        pass_count = warning_count = fail_count = reference_count = 0
        needs_review = False

        for rule in applicable_rules:
            await emit_log(f"-> 开始执行验证规则：[{rule.rule_name}]")
            
            # Check if this rule has linked modules
            linked_modules = rule_to_modules.get(rule.id, []) if rule_to_modules else []
            
            if linked_modules:
                # Execute linked modules for this specific rule
                await emit_log(f"规则 [{rule.rule_name}] 关联了 {len(linked_modules)} 个校验模块，开始执行并评分...")
                module_res_list = await self._execute_verification_modules(linked_modules, context, emit_log)
                
                # A rule's final status is calculated based on its modules' statuses
                rule_pass = True
                rule_msgs = []
                worst_severity = Severity.warning if rule.severity == Severity.warning else Severity.fail
                rule_severity = rule.severity.value if hasattr(rule.severity, 'value') else rule.severity
                
                for mr in module_res_list:
                    mr_pass = mr.get("passed", False)
                    mr_sev = mr.get("severity", "warning")
                    mr_msg = mr.get("message", "")
                    mr_name = mr.get("name", "未命名模块")
                    
                    rule_msgs.append(f"[{mr_name}] {'通过' if mr_pass else '失败'}({mr_msg})")
                    
                    if not mr_pass:
                        # If any critical module fails, the rule is not passed
                        if mr_sev == "critical":
                            rule_pass = False
                            worst_severity = Severity.fail
                        elif mr_sev == "warning":
                            # warning module failures make the rule fail, but severity is warning
                            if worst_severity != Severity.fail:
                                worst_severity = Severity.warning
                            # Even if warning, a failing module means the rule doesn't fully pass
                            rule_pass = False

                rule_msg = "；".join(rule_msgs) if rule_msgs else "没有关联的模块被执行"
                
                # Tally stats directly from individual linked modules
                for mr in module_res_list:
                    mr_sev = mr.get("severity", "warning")
                    mr_pass = mr.get("passed", False)
                    
                    if mr_sev == "info":
                        reference_count += 1
                        mr_status = "info"
                    elif mr_pass:
                        pass_count += 1
                        mr_status = "pass"
                    elif mr_sev == "warning":
                        warning_count += 1
                        mr_status = "warning"
                    else:
                        fail_count += 1
                        mr_status = "fail"

                    # Put module run detail directly as a check item, bound to the parent rule
                    rule_evaluations.append({
                        "name": f"{rule.rule_name} > {mr.get('name')}",
                        "status": mr_status,
                        "rule_name": rule.rule_name,
                        "rule_type": "module",
                        "passed": mr_pass,
                        "message": mr.get("message", ""),
                        "severity": mr_sev,
                        "confidence": mr.get("confidence", 1.0)
                    })
                
                continue
            
            # Check conditions (skip if mismatch)
            logic = rule.logic_config or {}
            conditions = logic.get("conditions", {})
            if conditions:
                sniffed_inst = context.shared_state.get("institution", "UNKNOWN")
                required_inst = conditions.get("institution")
                if required_inst:
                    required_norm = normalize_institution_name(required_inst)
                    sniffed_norm = normalize_institution_name(sniffed_inst)
                    if required_norm != sniffed_norm:
                        logger.info(f"[Engine] Skipping rule {rule.rule_name} (requires {required_inst} [norm: {required_norm}], but sniffed {sniffed_inst} [norm: {sniffed_norm}])")
                        await emit_log(f"规则 [{rule.rule_name}] 已跳过（适用机构不匹配）")
                        continue

            rule_pass = False
            rule_msg = "未执行"
            confidence = 1.0

            if rule.rule_type == RuleType.plugin:
                if rule.rule_content == "REQUIRE_QR_CODE":
                    qr_data = context.shared_state.get("qr_codes", [])
                    if len(qr_data) > 0:
                        rule_pass = True
                        qr_texts = [qr.get("data", "未知") for qr in qr_data if isinstance(qr, dict)]
                        rule_msg = f"通过：检测到 {len(qr_data)} 个二维码。内容：{', '.join(qr_texts)}"
                    else:
                        rule_msg = "未通过：未在页面上发现追溯二维码"

                elif rule.rule_content == "REQUIRE_SIGNATURE":
                    sig_data = context.shared_state.get("digital_signatures", {})
                    sigs = sig_data.get("signatures", [])
                    valid_sigs = [s for s in sigs if s.get("integrity", False)]
                    
                    if valid_sigs:
                        rule_pass = True
                        signers_info = []
                        for s in valid_sigs:
                            cn = s.get("signer_cn", "未知签署人")
                            if s.get("expired", False):
                                signers_info.append(f"{cn} (证书已过期)")
                            else:
                                signers_info.append(f"{cn} (证书有效)")
                        rule_msg = f"检测到 {len(valid_sigs)} 个有效数字签名。签署人详情：{', '.join(signers_info)}"
                    elif len(sigs) > 0:
                        rule_pass = False
                        rule_msg = f"未通过：检测到 {len(sigs)} 个数字签名，但均已损坏、被篡改或验证失败。"
                    else:
                        rule_pass = False
                        rule_msg = "未通过：该文档缺失强制要求的有效电子数字签名。"
                
                elif rule.rule_content == "REQUIRE_REVISION_CHECK":
                    rev_data = context.shared_state.get("pdf_revisions", {})
                    is_tampered = rev_data.get("is_tampered_after_sign", False)
                    rule_pass = not is_tampered
                    rule_msg = rev_data.get("tamper_message", "未执行修订版本分析。")
                    
                await emit_log(f"规则 [{rule.rule_name}] 结果: {'通过' if rule_pass else '不通过'} - {rule_msg}")
                
            elif rule.rule_type == RuleType.llm_prompt:
                model_type = logic.get("llm_model_type", "text")
                operation_mode = logic.get("llm_operation_mode", "verification")

                if model_type == "vision":
                    if operation_mode == "extraction":
                        await emit_log(f"大模型算子开始执行数据提取 (Vision LLM Extraction)...")
                    else:
                        await emit_log(f"大模型算子开始理解规则语义并执行视觉分析 (Vision LLM)...")
                    from app.engine.operators.vision_llm_operator import VisionLLMOperator
                    op = VisionLLMOperator()
                else:
                    if operation_mode == "extraction":
                        await emit_log(f"大模型算子开始执行数据提取 (Text LLM Extraction)...")
                    else:
                        await emit_log(f"大模型算子开始理解规则语义并执行文本匹配 (Text LLM)...")
                    from app.engine.operators.text_llm_operator import TextLLMOperator
                    op = TextLLMOperator()

                try:
                    res = await op.execute(context, prompt=rule.rule_content, operation_mode=operation_mode)
                    if res.pass_status:
                        llm_data = res.extracted_data

                        # Extraction mode: always pass, display extracted keys
                        if operation_mode == "extraction":
                            rule_pass = True
                            if isinstance(llm_data, dict):
                                extracted_keys = list(llm_data.keys())
                                # Store extracted data in shared state for other rules to use
                                for key, value in llm_data.items():
                                    context.shared_state[f"extracted_{key}"] = value
                                rule_msg = f"数据提取成功: {', '.join(extracted_keys)}"
                            else:
                                rule_msg = f"数据提取成功"
                        else:
                            # Verification mode: check passed status
                            rule_pass = llm_data.get("passed", False)
                            rule_msg = llm_data.get("reason", "大模型分析未返回原因。")
                            confidence = llm_data.get("confidence", 1.0)
                    else:
                        rule_pass = False
                        rule_msg = f"未通过：大模型调用失败 ({res.message})"
                except Exception as e:
                    rule_pass = False
                    rule_msg = f"未通过：大模型调用异常 ({e})"
                await emit_log(f"规则 [{rule.rule_name}] 结果: {'通过' if rule_pass else '不通过'} - {rule_msg}")
                
            elif rule.rule_type == RuleType.regex:
                import re
                full_text = context.shared_state.get("full_text", "")
                try:
                    match = re.search(rule.rule_content, full_text)
                    if match:
                        rule_pass = True
                        rule_msg = f"通过：检测到正则匹配项 '{match.group(0)}'"
                    else:
                        rule_pass = False
                        rule_msg = "未通过：未检测到匹配正则表达式的内容"
                except Exception as e:
                    rule_pass = False
                    rule_msg = f"未通过：正则表达式错误 ({e})"
                await emit_log(f"规则 [{rule.rule_name}] 结果: {'通过' if rule_pass else '不通过'} - {rule_msg}")
                
            elif rule.rule_type == RuleType.keyword:
                full_text = context.shared_state.get("full_text", "")
                if rule.rule_content and rule.rule_content in full_text:
                    rule_pass = True
                    rule_msg = f"通过：文档中包含关键字 '{rule.rule_content}'"
                else:
                    rule_pass = False
                    rule_msg = f"未通过：文档中不包含关键字 '{rule.rule_content}'"
                await emit_log(f"规则 [{rule.rule_name}] 结果: {'通过' if rule_pass else '不通过'} - {rule_msg}")

            elif rule.rule_type == RuleType.logic_graph:
                # Helper function to query nested paths (like response_json.data.status)
                def get_nested_val(d: dict, path: str):
                    parts = path.split('.')
                    curr = d
                    for p in parts:
                        if isinstance(curr, dict):
                            curr = curr.get(p)
                        else:
                            return ""
                    return curr if curr is not None else ""

                # Dynamic Variable Interpolation helper supporting {{#node_id.key#}} and {{key}}
                def interpolate_vars(val: any, state: dict, node_outputs: dict = None) -> any:
                    if isinstance(val, str):
                        import re
                        # 1. Resolve Dify-style variable mappings: {{#node_id.key#}}
                        dify_matches = re.findall(r'\{\{#([^}]+)#\}\}', val)
                        for match in dify_matches:
                            parts = match.split('.', 1)
                            if len(parts) == 2 and node_outputs:
                                target_node_id, path_key = parts[0].strip(), parts[1].strip()
                                node_data_dict = node_outputs.get(target_node_id, {})
                                replacement = get_nested_val(node_data_dict, path_key)
                                val = val.replace(f"{{{{#{match}#}}}}", str(replacement))
                            else:
                                val = val.replace(f"{{{{#{match}#}}}}", "")

                        # 2. Resolve standard flat variables: {{variable}} for backward compatibility
                        matches = re.findall(r'\{\{([^}]+)\}\}', val)
                        for match in matches:
                            if match.startswith('#'):
                                continue
                            key = match.strip()
                            replacement = state.get(key, "")
                            val = val.replace(f"{{{{{match}}}}}", str(replacement))
                        return val
                    elif isinstance(val, dict):
                        return {k: interpolate_vars(v, state, node_outputs) for k, v in val.items()}
                    elif isinstance(val, list):
                        return [interpolate_vars(v, state, node_outputs) for v in val]
                    return val

                nodes = logic.get("nodes", [])
                edges = logic.get("edges", [])
                
                nodes_by_id = {node.get("id"): node for node in nodes}
                
                # Identify entries (nodes without incoming edges)
                incoming_targets = {edge.get("target") for edge in edges if edge.get("target")}
                entry_nodes = [node for node in nodes if node.get("id") not in incoming_targets]
                
                if not entry_nodes:
                    entry_nodes = nodes
                    
                # Group outgoing edges by source node ID
                outgoing_edges = {}
                for edge in edges:
                    src = edge.get("source")
                    if src:
                        if src not in outgoing_edges:
                            outgoing_edges[src] = []
                        outgoing_edges[src].append(edge)
                        
                # DAG Edge-routing execution loop
                queue = [n.get("id") for n in entry_nodes if n.get("id")]
                visited = set()
                
                active_checks = []
                failed_checks = []
                executed_modules = []  # Track per-node verification module results
                
                # Initialize node_outputs in context
                if not hasattr(context, "node_outputs"):
                    context.node_outputs = {}
                
                while queue:
                    node_id = queue.pop(0)
                    if node_id in visited:
                        continue
                    visited.add(node_id)
                    
                    node = nodes_by_id.get(node_id)
                    if not node:
                        continue
                        
                    node_type = node.get("type")
                    if not node_type or node_type in ["default", "input", "output"]:
                        node_type = node.get("data", {}).get("nodeType")

                    # Interpolate parameters dynamically from shared context and upstream node outputs
                    node_data = interpolate_vars(node.get("data", {}), context.shared_state, context.node_outputs)
                    
                    node_passed = True
                    node_msg = ""
                    
                    # Capture intermediate results for output schema
                    node_extracted_groups = {}
                    node_llm_data = {}
                    node_http_response = {}
                    node_diff_similarity = None
                    
                    if node_type in ["digital_signature", "signature"]:
                        sig_data = context.shared_state.get("digital_signatures", {})
                        sigs = sig_data.get("signatures", [])
                        valid_sigs = [s for s in sigs if s.get("integrity", False)]

                        expected_issuer = node_data.get("expectedIssuer", "")
                        if valid_sigs:
                            signers_info = []
                            for s in valid_sigs:
                                cn = s.get("signer_cn", "未知签署人")
                                if s.get("expired", False):
                                    signers_info.append(f"{cn} (证书已过期)")
                                else:
                                    signers_info.append(f"{cn} (证书有效)")
                            signers_str = ", ".join(signers_info)

                            if expected_issuer:
                                matched = any(expected_issuer.lower() in s.get("signer_cn", "").lower() for s in valid_sigs)
                                if matched:
                                    node_passed = True
                                    node_msg = f"检测到 {len(valid_sigs)} 个有效数字签名，签发者匹配 [{expected_issuer}]。详情：{signers_str}"
                                else:
                                    node_passed = False
                                    node_msg = f"检测到 {len(valid_sigs)} 个有效数字签名，但均未匹配预期签发者 [{expected_issuer}]。详情：{signers_str}"
                            else:
                                node_passed = True
                                node_msg = f"检测到 {len(valid_sigs)} 个有效数字签名。签署人详情：{signers_str}"
                        elif len(sigs) > 0:
                            node_passed = False
                            node_msg = f"检测到 {len(sigs)} 个数字签名，但均已损坏、被篡改或验证失败。"
                        else:
                            node_passed = False
                            node_msg = "该文档缺失强制要求的有效电子数字签名。"

                        # Flatten signature data for variable access
                        self._flatten_shared_state(context)
                            
                    elif node_type in ["qr_scanner", "qr-code"]:
                        qr_data = context.shared_state.get("qr_codes", [])
                        if len(qr_data) > 0:
                            node_passed = True
                            qr_texts = [qr.get("data", "未知") for qr in qr_data if isinstance(qr, dict)]
                            node_msg = f"检测到 {len(qr_data)} 个二维码。内容：{', '.join(qr_texts)}"
                            # Store first QR content for easy reference
                            if qr_data and len(qr_data) > 0:
                                context.shared_state["qr_content"] = qr_data[0].get("data", "")
                        else:
                            node_passed = False
                            node_msg = "未检测到任何二维码"
                            
                    elif node_type in ["pdf_metadata", "pdf-info"]:
                        pdf_info = context.shared_state.get("pdf_info", {})
                        if pdf_info:
                            node_passed = True
                            node_msg = f"PDF元数据校验通过 (页数: {pdf_info.get('page_count', 0)})"
                        else:
                            node_passed = True
                            node_msg = "PDF元数据读取通过"
                            
                    elif node_type in ["regex_match", "regex"]:
                        pattern = node_data.get("pattern", "")
                        full_text = context.shared_state.get("full_text", "")
                        if pattern:
                            import re
                            try:
                                if re.search(pattern, full_text):
                                    node_passed = True
                                    node_msg = f"正则匹配成功: [{pattern}]"
                                else:
                                    node_passed = False
                                    node_msg = f"正则未匹配: [{pattern}]"
                            except Exception as e:
                                node_passed = False
                                node_msg = f"正则表达式语法错误: {e}"
                        else:
                            node_passed = True
                            node_msg = "未配置正则表达式，跳过"
                            
                    elif node_type in ["comparison", "data-compare"]:
                        field_a = node_data.get("fieldA", "") or node_data.get("source_a", "")
                        field_b = node_data.get("fieldB", "") or node_data.get("source_b", "")
                        val_a = context.shared_state.get(field_a) or context.shared_state.get("institution")
                        val_b = context.shared_state.get(field_b) or node_data.get("fieldBValue")
                        if val_a and val_b and str(val_a).lower() == str(val_b).lower():
                            node_passed = True
                            node_msg = f"字段一致校验通过: {field_a} == {field_b}"
                        else:
                            node_passed = False
                            node_msg = f"字段一致校验失败: {field_a} != {field_b}"
                            
                    elif node_type in ["text_llm", "text-llm", "vision_llm", "vision-llm"]:
                        # Get node configuration
                        node_prompt = node_data.get("prompt", "")
                        operation_mode = node_data.get("operation_mode", "verification")

                        # Execute LLM operator dynamically
                        try:
                            if node_type in ["vision_llm", "vision-llm"]:
                                from app.engine.operators.vision_llm_operator import VisionLLMOperator
                                op = VisionLLMOperator()
                            else:
                                from app.engine.operators.text_llm_operator import TextLLMOperator
                                op = TextLLMOperator()

                            res = await op.execute(context, prompt=node_prompt, operation_mode=operation_mode)

                            if res.pass_status:
                                llm_data = res.extracted_data if res.extracted_data else {}
                                node_llm_data = llm_data

                                if operation_mode == "extraction":
                                    # Extraction mode: always pass
                                    node_passed = True
                                    if isinstance(llm_data, dict):
                                        # Store extracted data in shared state
                                        for key, value in llm_data.items():
                                            context.shared_state[f"extracted_{key}"] = value
                                        extracted_keys = list(llm_data.keys())
                                        node_msg = f"数据提取成功: {', '.join(extracted_keys)}"
                                    else:
                                        node_msg = f"数据提取成功"
                                else:
                                    # Verification mode
                                    node_passed = llm_data.get("passed", True)
                                    node_msg = llm_data.get("reason", "大模型审核通过")
                            else:
                                node_passed = False
                                node_msg = f"大模型执行失败: {res.message}"
                        except Exception as e:
                            logger.error(f"[Engine] LLM node {node_type} failed: {e}")
                            node_passed = False
                            node_msg = f"大模型节点异常: {str(e)}"
                            
                    elif node_type in ["institution_sniffer", "institution-sniffer"]:
                        sniffed_inst = context.shared_state.get("institution", "UNKNOWN")
                        node_passed = sniffed_inst != "UNKNOWN"
                        node_msg = f"发证机构嗅探完成: {sniffed_inst}"

                    elif node_type in ["revision_check", "revision-check"]:
                        rev_data = context.shared_state.get("pdf_revisions", {})
                        is_tampered = rev_data.get("is_tampered_after_sign", False)
                        rev_count = rev_data.get("revision_count", 1)

                        expected_max = node_data.get("maxRevisions", 0)
                        if expected_max > 0 and rev_count > expected_max:
                            node_passed = False
                            node_msg = f"修订版本数 {rev_count} 超过允许上限 {expected_max}"
                        elif is_tampered:
                            node_passed = False
                            node_msg = f"文档已签名但存在 {rev_count} 次修订 (签名后 {rev_count - 1} 次增量更新)，存在篡改风险"
                        elif rev_count > 1:
                            node_passed = node_data.get("allowIncrementalUpdates", True)
                            node_msg = f"文档包含 {rev_count} 个修订版本 (增量更新)"
                        else:
                            node_passed = True
                            node_msg = f"文档共 {rev_count} 个版本，版本结构完整未修改"

                        # Flatten revision data for variable access
                        self._flatten_shared_state(context)

                    elif node_type == "http_call" or node_type == "http-call":
                        # HTTP External Verification Node
                        try:
                            import httpx

                            # Get configuration
                            url_template = node_data.get("url_template", "")
                            http_method = node_data.get("http_method", "GET")
                            headers_list = node_data.get("headers", [])
                            body_template = node_data.get("body_template", "")
                            timeout = node_data.get("timeout", 30)
                            success_type = node_data.get("success_type", "status_2xx")
                            json_path = node_data.get("json_path", "")
                            json_expected = node_data.get("json_expected", "true")
                            text_contains = node_data.get("text_contains", "")

                            # Interpolate variables in URL using outer interpolate_vars
                            url = interpolate_vars(url_template, context.shared_state, context.node_outputs)

                            if not url:
                                node_passed = False
                                node_msg = "HTTP 验证失败: URL 模板为空"
                            else:
                                # Build headers
                                headers = {}
                                for header in headers_list:
                                    # Skip internal fields like _id
                                    key = interpolate_vars(header.get("key", ""), context.shared_state, context.node_outputs)
                                    value = interpolate_vars(header.get("value", ""), context.shared_state, context.node_outputs)
                                    if key:
                                        headers[key] = value

                                # Build body for POST/PUT
                                body = None
                                if http_method in ["POST", "PUT"] and body_template:
                                    body = interpolate_vars(body_template, context.shared_state, context.node_outputs)

                                # Make HTTP request
                                async with httpx.AsyncClient(timeout=timeout) as client:
                                    if http_method == "GET":
                                        response = await client.get(url, headers=headers)
                                    elif http_method == "POST":
                                        response = await client.post(url, headers=headers, content=body)
                                    elif http_method == "PUT":
                                        response = await client.put(url, headers=headers, content=body)
                                    else:
                                        response = await client.get(url, headers=headers)

                                # Check success criteria
                                status_code = response.status_code

                                # Capture HTTP response for outputs schema
                                resp_json = None
                                try:
                                    resp_json = response.json()
                                except Exception:
                                    pass
                                node_http_response = {
                                    "status_code": status_code,
                                    "response_text": response.text,
                                    "response_json": resp_json
                                }

                                if success_type == "status_code":
                                    node_passed = status_code == 200
                                    node_msg = f"HTTP 验证完成: 状态码 {status_code}"
                                elif success_type == "status_2xx":
                                    node_passed = 200 <= status_code < 300
                                    node_msg = f"HTTP 验证完成: 状态码 {status_code}"
                                elif success_type == "json_path":
                                    try:
                                        response_json = response.json()
                                        # Simple JSON path evaluation (supports $.field or $.field.nested)
                                        path_parts = json_path.replace("$.", "").split(".")
                                        value = response_json
                                        for part in path_parts:
                                            if isinstance(value, dict):
                                                value = value.get(part)
                                            else:
                                                value = None
                                                break

                                        # Compare with expected value
                                        if json_expected.lower() == "true":
                                            node_passed = bool(value)
                                        elif json_expected.lower() == "false":
                                            node_passed = not bool(value)
                                        else:
                                            node_passed = str(value) == json_expected

                                        node_msg = f"HTTP 验证完成: JSON Path {json_path} = {value}"
                                    except Exception as e:
                                        node_passed = False
                                        node_msg = f"HTTP 验证失败: JSON 解析错误 - {str(e)}"
                                elif success_type == "text_contains":
                                    response_text = response.text
                                    node_passed = text_contains in response_text
                                    node_msg = f"HTTP 验证完成: 响应{'包含' if node_passed else '不包含'} '{text_contains}'"
                                else:
                                    node_passed = 200 <= status_code < 300
                                    node_msg = f"HTTP 验证完成: 状态码 {status_code}"

                        except httpx.TimeoutException:
                            node_passed = False
                            node_msg = f"HTTP 验证失败: 请求超时 (>{timeout}s)"
                        except httpx.HTTPError as e:
                            node_passed = False
                            node_msg = f"HTTP 验证失败: {str(e)}"
                        except Exception as e:
                            logger.error(f"[Engine] HTTP call node failed: {e}")
                            node_passed = False
                            node_msg = f"HTTP 验证异常: {str(e)}"

                    elif node_type in ["variable_extractor", "variable-extractor"]:
                        source_field = node_data.get("source_field", "qr_content")
                        pattern = node_data.get("pattern", "")
                        
                        source_text = context.shared_state.get(source_field, "")
                        if not source_text and source_field == "qr_content":
                            qr_codes = context.shared_state.get("qr_codes", [])
                            if qr_codes and isinstance(qr_codes, list) and len(qr_codes) > 0:
                                source_text = qr_codes[0].get("data", "")
                        
                        if pattern and source_text:
                            import re
                            try:
                                match = re.search(pattern, source_text)
                                if match:
                                    node_passed = True
                                    extracted = match.groupdict()
                                    if extracted:
                                        for k, v in extracted.items():
                                            context.shared_state[k] = v
                                        node_msg = f"变量提取成功: {', '.join([f'{k}={v}' for k, v in extracted.items()])}"
                                        node_extracted_groups = extracted
                                    else:
                                        context.shared_state["extracted_value"] = match.group(0)
                                        node_msg = f"变量提取成功: extracted_value={match.group(0)}"
                                else:
                                    node_passed = False
                                    node_msg = f"变量提取失败：未匹配到模式 [{pattern}]"
                            except Exception as e:
                                node_passed = False
                                node_msg = f"变量提取语法错误: {e}"
                        else:
                            node_passed = False
                            node_msg = "变量提取跳过：数据源为空或未配置模式"

                    elif node_type in ["document_diff", "document-diff"]:
                        base_document_url = node_data.get("base_document_url", "")
                        similarity_threshold = node_data.get("similarity_threshold", 100.0)
                        
                        if not base_document_url:
                            node_passed = False
                            node_msg = "原件比对失败：未配置基准文档 URL"
                        else:
                            try:
                                op = self._available_operators.get("DocumentDiff")
                                if not op:
                                    from app.engine.operators.diff_operator import DocumentDiffOperator
                                    op = DocumentDiffOperator()
                                
                                res = await op.execute(
                                    context, 
                                    base_document_url=base_document_url, 
                                    similarity_threshold=similarity_threshold
                                )
                                
                                node_passed = res.pass_status
                                node_msg = res.message
                                node_diff_similarity = res.extracted_data.get("similarity")
                                
                                # Store the result in operator_results for frontend FileDetailPage.vue to display diff changes
                                operator_results["DocumentDiff"] = res.dict()
                                operator_results["DocumentDiffOperator"] = res.dict()
                                
                            except Exception as e:
                                logger.error(f"[Engine] Document diff node failed: {e}")
                                node_passed = False
                                node_msg = f"原件比对异常: {e}"

                    else:
                        node_passed = True
                        node_msg = f"节点 {node_type} 执行完毕"

                    # Populate node_outputs cache dictionary
                    node_outputs_dict = {
                        "passed": node_passed,
                        "message": node_msg
                    }

                    if node_type in ["digital_signature", "signature", "digital-signature"]:
                        node_outputs_dict.update({
                            "signer_cn": context.shared_state.get("signer_cn", ""),
                            "signature_valid": context.shared_state.get("signature_valid", False),
                            "digital_signatures": context.shared_state.get("digital_signatures", {})
                        })
                    elif node_type in ["qr_scanner", "qr-code", "qr_scanner"]:
                        node_outputs_dict.update({
                            "qr_content": context.shared_state.get("qr_content", ""),
                            "qr_codes": context.shared_state.get("qr_codes", [])
                        })
                    elif node_type in ["pdf_metadata", "pdf-info", "pdf_info"]:
                        node_outputs_dict.update({
                            "pdf_info": context.shared_state.get("pdf_info", {}),
                            "page_count": context.shared_state.get("pdf_info", {}).get("page_count", 0),
                            "full_text": context.shared_state.get("full_text", "")
                        })
                    elif node_type in ["regex_match", "regex"]:
                        node_outputs_dict.update({
                            "pattern": node_data.get("pattern", "")
                        })
                    elif node_type in ["text_llm", "text-llm", "vision_llm", "vision-llm"]:
                        node_outputs_dict.update({
                            "passed": node_passed,
                            "reason": node_msg,
                            **node_llm_data
                        })
                    elif node_type in ["institution_sniffer", "institution-sniffer"]:
                        node_outputs_dict.update({
                            "institution": context.shared_state.get("institution", "UNKNOWN")
                        })
                    elif node_type in ["revision_check", "revision-check"]:
                        node_outputs_dict.update({
                            "is_tampered": context.shared_state.get("is_tampered", False),
                            "revision_count": context.shared_state.get("revision_count", 1)
                        })
                    elif node_type in ["http_call", "http-call"]:
                        node_outputs_dict.update(node_http_response)
                    elif node_type in ["variable_extractor", "variable-extractor"]:
                        node_outputs_dict.update({
                            "extracted_value": context.shared_state.get("extracted_value", ""),
                            **node_extracted_groups
                        })
                    elif node_type in ["document_diff", "document-diff"]:
                        node_outputs_dict.update({
                            "similarity": node_diff_similarity if node_diff_similarity is not None else 0.0
                        })

                    context.node_outputs[node_id] = node_outputs_dict

                    # Determine node severity from node data config
                    node_severity = node_data.get("severity", "fail")
                    # Classify this node as a verification module if it has hasSeverity or is a known check type
                    is_verification_module = node_data.get("hasSeverity", False) or node_type in [
                        "digital_signature", "signature", "qr_scanner", "qr-code", 
                        "revision_check", "revision-check", "pdf_metadata", "pdf-info",
                        "regex_match", "regex", "comparison", "data-compare", "keyword",
                        "text_llm", "text-llm", "vision_llm", "vision-llm", 
                        "http_call", "http-call", "stamp_detection", 
                        "document_diff", "document-diff", "variable_extractor", 
                        "variable-extractor", "table_verification"
                    ]

                    active_checks.append(node_msg)
                    if not node_passed:
                        failed_checks.append((node_msg, node_severity))

                    # Record per-node module result for fine-grained scoring
                    if is_verification_module:
                        executed_modules.append({
                            "node_id": node_id,
                            "node_type": node_type,
                            "label": node.get("label", node_type),
                            "passed": node_passed,
                            "message": node_msg,
                            "severity": node_severity
                        })
                        
                    # Follow active edges based on node result
                    edges_out = outgoing_edges.get(node_id, [])
                    for edge in edges_out:
                        handle = edge.get("sourceHandle")
                        should_follow = False
                        if node_passed:
                            should_follow = not handle or handle in ["pass", "success"]
                        else:
                            should_follow = handle == "fail"
                            
                        if should_follow:
                            target = edge.get("target")
                            if target:
                                queue.append(target)

                # --- Node-level scoring for logic_graph ---
                # Each executed verification module node is scored individually
                if executed_modules:
                    for mod in executed_modules:
                        mod_sev = mod["severity"]
                        mod_passed = mod["passed"]
                        mod_label = mod.get("label", mod["node_type"])

                        if mod_sev == "reference":
                            reference_count += 1
                            mod_status = "info"
                        elif mod_passed:
                            pass_count += 1
                            mod_status = "pass"
                        elif mod_sev == "warning":
                            warning_count += 1
                            mod_status = "warning"
                        elif mod_sev == "review":
                            warning_count += 1
                            needs_review = True
                            mod_status = "warning"
                        else:
                            fail_count += 1
                            mod_status = "fail"

                        rule_evaluations.append({
                            "name": f"{rule.rule_name} > {mod_label}",
                            "status": mod_status,
                            "rule_name": rule.rule_name,
                            "rule_type": rule.rule_type.value,
                            "passed": mod_passed,
                            "message": mod["message"],
                            "severity": mod_sev,
                            "confidence": confidence
                        })
                else:
                    # Fallback: no verification modules found, score rule as a whole
                    critical_failures = [msg for msg, sev in failed_checks if sev == "fail"]
                    if not critical_failures:
                        rule_pass = True
                        rule_msg = "可视化校验通过：" + "；".join(active_checks)
                    else:
                        rule_pass = False
                        rule_msg = "可视化校验未通过：" + "；".join([msg for msg, _ in failed_checks])

                    if rule.severity.value == "reference":
                        reference_count += 1
                        status_val = "info"
                    elif rule_pass:
                        pass_count += 1
                        status_val = "pass"
                    elif rule.severity.value == "warning":
                        warning_count += 1
                        status_val = "warning"
                    else:
                        fail_count += 1
                        status_val = "fail"

                    rule_evaluations.append({
                        "name": rule.rule_name,
                        "status": status_val,
                        "rule_name": rule.rule_name,
                        "rule_type": rule.rule_type.value,
                        "passed": rule_pass,
                        "message": rule_msg,
                        "severity": rule.severity.value,
                        "confidence": confidence
                    })

                # Skip the generic tally below — logic_graph is already tallied per-module
                continue

            else:
                # Fallback for old rule types (keyword, regex, llm) 
                # This logic can be moved to dedicated TextOperators later
                rule_msg = f"引擎尚未适配该规则类型 ({rule.rule_type})"
                rule_pass = False

            # Tally stats — reference severity is excluded from scoring (non-logic_graph rules)
            if rule.severity.value == "reference":
                reference_count += 1
            elif rule_pass:
                pass_count += 1
            else:
                if rule.severity.value == "warning":
                    warning_count += 1
                elif rule.severity.value == "review":
                    warning_count += 1
                    needs_review = True
                else:
                    fail_count += 1

            # Check if confidence is low enough to trigger human review
            if confidence < 0.85:
                needs_review = True

            # For reference rules: status is always 'info' regardless of pass/fail
            if rule.severity.value == "reference":
                status_val = "info"
            else:
                status_val = "pass" if rule_pass else ("warning" if rule.severity.value == "warning" else "fail")
            rule_evaluations.append({
                "name": rule.rule_name,
                "status": status_val,
                "rule_name": rule.rule_name,
                "rule_type": rule.rule_type.value,
                "passed": rule_pass,
                "message": rule_msg,
                "severity": rule.severity.value,
                "confidence": confidence
            })

        logger.info(f"[Engine] Verification complete. Pass:{pass_count}, Fail:{fail_count}, Reference:{reference_count}")

        # Count module results
        module_pass_count = 0
        module_warning_count = 0
        module_fail_count = 0
        module_info_count = 0

        for module_result in global_module_results:
            if module_result["status"] == "pass":
                module_pass_count += 1
            elif module_result["status"] == "warning":
                module_warning_count += 1
            elif module_result["status"] == "fail":
                module_fail_count += 1
            elif module_result["status"] == "info":
                module_info_count += 1

        # Combine rule and module evaluations
        combined_evaluations = rule_evaluations + [
            {**mr, "rule_type": "module"} for mr in global_module_results
        ]

        return {
            "checks": combined_evaluations,
            "operator_logs": operator_results,
            "pass_count": pass_count + module_pass_count,
            "warning_count": warning_count + module_warning_count,
            "fail_count": fail_count + module_fail_count,
            "reference_count": reference_count + module_info_count,
            "needs_review": needs_review,
            "institution": context.shared_state.get("institution", None),
            "matched_category": matched_category_name,
            "module_results": global_module_results
        }
