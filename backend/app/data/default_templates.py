"""
Default email templates initialization
"""
import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.models.email_template import EmailTemplate


DEFAULT_TEMPLATES = [
    {
        "id": "verification_complete",
        "name": "文件校验完成通知",
        "description": "文件校验完成后发送给用户的通知邮件",
        "subject": "文件校验完成 - {filename}",
        "html_content": """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background-color: #f5f7fa; margin: 0; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #4285F4 100%); padding: 30px; }
        .header h1 { color: white; margin: 0; }
        .content { padding: 30px; }
        .info-box { background: #f8fafc; border-left: 4px solid #4285F4; padding: 15px; margin: 20px 0; }
        .info-box p { margin: 0 0 10px 0; }
        .info-box p:last-child { margin: 5px 0 0 0; }
        .status-emoji { font-size: 20px; }
        .pass-rate { font-weight: bold; }
        .btn { background: #4285F4; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; margin-top: 30px; }
        .footer { background: #f8fafc; padding: 20px; text-align: center; color: #999; font-size: 12px; }
        .footer p { margin: 0; }
        .status-completed { color: #4CAF50; }
        .status-warning { color: #FF9800; }
        .status-failed { color: #F44336; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>文件校验完成通知</h1>
        </div>
        <div class="content">
            <p>您好！</p>
            <p>您上传的文件校验已完成：</p>

            <div class="info-box">
                <p><strong>文件名：</strong>{filename}</p>
                <p><strong>状态：</strong><span class="status-emoji">{status_emoji}</span> {status_text}</p>
                <p><strong>通过率：</strong><span class="pass-rate {status-class}">{pass_rate}%</span></p>
            </div>

            <p style="margin-top: 20px;">请登录 system 查看详细报告。</p>

            <div style="text-align: center;">
                <a href="#" class="btn">查看详情</a>
            </div>
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>""",
        "variables": ["filename", "status_emoji", "status_text", "pass_rate", "status-class"]
    },
    {
        "id": "daily_summary",
        "name": "每日汇总报告",
        "description": "每日发送给订阅用户的文件校验汇总报告",
        "subject": "每日文件校验汇总报告 - {date}",
        "html_content": """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background-color: #f5f7fa; margin: 0; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #4285F4 100%); padding: 30px; }
        .header h1 { color: white; margin: 0; }
        .content { padding: 30px; }
        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }
        .stat-card { background: #f8fafc; padding: 20px; border-radius: 8px; text-align: center; }
        .stat-card .number { font-size: 32px; font-weight: bold; color: #4285F4; margin-bottom: 5px; }
        .stat-card .label { color: #666; font-size: 14px; }
        .stat-card.completed .number { color: #4CAF50; }
        .stat-card.warning .number { color: #FF9800; }
        .stat-card.failed .number { color: #F44336; }
        .file-list { margin-top: 30px; }
        .file-item { padding: 12px; border-bottom: 1px solid #eee; }
        .file-item:last-child { border-bottom: none; }
        .file-name { font-weight: bold; margin-bottom: 5px; }
        .file-meta { font-size: 12px; color: #666; }
        .status-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-left: 10px; }
        .status-completed { background: #E8F5E9; color: #4CAF50; }
        .status-warning { background: #FFF3E0; color: #FF9800; }
        .status-failed { background: #FFEBEE; color: #F44336; }
        .footer { background: #f8fafc; padding: 20px; text-align: center; color: #999; font-size: 12px; }
        .footer p { margin: 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>每日文件校验汇总报告</h1>
        </div>
        <div class="content">
            <p>您好！</p>
            <p>以下是 <strong>{date}</strong> 的文件校验汇总：</p>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="number">{total_count}</div>
                    <div class="label">总文件数</div>
                </div>
                <div class="stat-card completed">
                    <div class="number">{completed_count}</div>
                    <div class="label">通过</div>
                </div>
                <div class="stat-card warning">
                    <div class="number">{warning_count}</div>
                    <div class="label">警告</div>
                </div>
                <div class="stat-card failed">
                    <div class="number">{failed_count}</div>
                    <div class="label">失败</div>
                </div>
            </div>

            <div class="file-list">
                <h3>最近校验的文件</h3>
                {file_list_html}
            </div>

            <p style="margin-top: 30px;">请登录 system 查看更多详情。</p>
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿回复。</p>
            <p>如需取消订阅，请在系统设置中关闭"每日汇总"选项。</p>
        </div>
    </div>
</body>
</html>""",
        "variables": ["date", "total_count", "completed_count", "warning_count", "failed_count", "file_list_html"]
    },
    {
        "id": "smtp_test",
        "name": "SMTP 测试邮件",
        "description": "用于测试 SMTP 配置的测试邮件",
        "subject": "SMTP 配置测试邮件",
        "html_content": """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background-color: #f5f7fa; margin: 0; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #4285F4 100%); padding: 30px; }
        .header h2 { color: white; margin: 0; }
        .content { padding: 30px; }
        .info-box { background: #f8fafc; border-left: 4px solid #4CAF50; padding: 15px; margin: 20px 0; }
        .info-box p { margin: 5px 0; }
        .footer { background: #f8fafc; padding: 20px; text-align: center; color: #999; font-size: 12px; }
        .footer p { margin: 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>SMTP 测试邮件</h2>
        </div>
        <div class="content">
            <p>您好！</p>
            <p>这是一封来自 <strong>{from_name}</strong> 的测试邮件。</p>

            <div class="info-box">
                <p style="font-size: 18px; color: #4CAF50;">✅ SMTP 配置成功！</p>
            </div>

            <p>如果您收到此邮件，说明邮件服务配置正确。</p>
        </div>
        <div class="footer">
            <p>SMTP 服务器: {smtp_host}:{smtp_port}</p>
            <p>加密方式: {encryption}</p>
            <p>发件人: {username}</p>
        </div>
    </div>
</body>
</html>""",
        "variables": ["from_name", "smtp_host", "smtp_port", "encryption", "username"]
    }
]


async def init_default_templates():
    """Initialize default email templates in the database"""
    async with async_session_maker() as db:
        for template_data in DEFAULT_TEMPLATES:
            # Check if template already exists
            existing = await db.get(EmailTemplate, template_data["id"])

            if existing:
                # Update existing template
                existing.name = template_data["name"]
                existing.subject = template_data["subject"]
                existing.html_content = template_data["html_content"]
                existing.description = template_data["description"]
                existing.variables = json.dumps(template_data["variables"])
            else:
                # Create new template
                new_template = EmailTemplate(
                    id=template_data["id"],
                    name=template_data["name"],
                    subject=template_data["subject"],
                    html_content=template_data["html_content"],
                    description=template_data["description"],
                    variables=json.dumps(template_data["variables"]),
                    is_active="true"
                )
                db.add(new_template)

        await db.commit()
        print("✅ Default email templates initialized successfully")


if __name__ == "__main__":
    asyncio.run(init_default_templates())
