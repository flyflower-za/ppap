"""
Email Service for sending emails via SMTP
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import asyncio
from email.utils import formataddr

from app.api.settings import SmtpConfig


class EmailService:
    """Service for sending emails using SMTP"""

    def __init__(self):
        self.smtp_host = None
        self.smtp_port = None
        self.smtp_use_tls = None

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        smtp_config: Optional[SmtpConfig] = None
    ):
        """
        Send an email using SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML body content
            text_body: Plain text body content (fallback)
            smtp_config: SMTP configuration (uses env if None)
        """
        if smtp_config is None:
            # Try to load from database first
            try:
                from app.core.database import async_session_maker
                from app.models.setting import Setting
                import json
                async with async_session_maker() as db:
                    result = await db.get(Setting, "smtp_config")
                    if result:
                        data = json.loads(result.value)
                        smtp_config = SmtpConfig(**data)
            except Exception:
                # Fallback if DB is not initialized or unreachable
                pass

        if smtp_config is None:
            # Load from environment
            import os
            smtp_config = SmtpConfig(
                enabled=os.getenv("SMTP_ENABLED", "false").lower() == "true",
                host=os.getenv("SMTP_HOST"),
                port=int(os.getenv("SMTP_PORT", "587")),
                encryption="tls" if os.getenv("SMTP_USE_TLS", "true").lower() == "true" else "none",
                username=os.getenv("SMTP_USERNAME"),
                from_name=os.getenv("SMTP_FROM", "文件校验平台"),
                password=os.getenv("SMTP_PASSWORD")
            )

        if not smtp_config.enabled or not smtp_config.host:
            raise ValueError("SMTP 未配置或未启用")

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr((smtp_config.from_name, smtp_config.username))
        msg['To'] = to_email

        # Attach HTML body
        msg.attach(MIMEText(html_body, 'html'))

        # Attach text body if provided
        if text_body:
            msg.attach(MIMEText(text_body, 'plain'))

        # Send email in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._send_sync,
            msg,
            smtp_config
        )

    def _send_sync(self, msg, smtp_config: SmtpConfig):
        """Synchronously send email (runs in thread pool)"""
        # Determine SSL/TLS usage
        if smtp_config.encryption == 'ssl':
            smtp_port = smtp_config.port or 465
            server = smtplib.SMTP_SSL(smtp_config.host, smtp_port, timeout=30)
        else:
            smtp_port = smtp_config.port or 587
            server = smtplib.SMTP(smtp_config.host, smtp_port, timeout=30)
            if smtp_config.encryption == 'tls':
                server.starttls()

        # Login if credentials provided (some SMTP servers don't require auth)
        if smtp_config.username and smtp_config.password:
            try:
                server.login(smtp_config.username, smtp_config.password)
            except smtplib.SMTPException as e:
                # If login fails but server doesn't require auth, continue
                if "550" not in str(e) and "535" not in str(e):
                    raise

        server.send_message(msg)
        server.quit()

    async def send_test_email(
        self,
        smtp_config: SmtpConfig,
        to_email: str
    ):
        """
        Send a test email to verify SMTP configuration

        Args:
            smtp_config: SMTP configuration to test
            to_email: Recipient email address
        """
        from app.services.email_template_service import template_service

        # Try to use template
        context = {
            "from_name": smtp_config.from_name,
            "smtp_host": smtp_config.host,
            "smtp_port": smtp_config.port,
            "encryption": smtp_config.encryption.upper(),
            "username": smtp_config.username
        }

        rendered = await template_service.render_email_template("smtp_test", context)

        if rendered:
            # Use template
            await self.send_email(
                to_email=to_email,
                subject=rendered["subject"],
                html_body=rendered["html_content"],
                smtp_config=smtp_config
            )
        else:
            # Fallback to hardcoded template
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #4285F4;">SMTP 测试邮件</h2>
                    <p>您好！</p>
                    <p>这是一封来自 <strong>{smtp_config.from_name}</strong> 的测试邮件。</p>
                    <p>如果您收到此邮件，说明 SMTP 配置成功！</p>
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #eee;">
                    <p style="color: #999; font-size: 12px;">
                        SMTP 服务器: {smtp_config.host}:{smtp_config.port}<br>
                        加密方式: {smtp_config.encryption.upper()}<br>
                        发件人: {smtp_config.username}
                    </p>
                </div>
            </body>
            </html>
            """

            await self.send_email(
                to_email=to_email,
                subject="SMTP 配置测试邮件",
                html_body=html_body,
                smtp_config=smtp_config
            )

    async def send_verification_complete_email(
        self,
        to_email: str,
        filename: str,
        status: str,
        pass_rate: int
    ):
        """
        Send email notification when file verification is complete

        Args:
            to_email: Recipient email
            filename: File name
            status: Verification status
            pass_rate: Pass rate percentage
        """
        from app.services.email_template_service import template_service

        # Prepare context
        status_emoji = "✅" if status == "completed" else ("⚠️" if status == "warning" else "❌")
        status_text = "通过" if status == "completed" else ("有警告" if status == "warning" else "失败")
        status_class = "status-completed" if status == "completed" else ("status-warning" if status == "warning" else "status-failed")

        context = {
            "filename": filename,
            "status_emoji": status_emoji,
            "status_text": status_text,
            "pass_rate": pass_rate,
            "status-class": status_class
        }

        # Try to use template
        rendered = await template_service.render_email_template("verification_complete", context)

        if rendered:
            # Use template
            await self.send_email(
                to_email=to_email,
                subject=rendered["subject"],
                html_body=rendered["html_content"]
            )
        else:
            # Fallback to hardcoded template
            status_color = "#4CAF50" if status == "completed" else ("#FF9800" if status == "warning" else "#F44336")

            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f7fa;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #4285F4 100%); padding: 30px;">
                        <h1 style="color: white; margin: 0;">文件校验完成通知</h1>
                    </div>
                    <div style="padding: 30px;">
                        <p>您好！</p>
                        <p>您上传的文件校验已完成：</p>

                        <div style="background: #f8fafc; border-left: 4px solid #4285F4; padding: 15px; margin: 20px 0;">
                            <p style="margin: 0 0 10px 0; font-weight: bold;">文件名：{filename}</p>
                            <p style="margin: 5px 0;">状态：{status_emoji} {status_text}</p>
                            <p style="margin: 5px 0;">通过率：<span style="color: {status_color}; font-weight: bold;">{pass_rate}%</span></p>
                        </div>

                        <p style="margin-top: 20px;">请登录系统查看详细报告。</p>

                        <div style="margin-top: 30px; text-align: center;">
                            <a href="#" style="background: #4285F4; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block;">
                                查看详情
                            </a>
                        </div>
                    </div>
                    <div style="background: #f8fafc; padding: 20px; text-align: center; color: #999; font-size: 12px;">
                        <p style="margin: 0;">此邮件由系统自动发送，请勿回复。</p>
                    </div>
                </div>
            </body>
            </html>
            """

            await self.send_email(
                to_email=to_email,
                subject=f"文件校验完成 - {filename}",
                html_body=html_body
            )


# Global email service instance
email_service = EmailService()
