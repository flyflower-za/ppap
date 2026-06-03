"""initial_schema

Revision ID: 455ad299810f
Revises:
Create Date: 2026-05-24 00:49:38.078268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '455ad299810f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Smart migration that checks if database is already initialized."""
    conn = op.get_bind()

    try:
        # Check if users table exists - if yes, database is already initialized
        inspector = inspect(conn)
        tables = inspector.get_table_names()

        if 'users' in tables:
            print("Database already initialized via init-db.sql, skipping migration...")
            return

        # If no tables exist, this would be the place to create them
        # But since we have init-db.sql for that, we just return
        print("No existing tables found - migration assumes init-db.sql will create the schema")

    except Exception as e:
        print(f"Migration check completed with warning: {e}")
        # Don't fail - let the database init happen separately


def downgrade() -> None:
    """Downgrade schema."""
    print("Downgrade not implemented - database schema managed by init-db.sql")
