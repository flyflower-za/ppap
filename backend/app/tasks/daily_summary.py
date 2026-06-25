"""
Daily summary report scheduled task
"""
from datetime import datetime, timedelta, timezone
from celery.utils.log import get_task_logger
from sqlalchemy import func, select, case

from app.tasks.celery_app import celery_app
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.file import File, FileStatus
from app.models.setting import Setting
from app.models.user import User
from app.services.email_service import email_service

logger = get_task_logger(__name__)


@celery_app.task(name='app.tasks.scheduler_tasks.send_daily_summary_report')
def send_daily_summary_report():
    """
    Send daily summary report to users who have subscribed.

    This task runs every day at 8:00 AM and sends a summary of
    the previous day's file verification activities.
    """
    logger.info("Starting daily summary report task")

    async def _async_send_report():
        task_engine = create_async_engine(
            settings.DATABASE_URL, echo=settings.DEBUG,
            pool_pre_ping=True, pool_size=5, max_overflow=10,
        )
        task_session_maker = sessionmaker(
            task_engine, class_=AsyncSession, expire_on_commit=False
        )
        try:
            async with task_session_maker() as db:
                # Calculate yesterday's date range
                yesterday = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
                start_of_yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_yesterday = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

                # Get all users who have daily_summary enabled
                users_result = await db.execute(
                    func.select(User.email)
                )
                users = users_result.scalars().all()

                recipient_count = 0

                for user_email in users:
                    # Get user's notification settings
                    setting = await db.get(Setting, f"notification_settings_{user_email}")
                    if not setting:
                        continue

                    try:
                        import json
                        notif_settings = json.loads(setting.value)
                        if not notif_settings.get('daily_summary', False):
                            continue

                        if not notif_settings.get('email_enabled', False):
                            continue
                    except Exception:
                        continue

                    # Get statistics for yesterday
                    stats_result = await db.execute(
                        select(
                            func.count(File.id).label('total'),
                            func.sum(case({File.status == 'completed': 1}, else_=0)).label('completed'),
                            func.sum(case({File.status == 'warning': 1}, else_=0)).label('warnings'),
                            func.sum(case({File.status == 'failed': 1}, else_=0)).label('failed')
                        ).where(
                            File.uploaded_at >= start_of_yesterday,
                            File.uploaded_at <= end_of_yesterday,
                            File.is_deleted == False
                        )
                    )
                    stats = stats_result.first()

                    if not stats or stats.total == 0:
                        continue

                    # Get recent files for the report
                    files_result = await db.execute(
                        func.select(File)
                        .where(
                            File.uploaded_at >= start_of_yesterday,
                            File.uploaded_at <= end_of_yesterday,
                            File.is_deleted == False
                        )
                        .order_by(File.uploaded_at.desc())
                        .limit(10)
                    )
                    recent_files = files_result.scalars().all()

                    # Generate HTML report using template
                    from app.services.email_template_service import template_service

                    total = stats.total or 0
                    completed = stats.completed or 0
                    warnings = stats.warnings or 0
                    failed = stats.failed or 0

                    # Generate recent files list HTML
                    files_html = ""
                    for file in recent_files:
                        status_emoji = "✅" if file.status == "completed" else ("⚠️" if file.status == "warning" else "❌")
                        status_text = "通过" if file.status == "completed" else ("有警告" if file.status == "warning" else "失败")
                        status_class = "status-completed" if file.status == "completed" else ("status-warning" if file.status == "warning" else "status-failed")

                        files_html += f"""
                        <div class="file-item">
                            <div class="file-name">{status_emoji} {file.original_filename or file.filename}</div>
                            <div class="file-meta">
                                状态: <span class="status-badge {status_class}">{status_text}</span>
                                通过率: {file.pass_rate or 0}%
                            </div>
                        </div>
                        """

                    # Prepare template context
                    context = {
                        "date": yesterday.strftime('%Y年%m月%d日'),
                        "total_count": total,
                        "completed_count": completed,
                        "warning_count": warnings,
                        "failed_count": failed,
                        "file_list_html": files_html
                    }

                    # Try to use template
                    rendered = await template_service.render_email_template("daily_summary", context)

                    # Send email
                    try:
                        if rendered:
                            await email_service.send_email(
                                to_email=user_email,
                                subject=rendered["subject"],
                                html_body=rendered["html_content"],
                                smtp_config=None
                            )
                        else:
                            html_report = _generate_daily_summary_html(
                                yesterday,
                                stats,
                                recent_files,
                                user_email
                            )
                            await email_service.send_email(
                                to_email=user_email,
                                subject=f"文件校验平台 - 每日汇总报告 ({yesterday.strftime('%Y-%m-%d')})",
                                html_body=html_report,
                                smtp_config=None
                            )
                        recipient_count += 1
                        logger.info(f"Daily summary sent to {user_email}")
                    except Exception as e:
                        logger.error(f"Failed to send daily summary to {user_email}: {e}")

                logger.info(f"Daily summary report completed. Sent to {recipient_count} users")
        finally:
            await task_engine.dispose()

    # Run the async operations
    try:
        import asyncio
        asyncio.run(_async_send_report())
    except Exception as e:
        logger.error(f"Daily summary report task failed: {e}")


def _generate_daily_summary_html(date, stats, recent_files, user_email):
    """
    Generate HTML email content for daily summary report

    Args:
        date: The date for the report
        stats: Statistics dictionary
        recent_files: List of recent File objects
        user_email: Recipient email

    Returns:
        HTML string
    """
    total = stats.total or 0
    completed = stats.completed or 0
    warnings = stats.warnings or 0
    failed = stats.failed or 0
    pass_rate = int((completed / total * 100)) if total > 0 else 0

    # Generate recent files list
    files_html = ""
    for file in recent_files:
        status_emoji = "✅" if file.status == "completed" else ("⚠️" if file.status == "warning" else "❌")
        status_text = "通过" if file.status == "completed" else ("有警告" if file.status == "warning" else "失败")
        status_color = "#4CAF50" if file.status == "completed" else ("#FF9800" if file.status == "warning" else "#F44336")

        files_html += f"""
        <tr style="border-bottom: 1px solid #f0f0f0;">
          <td style="padding: 12px 8px;">
            <span style="color: #666;">{status_emoji}</span> {file.original_filename or file.filename}
          </td>
          <td style="padding: 12px 8px; text-align: center;">
            <span style="color: {status_color}; font-weight: 500;">{status_text}</span>
          </td>
          <td style="padding: 12px 8px; text-align: center;">{file.pass_rate or 0}%</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #4285F4 100%);
                color: white;
                padding: 30px;
                border-radius: 12px 12px 0 0;
                text-align: center;
            }}
            .content {{
                background: white;
                padding: 30px;
                border-radius: 0 0 12px 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin: 20px 0;
            }}
            .stat-card {{
                background: #f8fafc;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }}
            .stat-number {{
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 5px;
            }}
            .stat-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
            }}
            .recent-files {{
                margin-top: 30px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            th {{
                background: #f8fafc;
                padding: 12px 8px;
                text-align: left;
                font-size: 12px;
                font-weight: 600;
                color: #666;
                text-transform: uppercase;
                border-bottom: 2px solid #e0e0e0;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e0e0e0;
                text-align: center;
                font-size: 12px;
                color: #999;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; font-size: 24px;">📊 每日文件校验汇总</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 14px;">{date.strftime('%Y年%m月%d日')} 数据统计</p>
            </div>
            <div class="content">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number" style="color: #4285F4;">{total}</div>
                        <div class="stat-label">总文件数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" style="color: #4CAF50;">{completed}</div>
                        <div class="stat-label">通过</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" style="color: #FF9800;">{warnings}</div>
                        <div class="stat-label">警告</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" style="color: #F44336;">{failed}</div>
                        <div class="stat-label">失败</div>
                    </div>
                </div>

                <div class="recent-files">
                    <h3 style="margin: 0 0 15px 0; font-size: 16px;">最近处理的文件</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>文件名</th>
                                <th>状态</th>
                                <th style="text-align: center;">通过率</th>
                            </tr>
                        </thead>
                        <tbody>
                            {files_html}
                        </tbody>
                    </table>
                </div>

                <div class="footer">
                    <p style="margin: 0;">系统自动发送，请勿回复</p>
                    <p style="margin: 5px 0 0 0;">
                        <a href="#" style="color: #4285F4; text-decoration: none;">登录系统查看详情</a>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html
