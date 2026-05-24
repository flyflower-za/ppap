"""
Settings API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, validator, field_validator
from typing import Optional, Literal
import os
import json
import logging

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin
from app.models.user import User
from app.models.setting import Setting
from app.core.audit_logger import log_audit_event

logger = logging.getLogger(__name__)

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
    current_user: User = Depends(get_current_admin),
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
    current_user: User = Depends(get_current_admin),
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
    current_user: User = Depends(get_current_admin),
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
    current_user: User = Depends(get_current_admin)
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
    current_user: User = Depends(get_current_admin),
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
    current_user: User = Depends(get_current_admin),
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
    current_user: User = Depends(get_current_admin),
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


# ==================== AI Model Configuration APIs ====================

import uuid as _uuid

_SINGLE_KEY = "ai_model_config"
_PROFILES_KEY = "ai_model_profiles"


class AiModelConfig(BaseModel):
    """Legacy single-model config kept for operator backward compat."""
    enabled: bool = False
    base_url: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    text_model: str = "gpt-4o-mini"
    vision_model: str = "gpt-4o"
    max_tokens: int = 2048
    temperature: float = 0.1


class ModelProfile(BaseModel):
    """A named OpenAI-compatible model profile."""
    id: str = ""
    name: str
    base_url: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    model_name: str
    model_type: Literal["text", "vision", "both"] = "both"
    max_tokens: int = 2048
    temperature: float = 0.1
    enabled: bool = True
    is_default_text: bool = False
    is_default_vision: bool = False


class SetDefaultRequest(BaseModel):
    for_type: Literal["text", "vision"]


# ---- helper utilities ------------------------------------------------------

async def _load_profiles_raw(db: AsyncSession) -> list:
    result = await db.get(Setting, _PROFILES_KEY)
    if result:
        try:
            return json.loads(result.value)
        except Exception:
            pass
    return []


async def _save_profiles_raw(db: AsyncSession, profiles: list):
    result = await db.get(Setting, _PROFILES_KEY)
    json_str = json.dumps(profiles)
    if result:
        result.value = json_str
    else:
        db.add(Setting(key=_PROFILES_KEY, value=json_str))
    await db.commit()


def _mask_profile(p: dict) -> dict:
    out = dict(p)
    if out.get("api_key"):
        out["api_key"] = "***"
    return out


async def _do_openai_test(api_key: str, base_url: str, model_name: str) -> dict:
    from openai import AsyncOpenAI
    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "回复 'pong' 即可，不要多余内容。"}],
            max_tokens=50,
            temperature=0
        )
        reply = response.choices[0].message.content
        reply = reply.strip() if reply else ""
        display_reply = reply if reply else "(模型返回了空内容)"
        return {"success": True, "message": f"连接成功！模型回复: {display_reply}"}
    except Exception as e:
        logger.error(f"OpenAI test failed: {e}")
        return {"success": False, "message": f"连接测试失败: {str(e)}"}


# ---- legacy single-config endpoints (kept for backward compat) -------------

@router.get("/ai-model")
async def get_ai_model_config(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get legacy single AI model configuration."""
    result = await db.get(Setting, _SINGLE_KEY)
    if result:
        try:
            data = json.loads(result.value)
            if data.get("api_key"):
                data["api_key"] = "***"
            return AiModelConfig(**data)
        except Exception:
            pass
    return AiModelConfig()


@router.post("/ai-model")
async def update_ai_model_config(
    config: AiModelConfig,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update legacy single AI model configuration."""
    config_dict = config.dict()
    existing = await db.get(Setting, _SINGLE_KEY)
    if config_dict.get("api_key") == "***":
        if existing:
            try:
                config_dict["api_key"] = json.loads(existing.value).get("api_key")
            except Exception:
                pass
        else:
            config_dict["api_key"] = None
    json_str = json.dumps(config_dict)
    if existing:
        existing.value = json_str
    else:
        db.add(Setting(key=_SINGLE_KEY, value=json_str))
    await db.commit()
    return {"message": "AI 模型配置已更新", "config": {k: v for k, v in config_dict.items() if k != "api_key"}}


@router.post("/ai-model/test")
async def test_ai_model_config(
    config: AiModelConfig,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Test legacy AI model config. Returns {success, message} HTTP 200."""
    api_key = config.api_key
    if not api_key or api_key == "***":
        existing = await db.get(Setting, _SINGLE_KEY)
        if existing:
            try:
                api_key = json.loads(existing.value).get("api_key")
            except Exception:
                pass
    if not api_key:
        return {"success": False, "message": "未配置 API Key。请先输入 API Key 并保存配置。"}
    return await _do_openai_test(api_key, config.base_url, config.text_model)


# ---- multi-profile endpoints -----------------------------------------------

@router.get("/ai-models")
async def list_model_profiles(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all model profiles (api_key masked)."""
    profiles = await _load_profiles_raw(db)
    return [_mask_profile(p) for p in profiles]


@router.post("/ai-models")
async def create_model_profile(
    profile: ModelProfile,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new model profile."""
    profiles = await _load_profiles_raw(db)
    profile_dict = profile.dict()
    profile_dict["id"] = str(_uuid.uuid4())
    # Auto-set as default if first profile
    if not profiles:
        if profile_dict["model_type"] in ("text", "both"):
            profile_dict["is_default_text"] = True
        if profile_dict["model_type"] in ("vision", "both"):
            profile_dict["is_default_vision"] = True
    profiles.append(profile_dict)
    await _save_profiles_raw(db, profiles)
    
    await log_audit_event(
        db=db,
        action="CREATE_MODEL_PROFILE",
        user=current_user,
        resource_type="SETTING",
        details={"profile_name": profile_dict["name"], "model_name": profile_dict["model_name"], "data": _mask_profile(profile_dict)}
    )
    await db.commit()
    
    return {"message": "模型配置已创建", "profile": _mask_profile(profile_dict)}


@router.put("/ai-models/{profile_id}")
async def update_model_profile(
    profile_id: str,
    profile: ModelProfile,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing model profile."""
    profiles = await _load_profiles_raw(db)
    idx = next((i for i, p in enumerate(profiles) if p["id"] == profile_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    update_dict = profile.dict()
    update_dict["id"] = profile_id
    submitted_key = update_dict.get("api_key")
    if not submitted_key or submitted_key == "***":
        update_dict["api_key"] = profiles[idx].get("api_key")
    profiles[idx] = update_dict
    await _save_profiles_raw(db, profiles)

    await log_audit_event(
        db=db,
        action="UPDATE_MODEL_PROFILE",
        user=current_user,
        resource_type="SETTING",
        details={"profile_id": profile_id, "profile_name": update_dict["name"], "data": _mask_profile(update_dict)}
    )
    await db.commit()

    return {"message": "模型配置已更新", "profile": _mask_profile(update_dict)}


@router.delete("/ai-models/{profile_id}")
async def delete_model_profile(
    profile_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a model profile."""
    profiles = await _load_profiles_raw(db)
    new_profiles = [p for p in profiles if p["id"] != profile_id]
    if len(new_profiles) == len(profiles):
        raise HTTPException(status_code=404, detail="模型配置不存在")
    await _save_profiles_raw(db, new_profiles)
    
    await log_audit_event(
        db=db,
        action="DELETE_MODEL_PROFILE",
        user=current_user,
        resource_type="SETTING",
        details={"profile_id": profile_id}
    )
    await db.commit()
    
    return {"message": "模型配置已删除"}


@router.post("/ai-models/{profile_id}/test")
async def test_model_profile(
    profile_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Test a specific model profile. Returns {success, message} HTTP 200."""
    profiles = await _load_profiles_raw(db)
    profile = next((p for p in profiles if p["id"] == profile_id), None)
    if not profile:
        return {"success": False, "message": "模型配置不存在"}
    api_key = profile.get("api_key")
    if not api_key:
        return {"success": False, "message": "该配置未设置 API Key"}
    return await _do_openai_test(
        api_key,
        profile.get("base_url", "https://api.openai.com/v1"),
        profile.get("model_name", "")
    )


@router.post("/ai-models/{profile_id}/set-default")
async def set_default_model_profile(
    profile_id: str,
    body: SetDefaultRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Set a profile as the default for text or vision inference."""
    profiles = await _load_profiles_raw(db)
    target_idx = next((i for i, p in enumerate(profiles) if p["id"] == profile_id), None)
    if target_idx is None:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    flag = f"is_default_{body.for_type}"
    for i, p in enumerate(profiles):
        p[flag] = (i == target_idx)
    await _save_profiles_raw(db, profiles)
    
    await log_audit_event(
        db=db,
        action="SET_DEFAULT_MODEL",
        user=current_user,
        resource_type="SETTING",
        details={"profile_id": profile_id, "type": body.for_type}
    )
    await db.commit()
    
    return {"message": f"已将该配置设为默认{body.for_type}模型"}



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

    await log_audit_event(
        db=db,
        action="UPDATE_RETENTION_SETTINGS",
        user=current_user,
        resource_type="SETTING",
        details={"data": settings.dict()}
    )
    
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
