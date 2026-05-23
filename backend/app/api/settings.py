"""
Settings API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, validator, field_validator
from typing import Optional, Literal
import os
import json

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.setting import Setting

router = APIRouter()


class NotificationSettings(BaseModel):
    """Notification Settings Schema"""
    email_enabled: bool = True
    notify_on_failure: bool = True
    daily_summary: bool = False


class SmtpConfig(BaseModel):
    """SMTP Configuration Schema"""
    enabled: bool = False
    host: Optional[str] = None
    port: int = 587
    encryption: Literal['none', 'tls', 'ssl'] = 'tls'
    username: Optional[EmailStr] = None
    from_name: str = "文件校验平台"
    password: Optional[str] = None

    @field_validator('host', 'username')
    @classmethod
    def validate_smtp_fields(cls, v, info):
        """Validate SMTP fields when enabled"""
        if info.data.get('enabled', False):
            if v is None or v == '':
                raise ValueError('启用 SMTP 时必须填写该字段')
        return v


class FileRetentionSettings(BaseModel):
    """File Retention Settings Schema"""
    retention_days: int = 30
    auto_cleanup_enabled: bool = True
    cleanup_hour: int = 2  # Hour of day (0-23) to run cleanup

    @field_validator('retention_days')
    @classmethod
    def validate_retention_days(cls, v):
        """Validate retention days is positive and reasonable"""
        if v < 1:
            raise ValueError('保留天数必须大于0')
        if v > 3650:  # 10 years max
            raise ValueError('保留天数不能超过3650天（10年）')
        return v

    @field_validator('cleanup_hour')
    @classmethod
    def validate_cleanup_hour(cls, v):
        """Validate cleanup hour is valid"""
        if v < 0 or v > 23:
            raise ValueError('清理时间必须在0-23之间')
        return v


class SmtpTestRequest(BaseModel):
    """SMTP Test Email Request"""
    config: SmtpConfig
    test_email: Optional[EmailStr] = None


@router.get("/notifications")
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get notification settings

    Only admin users can access this endpoint.
    """
    # TODO: Check if user is admin
    from app.models.setting import Setting

    # Try to load from database
    result = await db.get(Setting, "notification_settings")
    if result:
        try:
            data = json.loads(result.value)
            return NotificationSettings(**data)
        except Exception:
            pass

    # Return defaults
    return NotificationSettings()


@router.post("/notifications")
async def update_notification_settings(
    settings: NotificationSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update notification settings

    Only admin users can access this endpoint.
    """
    # TODO: Check if user is admin
    from app.models.setting import Setting

    # Convert Pydantic model to JSON string
    json_str = json.dumps(settings.dict())

    # Check if setting exists
    result = await db.get(Setting, "notification_settings")
    if result:
        result.value = json_str
    else:
        new_setting = Setting(key="notification_settings", value=json_str)
        db.add(new_setting)

    await db.commit()

    return {
        "message": "通知设置已更新",
        "settings": settings.dict()
    }


@router.get("/smtp")
async def get_smtp_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get SMTP configuration

    Only admin users can access this endpoint.
    """
    # TODO: Check if user is admin
    # Try to load from database
    result = await db.get(Setting, "smtp_config")
    if result:
        try:
            data = json.loads(result.value)
            # Mask actual password
            if "password" in data and data["password"]:
                data["password"] = "***"
            return SmtpConfig(**data)
        except Exception:
            pass

    # Fallback to environment variables
    config = SmtpConfig(
        enabled=os.getenv("SMTP_ENABLED", "false").lower() == "true",
        host=os.getenv("SMTP_HOST"),
        port=int(os.getenv("SMTP_PORT", "587")),
        encryption="tls" if os.getenv("SMTP_USE_TLS", "true").lower() == "true" else "none",
        username=os.getenv("SMTP_USERNAME"),
        from_name=os.getenv("SMTP_FROM", "文件校验平台"),
        password="***"  # Never return actual password
    )
    return config


@router.post("/smtp")
async def update_smtp_config(
    config: SmtpConfig,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update SMTP configuration

    Only admin users can access this endpoint.
    """
    # TODO: Check if user is admin

    # Validate configuration when enabled
    if config.enabled:
        if not config.host or not config.username:
            raise HTTPException(
                status_code=400,
                detail="启用 SMTP 时必须填写服务器和邮箱"
            )

    from app.models.setting import Setting
    import json
    
    # Fetch existing setting to handle password preservation
    existing = await db.get(Setting, "smtp_config")
    config_dict = config.dict()
    
    if config_dict.get("password") == "***":
        if existing:
            try:
                existing_data = json.loads(existing.value)
                config_dict["password"] = existing_data.get("password")
            except Exception:
                pass
        else:
            config_dict["password"] = os.getenv("SMTP_PASSWORD")
            
    json_str = json.dumps(config_dict)
    
    if existing:
        existing.value = json_str
    else:
        new_setting = Setting(key="smtp_config", value=json_str)
        db.add(new_setting)
        
    await db.commit()

    return {
        "message": "SMTP 配置已更新",
        "config": config.dict(exclude={'password'})
    }


@router.post("/smtp/test")
async def test_smtp_config(
    request: SmtpTestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Test SMTP configuration by sending a test email

    Only admin users can access this endpoint.
    """
    # TODO: Check if user is admin
    from app.services.email_service import email_service

    config = request.config
    test_email = request.test_email or current_user.email

    try:
        await email_service.send_test_email(
            smtp_config=config,
            to_email=test_email
        )
        return {
            "message": f"测试邮件已发送至 {test_email}",
            "success": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"发送测试邮件失败: {str(e)}"
        )


# ==================== Email Template APIs ====================

class EmailTemplateModel(BaseModel):
    """Email Template Schema"""
    id: str
    name: str
    subject: str
    html_content: str
    description: str | None = None
    variables: list[str] | None = None
    is_active: bool = True


class EmailTemplatePreview(BaseModel):
    """Email Template Preview Schema"""
    template_id: str
    context: dict


@router.get("/email-templates")
async def get_email_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all email templates"""
    from app.models.email_template import EmailTemplate
    from sqlalchemy import select

    result = await db.execute(select(EmailTemplate))
    templates = result.scalars().all()

    return [
        {
            "id": tmpl.id,
            "name": tmpl.name,
            "subject": tmpl.subject,
            "description": tmpl.description,
            "variables": json.loads(tmpl.variables) if tmpl.variables else [],
            "is_active": tmpl.is_active == "true"
        }
        for tmpl in templates
    ]


@router.get("/debug/permissions")
async def debug_permissions(
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to check user permissions"""
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

    return {
        "user_email": current_user.email,
        "user_role": user_role,
        "is_admin": current_user.is_admin,
        "can_access": {
            "profile": True,
            "notification": True,
            "smtp": user_role == "ADMIN",
            "email_templates": user_role == "ADMIN",
            "ldap": user_role == "ADMIN",
            "users": user_role == "ADMIN",
        }
    }


@router.get("/email-templates/{template_id}")
async def get_email_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific email template"""
    from app.models.email_template import EmailTemplate

    template = await db.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    return {
        "id": template.id,
        "name": template.name,
        "subject": template.subject,
        "html_content": template.html_content,
        "description": template.description,
        "variables": json.loads(template.variables) if template.variables else [],
        "is_active": template.is_active == "true"
    }


@router.post("/email-templates")
async def create_email_template(
    template: EmailTemplateModel,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new email template"""
    from app.models.email_template import EmailTemplate
    import re

    # Check if template ID already exists
    existing = await db.get(EmailTemplate, template.id)
    if existing:
        raise HTTPException(status_code=400, detail="模板ID已存在")

    # Extract variables from template
    variables = list(set(re.findall(r'\{\s*(\w+)\s*\}\}', template.subject + ' ' + template.html_content)))

    new_template = EmailTemplate(
        id=template.id,
        name=template.name,
        subject=template.subject,
        html_content=template.html_content,
        description=template.description,
        variables=json.dumps(variables),
        is_active="true" if template.is_active else "false"
    )

    db.add(new_template)
    await db.commit()

    return {"message": "模板创建成功", "template": template.dict()}


@router.put("/email-templates/{template_id}")
async def update_email_template(
    template_id: str,
    template: EmailTemplateModel,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing email template"""
    from app.models.email_template import EmailTemplate
    import re

    db_template = await db.get(EmailTemplate, template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # Update fields
    db_template.name = template.name
    db_template.subject = template.subject
    db_template.html_content = template.html_content
    db_template.description = template.description

    # Re-extract variables
    variables = list(set(re.findall(r'\{\s*(\w+)\s*\}\}', template.subject + ' ' + template.html_content)))
    db_template.variables = json.dumps(variables)

    await db.commit()

    return {"message": "模板更新成功"}


@router.post("/email-templates/preview")
async def preview_email_template(
    preview: EmailTemplatePreview,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Preview an email template with given context"""
    from app.models.email_template import EmailTemplate
    from app.services.email_template_service import template_service

    template = await db.get(EmailTemplate, preview.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # Render template with context
    html_content = template_service.render_template(
        template.html_content,
        preview.context
    )

    return {"html_content": html_content}


@router.delete("/email-templates/{template_id}")
async def delete_email_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an email template"""
    from app.models.email_template import EmailTemplate

    template = await db.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    await db.delete(template)
    await db.commit()

    return {"message": "模板删除成功"}


# ==================== File Retention Settings APIs ====================

@router.get("/file-retention")
async def get_file_retention_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get file retention settings

    Only admin users can access this endpoint.
    """
    # Check if user is admin
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role != "ADMIN":
        raise HTTPException(status_code=403, detail="只有管理员可以访问此设置")

    # Try to load from database
    result = await db.get(Setting, "file_retention_settings")
    if result:
        try:
            data = json.loads(result.value)
            return FileRetentionSettings(**data)
        except Exception:
            pass

    # Return defaults
    return FileRetentionSettings()


@router.post("/file-retention")
async def update_file_retention_settings(
    settings: FileRetentionSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update file retention settings

    Only admin users can access this endpoint.
    """
    # Check if user is admin
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role != "ADMIN":
        raise HTTPException(status_code=403, detail="只有管理员可以访问此设置")

    from app.models.setting import Setting
    import json

    # Convert Pydantic model to JSON string
    json_str = json.dumps(settings.dict())

    # Check if setting exists
    result = await db.get(Setting, "file_retention_settings")
    if result:
        result.value = json_str
    else:
        new_setting = Setting(key="file_retention_settings", value=json_str)
        db.add(new_setting)

    await db.commit()

    return {
        "message": "文件保留设置已更新",
        "settings": settings.dict()
    }


@router.post("/file-retention/cleanup-now")
async def trigger_cleanup_now(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger file cleanup task

    Only admin users can access this endpoint.
    """
    # Check if user is admin
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role != "ADMIN":
        raise HTTPException(status_code=403, detail="只有管理员可以执行此操作")

    from app.tasks.cleanup_tasks import cleanup_expired_files

    # Trigger the cleanup task asynchronously
    task = cleanup_expired_files.delay()

    return {
        "message": "文件清理任务已启动",
        "task_id": task.id
    }
