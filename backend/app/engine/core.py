import logging
from typing import List, Dict, Type
from app.models.rule import VerificationRule, RuleType
from app.engine.base import BaseOperator, DocumentContext
from app.engine.operators.qr_operator import QRScannerOperator
from app.engine.operators.signature_operator import SignatureOperator
from app.engine.operators.pdf_info_operator import PDFInfoOperator
from app.engine.operators.text_llm_operator import TextLLMOperator
from app.engine.operators.vision_llm_operator import VisionLLMOperator
from app.engine.operators.sniffer_operator import InstitutionSnifferOperator

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
            "InstitutionSniffer": InstitutionSnifferOperator(),
        }

    def _determine_required_operators(self, rules: List[VerificationRule]) -> List[BaseOperator]:
        """
        Analyze the AST/rule dependencies to figure out which operators must run.
        """
        required_names = set(["PDFInfoExtractor", "InstitutionSniffer"])
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
                if node_type == "digital_signature":
                    required_names.add("SignatureVerifier")
                elif node_type == "qr_scanner":
                    required_names.add("QRScanner")
                elif node_type == "pdf_metadata":
                    required_names.add("PDFInfoExtractor")
                elif node_type == "institution_sniffer":
                    required_names.add("InstitutionSniffer")
                elif node_type == "text_llm":
                    required_names.add("TextLLM")
                elif node_type == "vision_llm":
                    required_names.add("VisionLLM")

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
            # Check conditions (skip if mismatch)
            logic = rule.logic_config or {}
            conditions = logic.get("conditions", {})
            if conditions:
                sniffed_inst = context.shared_state.get("institution", "UNKNOWN")
                required_inst = conditions.get("institution")
                if required_inst and required_inst.lower() != sniffed_inst.lower():
                    logger.info(f"[Engine] Skipping rule {rule.rule_name} (requires {required_inst}, but sniffed {sniffed_inst})")
                    continue

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
            elif rule.rule_type == RuleType.logic_graph:
                # Dynamic Variable Interpolation helper
                def interpolate_vars(val: any, state: dict) -> any:
                    if isinstance(val, str):
                        import re
                        matches = re.findall(r'\{\{([^}]+)\}\}', val)
                        for match in matches:
                            key = match.strip()
                            replacement = state.get(key, "")
                            val = val.replace(f"{{{{{match}}}}}", str(replacement))
                        return val
                    elif isinstance(val, dict):
                        return {k: interpolate_vars(v, state) for k, v in val.items()}
                    elif isinstance(val, list):
                        return [interpolate_vars(v, state) for v in val]
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
                
                while queue:
                    node_id = queue.pop(0)
                    if node_id in visited:
                        continue
                    visited.add(node_id)
                    
                    node = nodes_by_id.get(node_id)
                    if not node:
                        continue
                        
                    node_type = node.get("type")
                    # Interpolate parameters dynamically from shared context
                    node_data = interpolate_vars(node.get("data", {}), context.shared_state)
                    
                    node_passed = True
                    node_msg = ""
                    
                    if node_type == "digital_signature":
                        sig_data = context.shared_state.get("digital_signatures", {})
                        sigs = sig_data.get("signatures", [])
                        valid_sigs = [s for s in sigs if s.get("integrity", False)]
                        
                        expected_issuer = node_data.get("expectedIssuer", "")
                        if expected_issuer and valid_sigs:
                            matched = any(expected_issuer.lower() in s.get("signer_cn", "").lower() for s in valid_sigs)
                            if matched:
                                node_passed = True
                                node_msg = f"数字签名完整，签发者匹配 [{expected_issuer}]"
                            else:
                                node_passed = False
                                node_msg = f"数字签名完整，但未匹配预期签发者 [{expected_issuer}]"
                        elif valid_sigs:
                            node_passed = True
                            node_msg = "检测到合法的数字签名"
                        else:
                            node_passed = False
                            node_msg = "缺失合法数字签名"
                            
                    elif node_type == "qr_scanner":
                        qr_data = context.shared_state.get("qr_codes", [])
                        if len(qr_data) > 0:
                            node_passed = True
                            node_msg = f"检测到 {len(qr_data)} 个二维码"
                        else:
                            node_passed = False
                            node_msg = "未检测到任何二维码"
                            
                    elif node_type == "pdf_metadata":
                        pdf_info = context.shared_state.get("pdf_info", {})
                        if pdf_info:
                            node_passed = True
                            node_msg = f"PDF元数据校验通过 (页数: {pdf_info.get('page_count', 0)})"
                        else:
                            node_passed = True
                            node_msg = "PDF元数据读取通过"
                            
                    elif node_type == "regex_match":
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
                            
                    elif node_type == "comparison":
                        field_a = node_data.get("fieldA", "")
                        field_b = node_data.get("fieldB", "")
                        val_a = context.shared_state.get(field_a) or context.shared_state.get("institution")
                        val_b = context.shared_state.get(field_b) or node_data.get("fieldBValue")
                        if val_a and val_b and str(val_a).lower() == str(val_b).lower():
                            node_passed = True
                            node_msg = f"字段一致校验通过: {field_a} == {field_b}"
                        else:
                            node_passed = False
                            node_msg = f"字段一致校验失败: {field_a} != {field_b}"
                            
                    elif node_type == "text_llm":
                        llm_results = context.shared_state.get("llm_semantic_analysis", [])
                        if llm_results:
                            res = llm_results[-1]
                            node_passed = res.get("passed", False)
                            node_msg = f"大模型审核点: {res.get('reason')}"
                        else:
                            node_passed = True
                            node_msg = "大模型节点（未运行）模拟通过"
                            
                    elif node_type == "institution_sniffer":
                        sniffed_inst = context.shared_state.get("institution", "UNKNOWN")
                        node_passed = sniffed_inst != "UNKNOWN"
                        node_msg = f"发证机构嗅探完成: {sniffed_inst}"
                        
                    else:
                        node_passed = True
                        node_msg = f"节点 {node_type} 执行完毕"
                        
                    active_checks.append(node_msg)
                    if not node_passed:
                        failed_checks.append((node_msg, node_data.get("severity", "fail")))
                        
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
                                
                critical_failures = [msg for msg, sev in failed_checks if sev == "fail"]
                if not critical_failures:
                    rule_pass = True
                    rule_msg = "可视化校验通过：" + "；".join(active_checks)
                else:
                    rule_pass = False
                    rule_msg = "可视化校验未通过：" + "；".join([msg for msg, _ in failed_checks])
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

        logger.info(f"[Engine] Verification complete. Pass:{pass_count}, Fail:{fail_count}")

        return {
            "checks": rule_evaluations,
            "operator_logs": operator_results,
            "pass_count": pass_count,
            "warning_count": warning_count,
            "fail_count": fail_count,
            "needs_review": needs_review
        }
