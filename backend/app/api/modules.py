from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Dict, Any, Optional
import os
import shutil
import tempfile
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.engine.core import VerificationEngine
from app.engine.base import DocumentContext
from app.services.file_service import FileService

router = APIRouter()
engine = VerificationEngine()

@router.get("/list", response_model=Dict[str, Any])
async def list_modules(current_user: User = Depends(get_current_user)):
    """
    List all available operators and their configurable parameters for the sandbox.
    """
    # Hardcoded metadata for known operators to render UI forms
    operators_meta = [
        {
            "name": "VisionLLM",
            "label": "视觉大模型分析 (VisionLLM)",
            "description": "基于图像的视觉推理，适合需要看图、看版面布局的规则",
            "params": [
                {"key": "prompt", "label": "系统提示词 (Prompt)", "type": "textarea", "default": "请检查文档图片是否包含完整的盖章审批流程。"},
                {"key": "target_page", "label": "目标页码 (Page)", "type": "number", "default": 1}
            ]
        },
        {
            "name": "TextLLM",
            "label": "文本语义大模型 (TextLLM)",
            "description": "基于纯文本的语义分析，速度快，适合纯文字内容的审核",
            "params": [
                {"key": "prompt", "label": "系统提示词 (Prompt)", "type": "textarea", "default": "请检查文档内容是否包含完整的审批流签字。"}
            ]
        },
        {
            "name": "InstitutionSniffer",
            "label": "签发机构嗅探 (Sniffer)",
            "description": "通过正则表达式和文本块分析，提取文件的签发/出具机构名称",
            "params": []
        },
        {
            "name": "QRScanner",
            "label": "二维码识别 (QRScanner)",
            "description": "识别文档内所有的二维码并提取其中的文本链接信息",
            "params": []
        },
        {
            "name": "SignatureVerifier",
            "label": "数字签名校验 (Signature)",
            "description": "基于 PDF 密码学的电子印章和数字签名防伪校验",
            "params": []
        },
        {
            "name": "RevisionCheck",
            "label": "修订版本检查 (RevisionCheck)",
            "description": "分析 PDF 文件是否经过非法的增量修订或篡改",
            "params": []
        },
        {
            "name": "URLFetchOperator",
            "label": "远端 PDF 拉取 (URL Fetch)",
            "description": "通过 URL 下载 PDF 并自动提取其中的文本与基础信息",
            "params": [
                {"key": "url", "label": "PDF 下载链接 (URL)", "type": "textarea", "default": "https://example.com/sample.pdf"}
            ]
        },
        {
            "name": "StampDetection",
            "label": "物理公章/印章检测 (StampDetection)",
            "description": "基于计算机视觉检测文档中是否包含红色的物理印章或公章",
            "params": []
        },
        {
            "name": "DocumentDiff",
            "label": "智能文档差异比对 (DocumentDiff)",
            "description": "计算当前文档与基准文档在纯文本级别上的相似度和差异信息",
            "params": [
                {"key": "base_document_url", "label": "基准文档URL", "type": "textarea", "default": ""},
                {"key": "similarity_threshold", "label": "相似度警告阈值 (%)", "type": "number", "default": 95}
            ]
        },
        {
            "name": "TableVerification",
            "label": "结构化表格提取与对账 (TableVerification)",
            "description": "使用专业表格引擎精准提取行列数据，并支持简单的数学列求和验证",
            "params": [
                {"key": "target_column_index", "label": "数值求和目标列 (索引自0开始, -1为不求和)", "type": "number", "default": -1}
            ]
        }
    ]
    
    return {"modules": operators_meta}

@router.post("/test")
async def test_module(
    operator_name: str = Form(...),
    params: str = Form("{}"),
    file_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    import json
    try:
        parsed_params = json.loads(params)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in params")
        
    operator = engine._available_operators.get(operator_name)
    if not operator:
        raise HTTPException(status_code=404, detail=f"Operator {operator_name} not found")

    temp_file_path = None
    
    try:
        # Determine the file path
        if operator_name == "URLFetchOperator":
            # For URLFetchOperator, we don't need a file upfront
            temp_file_path = ""
        elif file_id:
            from app.services.file_service import FileService
            file_service = FileService(db)
            db_file = await file_service.get_file(file_id)
            if not db_file:
                raise HTTPException(status_code=404, detail="File not found in database")
            
            from app.core.minio_client import minio_client
            pdf_bytes = minio_client.download_file(db_file.file_path)
            
            # Download file from MinIO to temp location
            import tempfile
            _, temp_ext = os.path.splitext(db_file.original_filename)
            fd, temp_file_path = tempfile.mkstemp(suffix=temp_ext)
            os.close(fd)
            with open(temp_file_path, "wb") as f:
                f.write(pdf_bytes)
            
        elif file:
            import tempfile
            _, temp_ext = os.path.splitext(file.filename)
            fd, temp_file_path = tempfile.mkstemp(suffix=temp_ext)
            os.close(fd)
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        else:
            raise HTTPException(status_code=400, detail="Must provide either file_id or a file upload")

        # Build DocumentContext
        context = DocumentContext(file_path=temp_file_path)
        if temp_file_path:
            with open(temp_file_path, "rb") as f:
                context.shared_state["pdf_bytes"] = f.read()
        
        # If the operator needs PDFInfo (most do, for page parsing), we run PDFInfoExtractor first, unless we are testing it
        if operator_name != "PDFInfoExtractor":
            pdf_op = engine._available_operators.get("PDFInfoExtractor")
            if pdf_op:
                await pdf_op.execute(context)
                
        # Run the specific operator
        result = await operator.execute(context, **parsed_params)
        
        return {
            "status": "success",
            "operator": operator_name,
            "pass_status": result.pass_status,
            "message": result.message,
            "extracted_data": result.extracted_data,
            "shared_state": {k: v for k, v in context.shared_state.items() if k not in ["full_text", "pdf_bytes"]} # Exclude large text and binary data for clarity
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "operator": operator_name,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
    finally:
        # Cleanup temp file
        cleanup_path = temp_file_path
        if 'context' in locals() and hasattr(context, 'file_path') and context.file_path:
            cleanup_path = context.file_path
            
        if cleanup_path and os.path.exists(cleanup_path):
            try:
                os.remove(cleanup_path)
            except Exception:
                pass
