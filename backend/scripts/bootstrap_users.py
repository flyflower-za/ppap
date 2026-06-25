#!/usr/bin/env python3
"""
Bootstrap script to ensure at least one admin user exists with a known password.

Idempotent — safe to run on every deployment.
Connects to the database and:
  1. Creates a default admin user if NO users exist.
  2. Sets a fallback password for any user with NULL password_hash.

Usage:
  python scripts/bootstrap_users.py

Environment variables:
  DATABASE_URL        — PostgreSQL connection (default: postgresql+asyncpg://ppap:ppap123@localhost:5432/ppap)
  ADMIN_EMAIL         — Default admin email (default: admin@example.com)
  ADMIN_PASSWORD      — Default/fallback password (default: admin123)
  ADMIN_PASSWORD_HASH — Pre-computed bcrypt hash (takes precedence over ADMIN_PASSWORD)
"""

import asyncio
import os
import re
import sys
import uuid

import bcrypt


# ── Config ────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://ppap:ppap123@localhost:5432/ppap",
)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")


def _dsn() -> str:
    """Strip SQLAlchemy prefix from DATABASE_URL for asyncpg."""
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", DATABASE_URL)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def bootstrap():
    import asyncpg

    dsn = _dsn()
    print(f"[bootstrap] Connecting to {re.sub(r':[^:@]+@', ':***@', dsn)}")
    conn = await asyncpg.connect(dsn)

    try:
        # ── Step 1: Count existing users ──
        count = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"[bootstrap] Existing users: {count}")

        if count == 0:
            # No users at all — create the admin
            pwd_hash = ADMIN_PASSWORD_HASH or _hash_password(ADMIN_PASSWORD)
            user_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO users (id, username, email, full_name, is_active, is_admin, role, password_hash)
                VALUES ($1, $2, $3, $4, TRUE, TRUE, 'ADMIN', $5)
                """,
                user_id,
                ADMIN_EMAIL.split("@")[0],
                ADMIN_EMAIL,
                "System Administrator",
                pwd_hash,
            )
            print(f"[bootstrap] ✅ Created admin user: {ADMIN_EMAIL} (password: {ADMIN_PASSWORD})")
            return

        # ── Step 2: Fix users with NULL password_hash (local accounts only) ──
        # Only set password for users WITHOUT SSO/LDAP provider marks
        null_pwd_users = await conn.fetch(
            """
            SELECT id, email, sso_provider, ldap_dn
            FROM users
            WHERE password_hash IS NULL
              AND sso_provider IS NULL
              AND ldap_dn IS NULL
            LIMIT 50
            """
        )
        if null_pwd_users:
            pwd_hash = ADMIN_PASSWORD_HASH or _hash_password(ADMIN_PASSWORD)
            for row in null_pwd_users:
                await conn.execute(
                    "UPDATE users SET password_hash = $1 WHERE id = $2",
                    pwd_hash,
                    row["id"],
                )
                print(f"[bootstrap] 🔑 Set password for local user: {row['email']}")

            print(f"[bootstrap] ✅ Fixed {len(null_pwd_users)} local user(s) with missing password")
        else:
            print("[bootstrap] ✓ All local users have password_hash set")

        # ── Step 3: Ensure at least one admin exists ──
        admin = await conn.fetchrow(
            "SELECT id, email FROM users WHERE is_admin = TRUE LIMIT 1"
        )
        if not admin:
            first_user = await conn.fetchrow(
                "SELECT id, email FROM users ORDER BY created_at ASC LIMIT 1"
            )
            if first_user:
                await conn.execute(
                    "UPDATE users SET is_admin = TRUE, role = 'ADMIN' WHERE id = $1",
                    first_user["id"],
                )
                print(f"[bootstrap] 👑 Promoted first user to admin: {first_user['email']}")
        else:
            print(f"[bootstrap] ✓ Admin user exists: {admin['email']}")

    finally:
        await conn.close()

    print("[bootstrap] Done.")


if __name__ == "__main__":
    asyncio.run(bootstrap())
