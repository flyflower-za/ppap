#!/usr/bin/env python3
"""
PPAP User Management CLI Tool

Standalone script to manage users without starting the backend server.

Features:
  - List all users (with password_hash status)
  - Create new users (with or without password)
  - Reset user password
  - Activate/deactivate users
  - Promote/demote admin privileges

Usage:
  python scripts/user_cli.py list
  python scripts/user_cli.py create --email user@example.com --password secret
  python scripts/user_cli.py reset-password --email user@example.com --password newpass
  python scripts/user_cli.py activate --email user@example.com
  python scripts/user_cli.py deactivate --email user@example.com
  python scripts/user_cli.py promote-admin --email user@example.com
  python scripts/user_cli.py demote-admin --email user@example.com

Environment:
  Reads DATABASE_URL from .env file (deploy/.env or backend/.env)
"""

import argparse
import asyncio
import os
import re
import sys
import uuid
from pathlib import Path

import bcrypt


def _find_env_path():
    """Find .env file in deploy/ or backend/ directory."""
    # script_dir: backend/scripts/ -> parent.parent -> project root
    # But if __file__ is absolute, we need to go up 3 levels: backend/scripts -> backend -> project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent  # Go up 3 levels: backend/scripts/user_cli.py -> backend -> project_root
    candidates = [
        project_root / "deploy" / ".env",
        project_root / ".env",
        Path.cwd() / ".env",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _load_database_url():
    """Load DATABASE_URL from environment variables or .env file."""
    # First, try to get from environment variables (Docker environment)
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        return database_url

    # If not in env, try to construct from POSTGRES_* variables
    postgres_db = os.environ.get("POSTGRES_DB", "ppap")
    postgres_user = os.environ.get("POSTGRES_USER", "ppap")
    postgres_password = os.environ.get("POSTGRES_PASSWORD", "ppap123")
    postgres_host = os.environ.get("POSTGRES_HOST", "postgres")  # Docker container name
    postgres_port = os.environ.get("POSTGRES_PORT", "5432")

    database_url = f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    return database_url


def _dsn():
    """Strip SQLAlchemy prefix from DATABASE_URL for asyncpg."""
    database_url = _load_database_url()
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", database_url)


def _hash_password(password: str) -> str:
    # 密码长度验证
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def _get_connection():
    import asyncpg
    dsn = _dsn()
    print(f"🔗 Connecting to database: {re.sub(r':[^:@]+@', ':***@', dsn)}")
    return await asyncpg.connect(dsn)


async def list_users():
    """List all users with their status."""
    conn = await _get_connection()
    try:
        users = await conn.fetch(
            """
            SELECT
                id,
                username,
                email,
                full_name,
                role,
                is_admin,
                is_active,
                password_hash IS NULL AS missing_password,
                sso_provider,
                ldap_dn,
                created_at
            FROM users
            ORDER BY created_at DESC
            """
        )

        if not users:
            print("📋 No users found.")
            return

        print(f"\n📋 Total users: {len(users)}\n")
        print(f"{'Email':<30} {'Username':<15} {'Role':<10} {'Admin':<6} {'Active':<6} {'Has Password':<12} {'SSO/LDAP':<10}")
        print("-" * 110)

        for u in users:
            has_pwd = "❌ NULL" if u["missing_password"] else "✅ Set"
            auth_provider = "SSO" if u["sso_provider"] else ("LDAP" if u["ldap_dn"] else "Local")
            print(
                f"{u['email']:<30} "
                f"{u['username']:<15} "
                f"{u['role']:<10} "
                f"{'✅' if u['is_admin'] else '❌':<6} "
                f"{'✅' if u['is_active'] else '❌':<6} "
                f"{has_pwd:<12} "
                f"{auth_provider:<10}"
            )
        print()

    finally:
        await conn.close()


async def create_user(email: str, full_name: str, password: str = None, role: str = "USER", department: str = None):
    """Create a new user."""
    conn = await _get_connection()
    try:
        # Check if user already exists
        existing = await conn.fetchrow("SELECT email FROM users WHERE email = $1", email)
        if existing:
            print(f"❌ Error: User with email '{email}' already exists")
            return

        # Generate username from email prefix
        base_username = email.split("@")[0].strip().lower()
        username = base_username
        suffix = 2
        while True:
            existing_username = await conn.fetchrow("SELECT username FROM users WHERE username = $1", username)
            if not existing_username:
                break
            username = f"{base_username}{suffix}"
            suffix += 1

        # Prepare user data
        user_id = str(uuid.uuid4())
        password_hash = _hash_password(password) if password else None

        await conn.execute(
            """
            INSERT INTO users (id, username, email, full_name, department, role, is_admin, is_active, password_hash)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            user_id,
            username,
            email,
            full_name,
            department,
            role,
            (role == "ADMIN"),
            True,
            password_hash,
        )

        print(f"✅ User created successfully:")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   Password: {'***' if password else '(not set - SSO/LDAP only)'}")
        print(f"   Role: {role}")

    finally:
        await conn.close()


async def reset_password(email: str, password: str):
    """Reset password for an existing user."""
    conn = await _get_connection()
    try:
        user = await conn.fetchrow("SELECT id, email, full_name FROM users WHERE email = $1", email)
        if not user:
            print(f"❌ Error: User '{email}' not found")
            return

        password_hash = _hash_password(password)
        await conn.execute(
            "UPDATE users SET password_hash = $1 WHERE id = $2",
            password_hash,
            user["id"],
        )

        print(f"✅ Password reset successfully for user:")
        print(f"   Email: {user['email']}")
        print(f"   Name: {user['full_name']}")

    finally:
        await conn.close()


async def activate_user(email: str):
    """Activate a user account."""
    conn = await _get_connection()
    try:
        result = await conn.execute(
            "UPDATE users SET is_active = TRUE WHERE email = $1", email
        )
        if result == "UPDATE 0":
            print(f"❌ Error: User '{email}' not found")
        else:
            print(f"✅ User '{email}' has been activated")

    finally:
        await conn.close()


async def deactivate_user(email: str):
    """Deactivate a user account."""
    conn = await _get_connection()
    try:
        result = await conn.execute(
            "UPDATE users SET is_active = FALSE WHERE email = $1", email
        )
        if result == "UPDATE 0":
            print(f"❌ Error: User '{email}' not found")
        else:
            print(f"⚠️  User '{email}' has been deactivated (cannot login)")

    finally:
        await conn.close()


async def promote_admin(email: str):
    """Promote a user to admin."""
    conn = await _get_connection()
    try:
        result = await conn.execute(
            """
            UPDATE users
            SET is_admin = TRUE, role = 'ADMIN'
            WHERE email = $1
            """,
            email,
        )
        if result == "UPDATE 0":
            print(f"❌ Error: User '{email}' not found")
        else:
            print(f"👑 User '{email}' promoted to admin")

    finally:
        await conn.close()


async def demote_admin(email: str):
    """Demote an admin to regular user."""
    conn = await _get_connection()
    try:
        result = await conn.execute(
            """
            UPDATE users
            SET is_admin = FALSE, role = 'USER'
            WHERE email = $1 AND is_admin = TRUE
            """,
            email,
        )
        if result == "UPDATE 0":
            print(f"❌ Error: User '{email}' not found or not an admin")
        else:
            print(f"👤 User '{email}' demoted to regular user")

    finally:
        await conn.close()


async def check_user(email: str):
    """Check if a user exists and show their details."""
    conn = await _get_connection()
    try:
        user = await conn.fetchrow(
            """
            SELECT
                id, username, email, full_name, department, role,
                is_admin, is_active, password_hash IS NULL AS missing_password,
                sso_provider, ldap_dn, created_at, last_login_at
            FROM users
            WHERE email = $1
            """,
            email,
        )

        if not user:
            print(f"❌ User '{email}' not found")
            return

        print(f"\n👤 User Details:")
        print(f"   Email:        {user['email']}")
        print(f"   Username:     {user['username']}")
        print(f"   Full Name:    {user['full_name']}")
        print(f"   Department:   {user['department'] or '(not set)'}")
        print(f"   Role:         {user['role']}")
        print(f"   Is Admin:     {'✅ Yes' if user['is_admin'] else '❌ No'}")
        print(f"   Is Active:    {'✅ Yes' if user['is_active'] else '❌ No'}")
        print(f"   Password:     {'❌ Not Set' if user['missing_password'] else '✅ Set'}")
        print(f"   Auth Provider: {'SSO' if user['sso_provider'] else ('LDAP' if user['ldap_dn'] else 'Local')}")
        print(f"   Created At:   {user['created_at']}")
        print(f"   Last Login:   {user['last_login_at'] or '(never)'}")
        print()

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="PPAP User Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/user_cli.py list
  python scripts/user_cli.py create --email admin@company.com --password admin123 --role ADMIN --full-name "Admin User"
  python scripts/user_cli.py check --email user@example.com
  python scripts/user_cli.py reset-password --email user@example.com --password newpass
  python scripts/user_cli.py activate --email user@example.com
  python scripts/user_cli.py promote-admin --email user@example.com
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List all users")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check if a user exists")
    check_parser.add_argument("--email", required=True, help="User email address")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new user")
    create_parser.add_argument("--email", required=True, help="User email address")
    create_parser.add_argument("--full-name", required=True, help="User full name")
    create_parser.add_argument("--password", help="Password (optional, for SSO/LDAP users omit this)")
    create_parser.add_argument("--role", default="USER", choices=["USER", "MANAGER", "ADMIN"], help="User role (default: USER)")
    create_parser.add_argument("--department", help="Department name")

    # Reset password command
    reset_parser = subparsers.add_parser("reset-password", help="Reset user password")
    reset_parser.add_argument("--email", required=True, help="User email address")
    reset_parser.add_argument("--password", required=True, help="New password")

    # Activate command
    activate_parser = subparsers.add_parser("activate", help="Activate a user account")
    activate_parser.add_argument("--email", required=True, help="User email address")

    # Deactivate command
    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate a user account")
    deactivate_parser.add_argument("--email", required=True, help="User email address")

    # Promote admin command
    promote_parser = subparsers.add_parser("promote-admin", help="Promote user to admin")
    promote_parser.add_argument("--email", required=True, help="User email address")

    # Demote admin command
    demote_parser = subparsers.add_parser("demote-admin", help="Demote admin to regular user")
    demote_parser.add_argument("--email", required=True, help="User email address")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "list":
        asyncio.run(list_users())
    elif args.command == "check":
        asyncio.run(check_user(args.email))
    elif args.command == "create":
        asyncio.run(create_user(
            email=args.email,
            full_name=args.full_name,
            password=args.password,
            role=args.role,
            department=args.department,
        ))
    elif args.command == "reset-password":
        asyncio.run(reset_password(args.email, args.password))
    elif args.command == "activate":
        asyncio.run(activate_user(args.email))
    elif args.command == "deactivate":
        asyncio.run(deactivate_user(args.email))
    elif args.command == "promote-admin":
        asyncio.run(promote_admin(args.email))
    elif args.command == "demote-admin":
        asyncio.run(demote_admin(args.email))


if __name__ == "__main__":
    main()
