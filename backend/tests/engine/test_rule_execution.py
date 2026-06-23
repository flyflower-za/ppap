import pytest
from unittest.mock import patch, MagicMock
from app.engine.base import DocumentContext
from app.engine.core import VerificationEngine
from app.models.rule import VerificationRule, RuleType, Severity
from app.engine.operators.diff_operator import DocumentDiffOperator

@pytest.mark.asyncio
async def test_logic_graph_variable_extraction_and_diff():
    # 1. Setup mock HTTP responses and extract_text patch
    # We want to patch _extract_text_from_bytes in DocumentDiffOperator so we don't need real PDF files
    
    current_text_mock = "扫描二维码: No:12345678;Code:ABCD99. 本文是一份采购单。"
    base_text_mock = "扫描二维码: No:12345678;Code:ABCD99. 本文是一份采购单。"
    
    def mock_extract(self, pdf_bytes):
        # Return base_text if downloading from base URL, otherwise current_text
        if pdf_bytes == b"MOCK_BASE_PDF_BYTES":
            return base_text_mock, 1
        return current_text_mock, 1

    # Setup context with mock pdf bytes and qr scanner content
    context = DocumentContext(
        file_path="dummy.pdf",
        file_type="quality_report",
        shared_state={
            "pdf_bytes": b"MOCK_CURRENT_PDF_BYTES",
            "qr_codes": [{"page": 1, "data": "No:12345678;Code:ABCD99"}]
        }
    )

    # 2. Define the logic graph rule
    graph_rule = VerificationRule(
        rule_name="QR -> Variable Extract -> Document Diff Flow",
        rule_type=RuleType.logic_graph,
        rule_content="AST GRAPH",
        severity=Severity.fail,
        logic_config={
            "nodes": [
                # Start: Input
                {"id": "node_input", "type": "input", "position": {"x": 0, "y": 0}},
                
                # QR code scan (will run automatically because qr_codes in shared_state)
                {"id": "node_qr", "type": "qr_scanner", "label": "qr_scanner", "position": {"x": 100, "y": 0}},
                
                # Variable extractor: parse qr_content with regex named groups
                {
                    "id": "node_extract",
                    "type": "variable_extractor",
                    "label": "正则变量提取器",
                    "position": {"x": 200, "y": 0},
                    "data": {
                        "source_field": "qr_content",
                        "pattern": r"No:(?P<report_number>\d+);Code:(?P<verification_code>[A-Z0-9]+)"
                    }
                },
                
                # Document diff: download reference from base URL templated with variables
                {
                    "id": "node_diff",
                    "type": "document_diff",
                    "label": "原件一致性比对",
                    "position": {"x": 300, "y": 0},
                    "data": {
                        "base_document_url": "http://mock-server/docs/{{report_number}}?code={{verification_code}}",
                        "similarity_threshold": 95.0,
                        "severity": "fail",
                        "hasSeverity": True
                    }
                },
                
                # End: Output
                {"id": "node_output", "type": "output", "position": {"x": 400, "y": 0}}
            ],
            "edges": [
                {"id": "e1", "source": "node_input", "target": "node_qr"},
                {"id": "e2", "source": "node_qr", "target": "node_extract", "sourceHandle": "pass"},
                {"id": "e3", "source": "node_extract", "target": "node_diff", "sourceHandle": "pass"},
                {"id": "e4", "source": "node_diff", "target": "node_output", "sourceHandle": "pass"}
            ]
        }
    )

    # Mock HTTP download request
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"MOCK_BASE_PDF_BYTES"
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_resp) as mock_get:
        with patch("app.engine.operators.qr_operator.decode_pdf_qrcodes", return_value=[{"page": 1, "data": "No:12345678;Code:ABCD99"}]):
            with patch.object(DocumentDiffOperator, "_extract_text_from_bytes", mock_extract):
                engine = VerificationEngine()
                result = await engine.run(context, [graph_rule])
                
                # Print result checks for debugging
                print("RESULT CHECKS:", result["checks"])
                print("OPERATOR LOGS:", result["operator_logs"])
                
                # Assert execution passed
                assert result["pass_count"] > 0
                assert result["fail_count"] == 0
            
            # Assert variables were extracted correctly into shared state
            assert context.shared_state.get("report_number") == "12345678"
            assert context.shared_state.get("verification_code") == "ABCD99"
            
            # Assert httpx.AsyncClient.get was called with the interpolated URL
            mock_get.assert_called_once_with("http://mock-server/docs/12345678?code=ABCD99")

            # Check that diff log is present
            checks = result.get("checks", [])
            diff_check = next((c for c in checks if "原件一致性比对" in c["name"]), None)
            assert diff_check is not None
            assert diff_check["passed"] is True
            assert "100.0%" in diff_check["message"]

            # Check operator log is populated under both keys
            assert "DocumentDiff" in result["operator_logs"]
            assert "DocumentDiffOperator" in result["operator_logs"]
            assert result["operator_logs"]["DocumentDiff"]["pass_status"] is True
            assert result["operator_logs"]["DocumentDiff"]["extracted_data"]["similarity"] == 100.0


@pytest.mark.asyncio
async def test_logic_graph_dify_variable_interpolation():
    current_text_mock = "扫描二维码: No:87654321;Code:XYZ789. 本文是一份采购单。"
    base_text_mock = "扫描二维码: No:87654321;Code:XYZ789. 本文是一份采购单。"
    
    def mock_extract(self, pdf_bytes):
        if pdf_bytes == b"MOCK_BASE_PDF_BYTES":
            return base_text_mock, 1
        return current_text_mock, 1

    context = DocumentContext(
        file_path="dummy.pdf",
        file_type="quality_report",
        shared_state={
            "pdf_bytes": b"MOCK_CURRENT_PDF_BYTES",
            "qr_codes": [{"page": 1, "data": "No:87654321;Code:XYZ789"}]
        }
    )

    # Define logic graph rule with Dify-style structured variables: {{#node_extract.report_number#}}
    graph_rule = VerificationRule(
        rule_name="Dify Variable Flow Test",
        rule_type=RuleType.logic_graph,
        rule_content="AST GRAPH",
        severity=Severity.fail,
        logic_config={
            "nodes": [
                {"id": "node_input", "type": "input", "position": {"x": 0, "y": 0}},
                {"id": "node_qr", "type": "qr_scanner", "label": "qr_scanner", "position": {"x": 100, "y": 0}},
                {
                    "id": "node_extract",
                    "type": "variable_extractor",
                    "label": "正则变量提取器",
                    "position": {"x": 200, "y": 0},
                    "data": {
                        "source_field": "qr_content",
                        "pattern": r"No:(?P<report_number>\d+);Code:(?P<verification_code>[A-Z0-9]+)"
                    }
                },
                {
                    "id": "node_diff",
                    "type": "document_diff",
                    "label": "原件一致性比对",
                    "position": {"x": 300, "y": 0},
                    "data": {
                        "base_document_url": "http://mock-server/docs/{{#node_extract.report_number#}}?code={{#node_extract.verification_code#}}",
                        "similarity_threshold": 95.0,
                        "severity": "fail",
                        "hasSeverity": True
                    }
                },
                {"id": "node_output", "type": "output", "position": {"x": 400, "y": 0}}
            ],
            "edges": [
                {"id": "e1", "source": "node_input", "target": "node_qr"},
                {"id": "e2", "source": "node_qr", "target": "node_extract", "sourceHandle": "pass"},
                {"id": "e3", "source": "node_extract", "target": "node_diff", "sourceHandle": "pass"},
                {"id": "e4", "source": "node_diff", "target": "node_output", "sourceHandle": "pass"}
            ]
        }
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"MOCK_BASE_PDF_BYTES"
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_resp) as mock_get:
        with patch("app.engine.operators.qr_operator.decode_pdf_qrcodes", return_value=[{"page": 1, "data": "No:87654321;Code:XYZ789"}]):
            with patch.object(DocumentDiffOperator, "_extract_text_from_bytes", mock_extract):
                engine = VerificationEngine()
                result = await engine.run(context, [graph_rule])
                
                assert result["pass_count"] > 0
                assert result["fail_count"] == 0
            
            # Assert Dify variable resolution in http request mock URL
            mock_get.assert_called_once_with("http://mock-server/docs/87654321?code=XYZ789")
