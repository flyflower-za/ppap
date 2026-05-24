import asyncio
from app.core.database import async_session_maker
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.rule import DocumentCategory
from app.schemas.rule import DocumentCategoryWithRules

async def test():
    async with async_session_maker() as db:
        result = await db.execute(select(DocumentCategory).options(selectinload(DocumentCategory.rules)))
        categories = result.scalars().all()
        for cat in categories:
            try:
                resp = DocumentCategoryWithRules.model_validate(cat)
                print("Success:", resp)
            except Exception as e:
                print("Error:", e)

asyncio.run(test())
