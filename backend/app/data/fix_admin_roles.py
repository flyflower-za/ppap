"""
Quick script to fix admin user roles
"""
import asyncio
from sqlalchemy import text
from app.core.database import engine

async def fix_admin_roles():
    """Fix admin user roles"""
    async with engine.begin() as conn:
        # Update admin users based on is_admin field
        result = await conn.execute(
            text("UPDATE users SET role = 'ADMIN' WHERE is_admin = TRUE AND role != 'ADMIN'")
        )
        print(f"✅ Updated {result.rowcount} admin users to ADMIN role")

if __name__ == "__main__":
    asyncio.run(fix_admin_roles())
