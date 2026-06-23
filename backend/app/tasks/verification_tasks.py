import asyncio
import json
import random
import time
from datetime import datetime
from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app
from app.core.database import async_session_maker
from app.core.minio_client import minio_client
from app.models.file import File, FileStatus, FileType
from app.models.task import Task, TaskStatus
from app.models.notification import Notification, NotificationType
from app.models.rule import VerificationRule, RuleType, Severity, DocumentCategory
from app.models.verification_module import VerificationModule
from app.core.redis import redis_client
import re

# Import localized checker modules
from app.checkers.qr_decoder import decode_pdf_qrcodes
from app.checkers.sig_verifier import verify_pdf_signatures
from app.checkers.pdf_info import check_pdf_text_layer
from app.checkers.revision_checker import check_revision_after_signing

logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def queue_verification_task(self, file_id: str):
    """
    Background task to execute the multi-stage PDF verification process.
    Integrates 4 key local checks:
      1. Whether PDF is text-based (searchable)
      2. Digital signature verification & signer CN extraction
      3. QR code identification & decoding
      4. Page count & Binding integrity (cross-referenced with signatures)
    """
    logger.info(f"Triggered background verification task for File ID: {file_id}")

    async def _async_verification():
        async with async_session_maker() as db:
            # 1. Fetch file record
            file_record = await db.get(File, file_id)
            if not file_record:
                logger.error(f"File {file_id} not found in database.")
                return

            # Helper to publish progress dynamically
            async def publish_progress(progress_val: int, status_val: str, step_msg: str):
                try:
                    if not redis_client.redis:
                        await redis_client.connect()
                    await redis_client.redis.publish(
                        f"file_progress:{file_id}",
                        json.dumps({
                            "file_id": file_id,
                            "progress": progress_val,
                            "status": status_val,
                            "current_step": step_msg
                        })
                    )
                except Exception as pub_err:
                    logger.warning(f"Failed to publish progress to Redis: {pub_err}")

            # Initialize timing
            start_time = datetime.utcnow()

            # Create Task status tracking record
            task_record = Task(
                file_id=file_id,
                task_type="verify",
                status=TaskStatus.RUNNING,
                progress=10,
                current_step="初始化智能校验引擎...",
                celery_task_id=self.request.id,
                started_at=start_time,
            )
            db.add(task_record)

            # Update File state to Processing
            file_record.status = FileStatus.PROCESSING
            file_record.verification_progress = 10
            file_record.verification_model = "Local Checker Engine v3.0 (PDF Standardized)"
            await db.commit()
            await publish_progress(10, FileStatus.PROCESSING.value, "初始化智能校验引擎...")

            # ============================================================
            # Stage 1: Download PDF from MinIO
            # ============================================================
            await asyncio.sleep(0.8)
            task_record.progress = 20
            task_record.current_step = "正在下载原 PDF 文件..."
            file_record.verification_progress = 20
            await db.commit()
            await publish_progress(20, FileStatus.PROCESSING.value, "正在下载原 PDF 文件...")

            # Download the actual PDF bytes from MinIO
            pdf_bytes = None
            try:
                pdf_bytes = minio_client.download_file(file_record.file_path)
                logger.info(f"Downloaded PDF from MinIO: {len(pdf_bytes)} bytes")
            except Exception as e:
                logger.warning(f"Could not download PDF from MinIO: {e}.")

            # ============================================================
            # Stage 2: Initialize Context and Execute Dynamic Engine
            # ============================================================
            await asyncio.sleep(0.8)
            task_record.progress = 40
            task_record.current_step = "正在构建文档上下文并启动动态规则引擎..."
            file_record.verification_progress = 40
            await db.commit()
            await publish_progress(40, FileStatus.PROCESSING.value, "正在构建文档上下文并启动动态规则引擎...")

            from app.engine.core import VerificationEngine
            from app.engine.base import DocumentContext
            from sqlalchemy import select

            context = DocumentContext(
                file_path=file_record.file_path,
                file_type=file_record.file_type.value,
                shared_state={"pdf_bytes": pdf_bytes} if pdf_bytes else {}
            )

            # Load verification rules and their associated modules
            # Fetch active rules and categories
            result = await db.execute(select(VerificationRule).where(VerificationRule.is_active == True))
            active_rules = result.scalars().all()

            cat_result = await db.execute(select(DocumentCategory).where(DocumentCategory.is_active == True))
            active_categories = cat_result.scalars().all()

            # Array to capture detailed trajectory logs from the engine
            trajectory_logs = []

            async def engine_progress_cb(msg: str):
                log_entry = {
                    "time": datetime.utcnow().isoformat() + "Z",
                    "message": msg
                }
                trajectory_logs.append(log_entry)
                # Keep progress pinned at 60 while engine does work, but update the step_msg
                await publish_progress(60, FileStatus.PROCESSING.value, msg)

            # Build mapping of rule_id -> List[VerificationModule]
            rule_to_modules = {}
            all_active_modules = []
            try:
                from sqlalchemy import select
                from app.models.verification_module import RuleModule
                
                # Fetch all junctions
                junctions_res = await db.execute(select(RuleModule))
                junctions = junctions_res.scalars().all()
                
                # Fetch all active modules
                modules_res = await db.execute(
                    select(VerificationModule)
                    .where(VerificationModule.is_active == True)
                    .order_by(VerificationModule.sort_order)
                )
                active_modules_list = modules_res.scalars().all()
                modules_by_id = {m.id: m for m in active_modules_list}
                
                for j in junctions:
                    if j.module_id in modules_by_id:
                        rule_to_modules.setdefault(j.rule_id, []).append(modules_by_id[j.module_id])
            except Exception as e:
                logger.warning(f"Failed to pre-load rule-module junctions: {e}")

            # Let Engine do the heavy lifting
            task_record.progress = 60
            task_record.current_step = "引擎执行与分析算子调度中..."
            file_record.verification_progress = 60
            await db.commit()
            await publish_progress(60, FileStatus.PROCESSING.value, "引擎执行与分析算子调度中...")

            engine = VerificationEngine()
            # Pass rule_to_modules to engine.run
            engine_result = await engine.run(
                context, 
                active_rules, 
                progress_callback=engine_progress_cb, 
                categories=active_categories,
                rule_to_modules=rule_to_modules
            )

            # ============================================================
            # Stage 3: Compile Final Report (Progress 100%)
            # ============================================================
            await asyncio.sleep(0.5)
            task_record.progress = 95
            task_record.current_step = "正在汇总智能引擎判决报告..."
            file_record.verification_progress = 95
            await db.commit()
            await publish_progress(95, FileStatus.PROCESSING.value, "正在汇总智能引擎判决报告...")

            pass_count = engine_result.get("pass_count", 0)
            warning_count = engine_result.get("warning_count", 0)
            fail_count = engine_result.get("fail_count", 0)
            reference_count = engine_result.get("reference_count", 0)
            institution = engine_result.get("institution", None)
            needs_review = engine_result.get("needs_review", False)
            # Reference items do NOT affect total_checks or pass_rate — advisory only
            total_checks = pass_count + warning_count + fail_count
            pass_rate = int((pass_count / total_checks) * 100) if total_checks > 0 else 0

            # Determine final status based on engine results
            if needs_review:
                final_status = FileStatus.NEEDS_REVIEW
            elif fail_count > 0:
                final_status = FileStatus.FAILED
            elif warning_count > 0:
                final_status = FileStatus.WARNING
            else:
                final_status = FileStatus.COMPLETED

            matched_category = engine_result.get("matched_category", None)

            # Build Result Payload
            verification_result = {
                "status": final_status.value,
                "model_version": "Next-Gen Dynamic Engine v4.0",
                "checks": engine_result.get("checks", []),
                "summary": {
                    "total": total_checks,
                    "pass": pass_count,
                    "warning": warning_count,
                    "fail": fail_count,
                    "reference": reference_count,
                    "institution": institution,
                    "needs_review": needs_review,
                    "matched_category": matched_category
                },
                "operator_logs": engine_result.get("operator_logs", {}),
                "execution_trajectory": trajectory_logs
            }

            end_time = datetime.utcnow()
            duration = int((end_time - start_time).total_seconds())

            # Update File Row
            file_record.status = final_status
            file_record.verification_progress = 100
            file_record.pass_count = pass_count
            file_record.warning_count = warning_count
            file_record.fail_count = fail_count
            file_record.pass_rate = pass_rate
            file_record.completed_at = end_time
            file_record.duration_seconds = duration
            # Extract page count from PDFInfoExtactor if it ran
            pdf_info_op_res = engine_result.get("operator_logs", {}).get("PDFInfoExtractor", {})
            if pdf_info_op_res.get("pass_status"):
                 file_record.page_count = pdf_info_op_res.get("extracted_data", {}).get("pdf_info", {}).get("page_count", 0)
            file_record.verification_result = json.dumps(verification_result)

            # Update Task tracking record
            task_record.status = TaskStatus.COMPLETED
            task_record.progress = 100
            task_record.current_step = "PDF 标准合规校验完成，报告已归档。"
            task_record.completed_at = end_time
            task_record.result = json.dumps(verification_result)

            # Generate User System Notification
            notif_type = NotificationType.WARNING if needs_review else (NotificationType.SUCCESS if final_status in [FileStatus.COMPLETED, FileStatus.WARNING] else NotificationType.ERROR)
            
            type_name = "受控合规性文件"
            if file_record.file_type == FileType.PRODUCTION_PLAN:
                type_name = "生产计划单"
            elif file_record.file_type == FileType.QUALITY_REPORT:
                type_name = "质量检测报告"
            elif file_record.file_type == FileType.PURCHASE_ORDER:
                type_name = "采购订单"

            notif_title = f"PDF【{file_record.original_filename}】标准化合规校验完成"
            if needs_review:
                notif_msg = f"该【{type_name}】存在存疑或置信度低的校验项，引擎已主动拦截并触发【人工仲裁】流程，请查阅报告并放行或驳回。"
            else:
                notif_msg = f"该【{type_name}】通过率：{pass_rate}%。共 {total_checks} 项检查中：通过 {pass_count} 项，警告 {warning_count} 项，失败 {fail_count} 项。"
            
            notification = Notification(
                user_id=file_record.uploaded_by,
                type=notif_type,
                title=notif_title,
                message=notif_msg,
                link=f"/files/{file_record.id}",
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.add(notification)

            # ─── 运行日志审计闭环 ───
            try:
                from app.core.audit_logger import log_audit_event
                from app.models.user import User
                
                # 获取真正的上传文件操作用户
                uploader_user = await db.get(User, file_record.uploaded_by)
                
                # 获取本次执行的所有算子名称
                operators_run = list(engine_result.get("operator_logs", {}).keys())
                
                await log_audit_event(
                    db=db,
                    action="RUN_VERIFICATION",
                    user=uploader_user, # 绑定真正的发起用户
                    resource_type="DOCUMENT",
                    resource_id=file_id,
                    details={
                        "filename": file_record.original_filename,
                        "status": final_status.value,
                        "pass_rate": pass_rate,
                        "pass_count": pass_count,
                        "warning_count": warning_count,
                        "fail_count": fail_count,
                        "duration_seconds": duration,
                        "operators_run": operators_run
                    },
                    request=None # 后台异步无请求
                )
            except Exception as audit_err:
                logger.warning(f"Failed to write RUN_VERIFICATION audit log: {audit_err}")

            await db.commit()
            await publish_progress(100, final_status.value, "PDF 标准合规校验完成，报告已归档。")
            logger.info(f"Verification complete for PDF File {file_id}. Status: {final_status.value}, Pass Rate: {pass_rate}%")

    # Run the async operations inside the sync Celery context and cleanly dispose connections
    async def _run_all():
        try:
            await _async_verification()
        except Exception as global_err:
            logger.error(f"Global verification task crash: {global_err}")
            # 异常时也尝试查出用户并绑定审计
            try:
                async with async_session_maker() as db:
                    from app.core.audit_logger import log_audit_event
                    from app.models.file import File
                    from app.models.user import User
                    
                    file_record = await db.get(File, file_id)
                    uploader_user = None
                    filename = "Unknown"
                    if file_record:
                        filename = file_record.original_filename
                        uploader_user = await db.get(User, file_record.uploaded_by)
                        
                    await log_audit_event(
                        db=db,
                        action="RUN_VERIFICATION",
                        user=uploader_user,
                        resource_type="DOCUMENT",
                        resource_id=file_id,
                        details={
                            "filename": filename,
                            "status": "error",
                            "error_msg": str(global_err)
                        },
                        request=None
                    )
                    await db.commit()
            except Exception as inner_err:
                logger.warning(f"Failed to log crashed RUN_VERIFICATION: {inner_err}")
            raise global_err
        finally:
            from app.core.database import engine
            try:
                await engine.dispose()
            except Exception:
                pass
                
    asyncio.run(_run_all())
