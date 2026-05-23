"""
Email Template Service for rendering email templates
"""
import re
import json
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.email_template import EmailTemplate
from app.core.database import async_session_maker


class EmailTemplateService:
    """Service for rendering and managing email templates"""

    def render_template(self, template_content: str, context: Dict[str, Any]) -> str:
        """
        Render a template with given context variables

        Args:
            template_content: Template string with {variable} placeholders
            context: Dictionary of variables to substitute

        Returns:
            Rendered template string
        """
        result = template_content

        # Replace all variables in the template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))

        return result

    async def get_template(self, template_id: str, db: Optional[AsyncSession] = None) -> Optional[EmailTemplate]:
        """
        Get email template by ID

        Args:
            template_id: Template identifier
            db: Database session (optional, will create new if not provided)

        Returns:
            EmailTemplate object or None
        """
        if db is None:
            async with async_session_maker() as session:
                return await session.get(EmailTemplate, template_id)
        return await db.get(EmailTemplate, template_id)

    async def render_email_template(
        self,
        template_id: str,
        context: Dict[str, Any],
        db: Optional[AsyncSession] = None
    ) -> Optional[Dict[str, str]]:
        """
        Render an email template (both subject and body)

        Args:
            template_id: Template identifier
            context: Dictionary of variables to substitute
            db: Database session (optional)

        Returns:
            Dictionary with 'subject' and 'html_content' keys, or None if template not found
        """
        template = await self.get_template(template_id, db)

        if not template:
            return None

        if template.is_active != "true":
            return None

        return {
            "subject": self.render_template(template.subject, context),
            "html_content": self.render_template(template.html_content, context)
        }

    async def get_all_templates(self, db: AsyncSession) -> list[EmailTemplate]:
        """
        Get all email templates

        Args:
            db: Database session

        Returns:
            List of EmailTemplate objects
        """
        result = await db.execute(select(EmailTemplate))
        return result.scalars().all()

    def extract_variables(self, content: str) -> list[str]:
        """
        Extract variable names from template content

        Args:
            content: Template string

        Returns:
            List of variable names
        """
        return list(set(re.findall(r'\{\s*(\w+)\s*\}\}', content)))


# Global template service instance
template_service = EmailTemplateService()
