"""
Migration script to add role field to existing users
Run this script to update existing users with role field
"""
import asyncio
from sqlalchemy import select, text
from app.core.database import async_session_maker, engine
from app.models.user import User, UserRole


async def add_role_column():
    """Add role column to users table if it doesn't exist"""
    async with engine.begin() as conn:
        # Check if role column exists
        try:
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='role'")
            )
            role_exists = result.first() is not None

            if not role_exists:
                # Add role column with uppercase enum values
                await conn.execute(
                    text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'USER' NOT NULL")
                )
                print("✅ Added role column to users table")
            else:
                print("ℹ️  Role column already exists")
        except Exception as e:
            print(f"⚠️  Error checking/adding role column: {e}")


async def add_ad_groups_column():
    """Add ad_groups column to users table if it doesn't exist"""
    async with engine.begin() as conn:
        # Check if ad_groups column exists
        try:
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='ad_groups'")
            )
            column_exists = result.first() is not None

            if not column_exists:
                # Add ad_groups column
                await conn.execute(
                    text("ALTER TABLE users ADD COLUMN ad_groups VARCHAR(1000)")
                )
                print("✅ Added ad_groups column to users table")
            else:
                print("ℹ️  ad_groups column already exists")
        except Exception as e:
            print(f"⚠️  Error checking/adding ad_groups column: {e}")


async def migrate_user_roles():
    """Add role field to existing users"""
    # First add the columns if they don't exist
    await add_role_column()
    await add_ad_groups_column()

    # Fix any incorrect enum values in the database
    async with engine.begin() as conn:
        try:
            # Update users based on is_admin field
            result = await conn.execute(
                text("UPDATE users SET role = 'ADMIN' WHERE is_admin = TRUE AND (role IS NULL OR role != 'ADMIN')")
            )
            if result.rowcount > 0:
                print(f"✅ Updated {result.rowcount} admin users to ADMIN role")

            result = await conn.execute(
                text("UPDATE users SET role = 'USER' WHERE is_admin = FALSE AND (role IS NULL OR role NOT IN ('ADMIN', 'MANAGER', 'USER'))")
            )
            if result.rowcount > 0:
                print(f"✅ Updated {result.rowcount} regular users to USER role")
        except Exception as e:
            print(f"⚠️  Error updating enum values: {e}")

    # Now update existing users using ORM
    async with async_session_maker() as db:
        # Get all users
        result = await db.execute(select(User))
        users = result.scalars().all()

        updated_count = 0
        for user in users:
            # Only update if role is not set or is invalid
            if user.role is None or user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER]:
                # Set role based on is_admin field for backward compatibility
                if user.is_admin:
                    user.role = UserRole.ADMIN
                else:
                    user.role = UserRole.USER
                updated_count += 1

        if updated_count > 0:
            await db.commit()
            print(f"✅ Updated {updated_count} users with role field")
        else:
            print("ℹ️  All users already have roles set")


if __name__ == "__main__":
    asyncio.run(migrate_user_roles())
