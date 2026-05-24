import asyncio
from app.core.database import async_session_maker
from app.models.audit import AuditLog
from sqlalchemy import select, func

async def main():
    async with async_session_maker() as session:
        result = await session.execute(select(func.count(AuditLog.id)))
        count = result.scalar_one()
        print(f"Total audit logs: {count}")

asyncio.run(main())
