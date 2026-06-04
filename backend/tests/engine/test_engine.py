import pytest
from app.engine.base import DocumentContext
from app.engine.operators.sniffer_operator import InstitutionSnifferOperator
from app.engine.core import VerificationEngine
from app.models.rule import VerificationRule, RuleType, Severity

@pytest.mark.asyncio
async def test_sniffer_operator_cti():
    operator = InstitutionSnifferOperator()
    context = DocumentContext(
        file_path="dummy.pdf",
        file_type="quality_report",
        shared_state={"full_text": "这是一个由华测检测 (CTI) 签发的报告。"}
    )
    
    result = await operator.execute(context)
    assert result.pass_status is True
    assert context.shared_state["institution"] == "CTI"
    assert result.extracted_data["institution"] == "CTI"


@pytest.mark.asyncio
async def test_sniffer_operator_sgs():
    operator = InstitutionSnifferOperator()
    context = DocumentContext(
        file_path="dummy.pdf",
        file_type="quality_report",
        shared_state={"full_text": "SGS testing services report."}
    )
    
    result = await operator.execute(context)
    assert result.pass_status is True
    assert context.shared_state["institution"] == "SGS"
    assert result.extracted_data["institution"] == "SGS"


@pytest.mark.asyncio
async def test_engine_skips_mismatched_rules():
    # Set up engine and context with CTI institution and non-empty qr_codes to pass the rule
    engine = VerificationEngine()
    context = DocumentContext(
        file_path="dummy.pdf",
        file_type="quality_report",
        shared_state={
            "full_text": "这是一个由华测检测 (CTI) 签发的报告。",
            "institution": "CTI",
            "qr_codes": [{"page": 1, "data": "http://example.com"}]
        }
    )
    
    # Create rules
    # 1. A rule requiring CTI institution (should match and run)
    rule_cti = VerificationRule(
        rule_name="CTI Rule",
        rule_type=RuleType.plugin,
        rule_content="REQUIRE_QR_CODE",
        severity=Severity.fail,
        logic_config={"conditions": {"institution": "CTI"}}
    )
    # 2. A rule requiring SGS institution (should skip)
    rule_sgs = VerificationRule(
        rule_name="SGS Rule",
        rule_type=RuleType.plugin,
        rule_content="REQUIRE_QR_CODE",
        severity=Severity.fail,
        logic_config={"conditions": {"institution": "SGS"}}
    )
    
    # Run the engine
    result = await engine.run(context, [rule_cti, rule_sgs])
    
    # The CTI rule should be processed (it should pass because qr_codes is not empty)
    # The SGS rule should be skipped, so it shouldn't fail the verification or be counted.
    assert result["pass_count"] == 1
    assert result["fail_count"] == 0
    
    # Check skipped logs or rules summary
    rules_summary = result.get("checks", [])
    # Find matching rules in summary
    cti_summary = next((r for r in rules_summary if r["rule_name"] == "CTI Rule"), None)
    sgs_summary = next((r for r in rules_summary if r["rule_name"] == "SGS Rule"), None)
    
    assert cti_summary is not None
    assert cti_summary["passed"] is True
    # SGS rule is skipped so it shouldn't be executed or should be omitted
    assert sgs_summary is None


@pytest.mark.asyncio
async def test_logic_graph_rule_evaluation():
    engine = VerificationEngine()
    
    context = DocumentContext(
        file_path="dummy.pdf",
        file_type="quality_report",
        shared_state={
            "full_text": "这是一个由华测检测 (CTI) 签发的报告。",
            "institution": "CTI",
            "qr_codes": [{"page": 1, "data": "http://example.com"}],
            "digital_signatures": {
                "signed": True,
                "signatures": [{"integrity": True, "signer_cn": "Centre Testing International Group Co., Ltd."}]
            }
        }
    )
    
    # Logic graph rule with QR Scanner and Digital Signature checks
    graph_rule = VerificationRule(
        rule_name="Visual Multi-check Rule",
        rule_type=RuleType.logic_graph,
        rule_content="AST GRAPH",
        severity=Severity.fail,
        logic_config={
            "nodes": [
                {"id": "1", "type": "qr_scanner", "data": {"severity": "fail"}},
                {"id": "2", "type": "digital_signature", "data": {"expectedIssuer": "Centre Testing International", "severity": "fail"}}
            ],
            "edges": []
        }
    )
    
    result = await engine.run(context, [graph_rule])
    
    assert result["pass_count"] == 2
    assert result["fail_count"] == 0
    
    checks = result.get("checks", [])
    assert len(checks) == 2
    for c in checks:
        assert c["passed"] is True
    
    messages = [c["message"] for c in checks]
    assert any("检测到 1 个二维码" in m for m in messages)
    assert any("签发者匹配" in m for m in messages)


@pytest.mark.asyncio
async def test_logic_graph_dag_and_interpolation():
    engine = VerificationEngine()
    
    # 1. Test case where QR Scanner passes, executing signature verifier along the 'pass' edge,
    # and skipping a failing regex_match node connected along the 'fail' edge.
    # Also tests dynamic variable interpolation: regex matches on the interpolated {{institution}} which resolves to "CTI".
    context = DocumentContext(
        file_path="dummy.pdf",
        file_type="quality_report",
        shared_state={
            "full_text": "这是一个由华测检测 (CTI) 签发的报告。",
            "institution": "CTI",
            "qr_codes": [{"page": 1, "data": "http://example.com"}],
            "digital_signatures": {
                "signed": True,
                "signatures": [{"integrity": True, "signer_cn": "Centre Testing International Group Co., Ltd."}]
            }
        }
    )
    
    graph_rule = VerificationRule(
        rule_name="DAG Edge Routing and Interpolation Rule",
        rule_type=RuleType.logic_graph,
        rule_content="AST GRAPH",
        severity=Severity.fail,
        logic_config={
            "nodes": [
                # 1. QR Scanner (Start node, will pass)
                {"id": "node_qr", "type": "qr_scanner", "data": {"severity": "fail"}},
                
                # 2. Digital Signature (Connected along QR's pass edge, will execute and pass)
                {"id": "node_sig", "type": "digital_signature", "data": {"expectedIssuer": "Centre Testing International", "severity": "fail"}},
                
                # 3. Dynamic Regex Match (Connected along QR's fail edge, should NOT execute at all)
                {"id": "node_regex_fail", "type": "regex_match", "data": {"pattern": "NON_EXISTENT_PATTERN_12345", "severity": "fail"}},
                
                # 4. Interpolated Regex Match (Independent node, will execute and pass using {{institution}})
                {"id": "node_regex_interpolate", "type": "regex_match", "data": {"pattern": "{{institution}}", "severity": "fail"}}
            ],
            "edges": [
                # Connect QR success -> Digital Signature
                {"id": "edge_pass", "source": "node_qr", "target": "node_sig", "sourceHandle": "pass"},
                # Connect QR fail -> Failing Regex Match (should be skipped!)
                {"id": "edge_fail", "source": "node_qr", "target": "node_regex_fail", "sourceHandle": "fail"}
            ]
        }
    )
    
    result = await engine.run(context, [graph_rule])
    
    # It should pass because:
    # - QR scanner passed
    # - Sig verifier passed (visited via QR pass edge)
    # - Node_regex_fail was NOT traversed/executed (so its failure was skipped!)
    # - Node_regex_interpolate passed (visited as an entry node, successfully matched 'CTI')
    assert result["pass_count"] == 3
    assert result["fail_count"] == 0
    
    checks = result.get("checks", [])
    assert len(checks) == 3
    for c in checks:
        assert c["passed"] is True
        
    messages = [c["message"] for c in checks]
    assert any("检测到 1 个二维码" in m for m in messages)
    assert any("签发者匹配" in m for m in messages)
    assert any("正则匹配成功: [CTI]" in m for m in messages)
    
    # Verify node_regex_fail was skipped and is NOT in the active checks log
    for c in checks:
        assert "正则未匹配" not in c["message"]

